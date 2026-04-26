import asyncio
import copy
import json
from typing import Any

import litellm
from loguru import logger
from nanobot.agent.tools.base import Tool

from agent.models import AgentAction
from agent.utils.parsing import parse_agent_response
from agent.framework.nanobot.agents.registry import AgentRegistry

_TOOL_TIMEOUT = 60


def _unavailable() -> str:
    return "Tool is unavailable, please apologize to the user and ask them to try again later."


def _main():
    # lazy: dispatch is imported during nanobot main module load — circular
    from agent.framework.nanobot import main
    return main


class ProgressEmitter:
    def __init__(self, queue):
        self.q = queue

    def _emit(self, content: str) -> None:
        if self.q:
            self.q.put_nowait({"type": "progress", "content": content})

    def dispatch_start(self, agent_name: str) -> None:
        self._emit(f"dispatch({agent_name!r})")

    def tool_call(self, agent_name: str, tool_name: str, kwargs: dict) -> None:
        self._emit(f"[{agent_name}] → {tool_name}({json.dumps(kwargs)})")

    def tool_result(self, agent_name: str, tool_name: str, preview: str) -> None:
        self._emit(f"[{agent_name}] ← {tool_name}: {preview}")

    def tokens(self, prompt: int, completion: int) -> None:
        self._emit(f"Tokens: {prompt} prompt / {completion} completion / {prompt + completion} total")


class GuardrailChecker:
    def __init__(self, tool_config: dict[str, dict], requires_write_access: bool):
        self._tool_config = tool_config
        self._requires_write_access = requires_write_access

    def check_role(self, role: str) -> str | None:
        if role == "viewer" and self._requires_write_access:
            return "Access denied: your role (viewer) cannot perform write operations."
        return None

    def check_call(self, tool_name: str, kwargs: dict) -> str | None:
        cfg = self._tool_config.get(tool_name, {})
        for param, cap in cfg.get("max", {}).items():
            if kwargs.get(param, 0) > cap:
                return f"Guardrail violated: {param} {kwargs[param]} exceeds limit {cap}."
        for param, floor in cfg.get("min", {}).items():
            if kwargs.get(param, 0) < floor:
                return f"Guardrail violated: {param} {kwargs[param]} below minimum {floor}."
        return None


def _inject_limits(schema: dict, tool_cfg: dict) -> dict:
    if not tool_cfg:
        return schema
    schema = copy.deepcopy(schema)
    props = schema.get("function", {}).get("parameters", {}).get("properties", {})
    for param, cap in tool_cfg.get("max", {}).items():
        if param in props:
            props[param]["maximum"] = cap
    for param, floor in tool_cfg.get("min", {}).items():
        if param in props:
            props[param]["minimum"] = floor
    return schema


def extract_erp_ref(result: str, audit_keys: list[str]) -> str | None:
    if not audit_keys:
        return None
    try:
        data = json.loads(result)
        for key in audit_keys:
            if data.get(key):
                return str(data[key])
    except Exception:
        pass
    return None


def _normalize_tool_calls(tool_calls) -> list[dict]:
    return [
        {
            "id": tc.id,
            "type": "function",
            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
        }
        for tc in tool_calls
    ]


class ActionTracker:
    def __init__(self):
        self._action_id = None

    async def start(self, ctx, agent_name: str, task: str) -> int:
        action = await AgentAction.objects.acreate(
            run_id=ctx.run_id,
            source=ctx.source,
            bot_id=ctx.bot_id,
            user_id=ctx.user_id,
            intent=task[:500],
            agent_name=agent_name,
            tool_called="",
            status=AgentAction.Status.PENDING,
            input_params={"task": task},
            output={},
        )
        self._action_id = action.id
        return self._action_id

    async def fail_guardrail(self, msg: str) -> None:
        await AgentAction.objects.filter(id=self._action_id).aupdate(
            status=AgentAction.Status.FAILED,
            output={"error": msg},
        )

    async def set_erp_ref(self, ref: str) -> None:
        await AgentAction.objects.filter(id=self._action_id).aupdate(erp_record_ref=ref)

    async def complete_pending(self, summary: str, details: dict, tools_used: str, tokens: dict) -> None:
        await AgentAction.objects.filter(id=self._action_id).aupdate(
            tool_called=tools_used,
            output={"pending_summary": summary, "details": details, "tokens": tokens},
        )

    async def complete_success(self, summary: str, tools_used: str, tokens: dict, artifacts: list) -> None:
        await AgentAction.objects.filter(id=self._action_id).aupdate(
            status=AgentAction.Status.SUCCESS,
            tool_called=tools_used,
            output={"result": summary, "tokens": tokens},
            artifacts=artifacts,
        )

    async def fail(self, error: str) -> None:
        await AgentAction.objects.filter(id=self._action_id).aupdate(
            status=AgentAction.Status.FAILED,
            output={"error": error},
        )


