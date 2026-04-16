import asyncio
import json
from typing import Any
import litellm

_TOOL_TIMEOUT = 60


def _unavailable() -> str:
    return "Tool is unavailable, please apologize to the user and ask them to try again later."

from loguru import logger
from nanobot.agent.tools.base import Tool
from agent.utils.parsing import parse_agent_response
from agent.framework.nanobot.utils.guardrails import WRITE_TOOLS, TOOL_GUARDRAILS


class DispatchTool(Tool):
    def __init__(self, provider, registry, model: str, temperature: float, max_tokens: int):
        self._provider = provider
        self._registry = registry
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    @property
    def name(self) -> str:
        return "dispatch"

    @property
    def description(self) -> str:
        from agent.framework.nanobot.agents.sub_agents_odoo import AGENTS as _ODOO_AGENTS
        from agent.framework.nanobot.agents.sub_agents_demo import AGENTS as _DEMO_AGENTS
        from agent.framework.nanobot.main import _healthy_servers
        all_agents = [
            a for a in (_ODOO_AGENTS + _DEMO_AGENTS)
            if all(
                t.split("_")[1] in _healthy_servers
                for t in a["allowed_tools"]
                if t.startswith("mcp_")
            )
        ]
        names = ", ".join(a["name"] for a in all_agents) or "none"
        return (
            "Route a task to a specialized domain agent. "
            "Use this for all ERP operations instead of calling MCP tools directly. "
            f"Available agents: {names}."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "agent_name": {
                    "type": "string",
                    "description": "Name of the agent to dispatch to.",
                },
                "task": {
                    "type": "string",
                    "description": "Full task description for the agent.",
                },
            },
            "required": ["agent_name", "task"],
        }

    async def execute(self, agent_name: str, task: str) -> str:
        from agent.framework.nanobot.agents.sub_agents_odoo import AGENTS as _ODOO_AGENTS
        from agent.framework.nanobot.agents.sub_agents_demo import AGENTS as _DEMO_AGENTS
        from agent.framework.nanobot.main import _healthy_servers
        AGENTS = [
            a for a in (_ODOO_AGENTS + _DEMO_AGENTS)
            if all(
                t.split("_")[1] in _healthy_servers
                for t in a["allowed_tools"]
                if t.startswith("mcp_")
            )
        ]
        from agent.models import AgentAction, AgentTemplate
        from agent.framework.nanobot.main import _user_role, _user_id, _task_queues, _run_id, _source, _bot_id

        db_template = await AgentTemplate.objects.filter(name=agent_name, is_active=True).afirst()
        if db_template:
            template = {"name": db_template.name, "system_prompt": db_template.instructions, "allowed_tools": db_template.allowed_tools}
        else:
            disabled = await AgentTemplate.objects.filter(name=agent_name, is_active=False).afirst()
            if disabled:
                return f"Error: Agent '{agent_name}' is currently disabled."
            template = next((a for a in AGENTS if a["name"] == agent_name), None)
        if not template:
            builtin_names = [a["name"] for a in AGENTS]
            db_names = [t async for t in AgentTemplate.objects.filter(is_active=True).values_list("name", flat=True)]
            return f"Error: No agent named '{agent_name}'. Available: {list(set(builtin_names + db_names))}"

        role = _user_role.get()
        if role == "viewer":
            blocked = set(template["allowed_tools"]) & WRITE_TOOLS
            if blocked:
                return f"Access denied: your role (viewer) cannot perform write operations."

        action = await AgentAction.objects.acreate(
            run_id=_run_id.get(),
            source=_source.get(),
            bot_id=_bot_id.get(),
            user_id=_user_id.get(),
            intent=task[:500],
            agent_name=agent_name,
            tool_called="",
            status=AgentAction.Status.PENDING,
            input_params={"task": task},
            output={},
        )

        allowed = set(template["allowed_tools"])
        filtered = {
            name: tool
            for name, tool in self._registry._tools.items()
            if name in allowed
        }
        tool_defs = [tool.to_schema() for tool in filtered.values()]

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": template["system_prompt"]},
            {"role": "user", "content": task},
        ]

        current_task = asyncio.current_task()
        q = _task_queues.get(id(current_task)) if current_task else None

        if q:
            q.put_nowait({"type": "progress", "content": f"dispatch({agent_name!r})"})

        final_text = "Task completed with no output."
        total_prompt = 0
        total_completion = 0

        try:
            for _ in range(10):
                if _ == 0:
                    logger.info(f"[sub-agent:{agent_name}] start")
                response = await litellm.acompletion(
                    model=self._model,
                    messages=messages,
                    tools=tool_defs,
                    temperature=self._temperature,
                    max_tokens=self._max_tokens,
                )
                total_prompt += response.usage.prompt_tokens or 0
                total_completion += response.usage.completion_tokens or 0
                msg = response.choices[0].message
                if msg.tool_calls:
                    tool_call_dicts = [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                        }
                        for tc in msg.tool_calls
                    ]
                    messages.append({
                        "role": "assistant",
                        "content": msg.content or "",
                        "tool_calls": tool_call_dicts,
                    })
                    for tc in msg.tool_calls:
                        tool = filtered.get(tc.function.name)
                        if tool:
                            kwargs = json.loads(tc.function.arguments)
                            logger.info(f"[sub-agent:{agent_name}] → {tc.function.name}({tc.function.arguments})")
                            guardrail = TOOL_GUARDRAILS.get(tc.function.name, {})
                            violation = None
                            if "max_quantity" in guardrail and kwargs.get("quantity", 0) > guardrail["max_quantity"]:
                                violation = f"Guardrail violated: quantity {kwargs['quantity']} exceeds limit {guardrail['max_quantity']}."
                            if "max_unit_price" in guardrail and kwargs.get("price_unit", 0) > guardrail["max_unit_price"]:
                                violation = f"Guardrail violated: price_unit {kwargs['price_unit']} exceeds limit {guardrail['max_unit_price']}."
                            if violation:
                                await AgentAction.objects.filter(id=action.id).aupdate(
                                    status=AgentAction.Status.FAILED,
                                    output={"error": violation},
                                )
                                return violation
                            if q:
                                q.put_nowait({"type": "progress", "content": f"[{agent_name}] → {tc.function.name}({json.dumps(kwargs)})"})
                            try:
                                result = await asyncio.wait_for(tool.execute(**kwargs), timeout=_TOOL_TIMEOUT)
                            except asyncio.TimeoutError:
                                result = _unavailable()
                            preview = result[:120] if isinstance(result, str) else str(result)[:120]
                            logger.info(f"[sub-agent:{agent_name}] ← {tc.function.name}: {preview}")
                            if q:
                                q.put_nowait({"type": "progress", "content": f"[{agent_name}] ← {tc.function.name}: {preview}"})
                            if tc.function.name in WRITE_TOOLS:
                                try:
                                    ref_data = json.loads(result)
                                    ref = str(ref_data.get("order_id") or ref_data.get("invoice_id") or "")
                                    if ref:
                                        await AgentAction.objects.filter(id=action.id).aupdate(erp_record_ref=ref)
                                except Exception:
                                    pass
                        else:
                            result = f"Error: Tool '{tc.function.name}' not available for {agent_name}"
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": tc.function.name,
                            "content": result,
                        })
                else:
                    final_text = msg.content or final_text
                    preview = final_text[:200] if isinstance(final_text, str) else str(final_text)[:200]
                    logger.info(f"[sub-agent:{agent_name}] ← {preview}")
                    break

            # logger.info(f"[{agent_name}] raw response: {final_text[:500]}")

            tools_used = ", ".join(dict.fromkeys(m["name"] for m in messages if m.get("role") == "tool"))[:255]
            result = parse_agent_response(final_text, agent_name, task, q, fallback=final_text, action_id=action.id)

            tokens = {"prompt": total_prompt, "completion": total_completion, "total": total_prompt + total_completion}
            if q:
                q.put_nowait({"type": "progress", "content": f"Tokens: {total_prompt} prompt / {total_completion} completion / {total_prompt + total_completion} total"})

            if result.confirmation_required:
                await AgentAction.objects.filter(id=action.id).aupdate(
                    tool_called=tools_used,
                    output={"pending_summary": result.summary, "details": result.details, "tokens": tokens},
                )
                return result.summary
            else:
                await AgentAction.objects.filter(id=action.id).aupdate(
                    status=AgentAction.Status.SUCCESS,
                    tool_called=tools_used,
                    output={"result": result.summary, "tokens": tokens},
                    artifacts=result.artifacts,
                )

            return result.summary

        except Exception as e:
            await AgentAction.objects.filter(id=action.id).aupdate(
                status=AgentAction.Status.FAILED,
                output={"error": str(e)},
            )
            raise
