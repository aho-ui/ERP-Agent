import asyncio
import json
from typing import Any
import litellm

from loguru import logger
from nanobot.agent.loop import AgentLoop
from nanobot.agent.tools.base import Tool
from nanobot.bus.queue import MessageBus
from nanobot.providers.litellm_provider import LiteLLMProvider
from nanobot.config.loader import load_config
from nanobot.config.schema import MCPServerConfig
from MCP.config import SERVERS
from agent.utils.parsing import parse_agent_response

_agent_loop: AgentLoop | None = None
_task_queues: dict[int, asyncio.Queue] = {}

GROQ_MODEL = "groq/llama-3.3-70b-versatile"


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
        return (
            "Route a task to a specialized domain agent. "
            "Use this for all ERP operations instead of calling MCP tools directly. "
            "Available agents: purchase_agent, sales_agent, invoice_agent, inventory_agent, analytics_agent."
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
        from agent.framework.agents import AGENTS
        from agent.models import AgentAction

        template = next((a for a in AGENTS if a["name"] == agent_name), None)
        if not template:
            names = [a["name"] for a in AGENTS]
            return f"Error: No agent named '{agent_name}'. Available: {names}"

        action = await AgentAction.objects.acreate(
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

        final_text = "Task completed with no output."
        total_prompt = 0
        total_completion = 0

        try:
            for _ in range(10):
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
                            result = await tool.execute(**json.loads(tc.function.arguments))
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
                    break

            logger.info(f"[{agent_name}] raw response: {final_text[:500]}")

            tools_used = ", ".join(dict.fromkeys(m["name"] for m in messages if m.get("role") == "tool"))[:255]
            current_task = asyncio.current_task()
            q = _task_queues.get(id(current_task)) if current_task else None
            result = parse_agent_response(final_text, agent_name, task, q, fallback=final_text, action_id=action.id)

            tokens = {"prompt": total_prompt, "completion": total_completion, "total": total_prompt + total_completion}
            if q:
                q.put_nowait({"type": "progress", "content": f"Tokens: {total_prompt} prompt / {total_completion} completion / {total_prompt + total_completion} total"})

            if result.confirmation_required:
                await AgentAction.objects.filter(id=action.id).aupdate(
                    tool_called=tools_used,
                    output={"pending_summary": result.summary, "tokens": tokens},
                )
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


def _tool_call_sink(message):
    text = message.record["message"]
    if not text.startswith("Tool call: "):
        return
    task = asyncio.current_task()
    if task:
        q = _task_queues.get(id(task))
        if q:
            q.put_nowait({"type": "progress", "content": text})


logger.add(_tool_call_sink, level="INFO", format="{message}")


def get_agent_loop() -> AgentLoop:
    global _agent_loop
    if _agent_loop is None:
        config = load_config()
        provider = LiteLLMProvider(
            api_key=None,
            api_base=None,
            default_model=GROQ_MODEL,
        )
        bus = MessageBus()
        workspace = config.workspace_path
        workspace.mkdir(parents=True, exist_ok=True)

        mcp_servers = {
            name: MCPServerConfig(**cfg)
            for name, cfg in SERVERS.items()
        }

        _agent_loop = AgentLoop(
            bus=bus,
            provider=provider,
            workspace=workspace,
            mcp_servers=mcp_servers,
        )

        dispatch_tool = DispatchTool(
            provider=provider,
            registry=_agent_loop.tools,
            model=GROQ_MODEL,
            temperature=0.0,
            max_tokens=4096,
        )
        _agent_loop.tools.register(dispatch_tool)

        _orig_defs = _agent_loop.tools.get_definitions
        _agent_loop.tools.get_definitions = lambda: [
            d for d in _orig_defs()
            if not d["function"]["name"].startswith("mcp_")
        ]

    return _agent_loop
