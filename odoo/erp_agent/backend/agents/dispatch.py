import asyncio
import json
from typing import Any

import litellm
from loguru import logger
from nanobot.agent.tools.base import Tool

from backend.parsing import parse_agent_response
from backend.agents.registry import AgentRegistry

_TOOL_TIMEOUT = 60


def _unavailable() -> str:
    return "Tool is unavailable, please apologize to the user and ask them to try again later."


def _main():
    # lazy: dispatch is imported during agents.main module load — circular
    from backend.agents import main
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
        self._emit(f"[{agent_name}] -> {tool_name}({json.dumps(kwargs)})")

    def tool_result(self, agent_name: str, tool_name: str, preview: str) -> None:
        self._emit(f"[{agent_name}] <- {tool_name}: {preview}")

    def tokens(self, prompt: int, completion: int) -> None:
        self._emit(f"Tokens: {prompt} prompt / {completion} completion / {prompt + completion} total")


def _normalize_tool_calls(tool_calls) -> list[dict]:
    return [
        {
            "id": tc.id,
            "type": "function",
            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
        }
        for tc in tool_calls
    ]


class SubAgentRunner:
    MAX_TOOL_ITERATIONS = 10

    def __init__(self, model: str, temperature: float, max_tokens: int, q):
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._q = q
        self._emitter = ProgressEmitter(q)

    async def run(self, template: dict, filtered_tools: dict, task: str) -> str:
        agent_name = template["name"]
        tool_defs = [tool.to_schema() for tool in filtered_tools.values()]
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": template["system_prompt"]},
            {"role": "user", "content": task},
        ]
        self._emitter.dispatch_start(agent_name)

        ctx = _main().get_context()
        active = ctx.profile or {}
        model = active.get("model") or self._model
        api_key = active.get("api_key") or None

        final_text = "Task completed with no output."
        total_prompt = 0
        total_completion = 0
        prev_call_sig: tuple | None = None  # (sorted tool name+args) to detect a stuck retry

        for iteration in range(self.MAX_TOOL_ITERATIONS):
            if iteration == 0:
                logger.info(f"[sub-agent:{agent_name}] start (model={model})")
            response = await litellm.acompletion(
                model=model,
                messages=messages,
                tools=tool_defs,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
                api_key=api_key,
            )
            total_prompt += response.usage.prompt_tokens or 0
            total_completion += response.usage.completion_tokens or 0
            msg = response.choices[0].message

            if not msg.tool_calls:
                final_text = msg.content or final_text
                preview = final_text[:200] if isinstance(final_text, str) else str(final_text)[:200]
                logger.info(f"[sub-agent:{agent_name}] <- {preview}")
                break

            # stuck-retry guard: same tool(s) + same args as last iteration -> stop
            call_sig = tuple(sorted((tc.function.name, tc.function.arguments) for tc in msg.tool_calls))
            if call_sig == prev_call_sig:
                logger.warning(f"[sub-agent:{agent_name}] repeated identical tool call; stopping early")
                final_text = msg.content or "Stopped: the same tool call was failing repeatedly."
                break
            prev_call_sig = call_sig

            messages.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": _normalize_tool_calls(msg.tool_calls),
            })
            for tc in msg.tool_calls:
                result = await self._handle_tool_call(tc, agent_name, filtered_tools)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": tc.function.name,
                    "content": result,
                })

        result = parse_agent_response(final_text, agent_name, task, self._q, fallback=final_text)
        self._emitter.tokens(total_prompt, total_completion)
        return result.summary

    async def _handle_tool_call(self, tc, agent_name: str, filtered_tools: dict) -> str:
        tool = filtered_tools.get(tc.function.name)
        if not tool:
            return f"Error: Tool '{tc.function.name}' not available for {agent_name}"
        kwargs = json.loads(tc.function.arguments)
        logger.info(f"[sub-agent:{agent_name}] -> {tc.function.name}({tc.function.arguments})")
        self._emitter.tool_call(agent_name, tc.function.name, kwargs)
        try:
            result = await asyncio.wait_for(tool.execute(**kwargs), timeout=_TOOL_TIMEOUT)
        except asyncio.TimeoutError:
            result = _unavailable()
        preview = result[:120] if isinstance(result, str) else str(result)[:120]
        logger.info(f"[sub-agent:{agent_name}] <- {tc.function.name}: {preview}")
        self._emitter.tool_result(agent_name, tc.function.name, preview)
        return result


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

    @property
    def description(self) -> str:
        agents = AgentRegistry.available(_main().healthy_servers())
        names = ", ".join(a["name"] for a in agents) or "none"
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
        m = _main()

        template, status = await AgentRegistry.resolve(agent_name)
        if status == "not_found":
            available = [a["name"] for a in await AgentRegistry.aavailable(m.healthy_servers())]
            return f"Error: No agent named '{agent_name}'. Available: {available}"

        allowed = set(template["allowed_tools"])
        filtered = {
            name: tool
            for name, tool in self._registry._tools.items()
            if name in allowed
        }

        current_task = asyncio.current_task()
        q = m._task_queues.get(id(current_task)) if current_task else None

        runner = SubAgentRunner(
            self._model, self._temperature, self._max_tokens, q,
        )
        return await runner.run(template, filtered, task)