class SubAgentRunner:
    MAX_TOOL_ITERATIONS = 10

    def __init__(self, model: str, temperature: float, max_tokens: int, guardrails: GuardrailChecker, tracker: ActionTracker, q):
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._guardrails = guardrails
        self._tracker = tracker
        self._q = q
        self._emitter = ProgressEmitter(q)

    async def run(self, template: dict, filtered_tools: dict, task: str) -> str:
        agent_name = template["name"]
        tool_config = template.get("tool_config", {})
        tool_defs = [
            _inject_limits(tool.to_schema(), tool_config.get(name, {}))
            for name, tool in filtered_tools.items()
        ]
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": template["system_prompt"]},
            {"role": "user", "content": task},
        ]
        self._emitter.dispatch_start(agent_name)

        final_text = "Task completed with no output."
        total_prompt = 0
        total_completion = 0

        try:
            for iteration in range(self.MAX_TOOL_ITERATIONS):
                if iteration == 0:
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

                if not msg.tool_calls:
                    final_text = msg.content or final_text
                    preview = final_text[:200] if isinstance(final_text, str) else str(final_text)[:200]
                    logger.info(f"[sub-agent:{agent_name}] ← {preview}")
                    break

                messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": _normalize_tool_calls(msg.tool_calls),
                })
                for tc in msg.tool_calls:
                    violation, result = await self._handle_tool_call(tc, agent_name, filtered_tools, tool_config)
                    if violation:
                        return violation
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "name": tc.function.name,
                        "content": result,
                    })

            tools_used = ", ".join(dict.fromkeys(m["name"] for m in messages if m.get("role") == "tool"))[:255]
            result = parse_agent_response(final_text, agent_name, task, self._q, fallback=final_text, action_id=self._tracker._action_id)
            tokens = {"prompt": total_prompt, "completion": total_completion, "total": total_prompt + total_completion}
            self._emitter.tokens(total_prompt, total_completion)

            if result.confirmation_required:
                await self._tracker.complete_pending(result.summary, result.details, tools_used, tokens)
            else:
                await self._tracker.complete_success(result.summary, tools_used, tokens, result.artifacts)
            return result.summary

        except Exception as e:
            await self._tracker.fail(str(e))
            raise

    async def _handle_tool_call(self, tc, agent_name: str, filtered_tools: dict, tool_config: dict) -> tuple[str | None, str]:
        tool = filtered_tools.get(tc.function.name)
        if not tool:
            return None, f"Error: Tool '{tc.function.name}' not available for {agent_name}"
        kwargs = json.loads(tc.function.arguments)
        logger.info(f"[sub-agent:{agent_name}] → {tc.function.name}({tc.function.arguments})")
        violation = self._guardrails.check_call(tc.function.name, kwargs)
        if violation:
            await self._tracker.fail_guardrail(violation)
            return violation, ""
        self._emitter.tool_call(agent_name, tc.function.name, kwargs)
        try:
            result = await asyncio.wait_for(tool.execute(**kwargs), timeout=_TOOL_TIMEOUT)
        except asyncio.TimeoutError:
            result = _unavailable()
        preview = result[:120] if isinstance(result, str) else str(result)[:120]
        logger.info(f"[sub-agent:{agent_name}] ← {tc.function.name}: {preview}")
        self._emitter.tool_result(agent_name, tc.function.name, preview)
        audit_keys = tool_config.get(tc.function.name, {}).get("audit_keys", [])
        if ref := extract_erp_ref(result, audit_keys):
            await self._tracker.set_erp_ref(ref)
        return None, result


class DispatchTool(Tool):
    _description: str = "Route a task to a specialized domain agent."

    def __init__(self, provider, registry, model: str, temperature: float, max_tokens: int):
        self._provider = provider
        self._registry = registry
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    @property
    def name(self) -> str:
        return "dispatch"

    @classmethod
    async def refresh(cls) -> None:
        agents = await AgentRegistry.aavailable(_main()._healthy_servers)
        names = ", ".join(a["name"] for a in agents) or "none"
        cls._description = (
            "Route a task to a specialized domain agent. "
            "Use this for all ERP operations instead of calling MCP tools directly. "
            f"Available agents: {names}."
        )

    @property
    def description(self) -> str:
        return self._description

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
        m = _main()
        ctx = m.get_context()

        template, status = await AgentRegistry.resolve(agent_name)
        if status == "disabled":
            return f"Error: Agent '{agent_name}' is currently disabled."
        if status == "not_found":
            available = [a["name"] for a in await AgentRegistry.aavailable(m._healthy_servers)]
            return f"Error: No agent named '{agent_name}'. Available: {available}"

        role = ctx.user_role
        guardrails = GuardrailChecker(
            template.get("tool_config", {}),
            template.get("requires_write_access", False),
        )
        if violation := guardrails.check_role(role):
            return violation

        tracker = ActionTracker()
        await tracker.start(ctx, agent_name, task)

        allowed = set(template["allowed_tools"])
        tool_config = template.get("tool_config", {})
        confirmed = "CONFIRMED" in task
        filtered = {
            name: tool
            for name, tool in self._registry._tools.items()
            if name in allowed
            and (confirmed or not tool_config.get(name, {}).get("requires_confirmation"))
        }

        current_task = asyncio.current_task()
        q = m._task_queues.get(id(current_task)) if current_task else None

        runner = SubAgentRunner(
            self._model, self._temperature, self._max_tokens,
            guardrails, tracker, q,
        )
        return await runner.run(template, filtered, task)
