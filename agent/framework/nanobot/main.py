import asyncio
from contextvars import ContextVar

from loguru import logger
from nanobot.agent.loop import AgentLoop
from nanobot.bus.queue import MessageBus
from nanobot.config.schema import MCPServerConfig
from MCP.config import SERVERS
from MCP.utils.health import check_all as _check_mcp_health
from agent.framework.nanobot.config.loader import load
from agent.framework.nanobot.utils.dispatch import DispatchTool

_agent_loop: AgentLoop | None = None
_task_queues: dict[int, asyncio.Queue] = {}
_healthy_servers: set[str] = set()

_user_role: ContextVar[str] = ContextVar("user_role", default="viewer")
_user_id: ContextVar[str | None] = ContextVar("user_id", default=None)


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
    global _agent_loop, _healthy_servers
    if _agent_loop is None:
        config, provider = load()
        bus = MessageBus()
        workspace = config.workspace_path
        workspace.mkdir(parents=True, exist_ok=True)

        health = _check_mcp_health()
        _healthy_servers = {name for name, ok in health.items() if ok}

        mcp_servers = {
            name: MCPServerConfig(**cfg)
            for name, cfg in SERVERS.items()
            if name in _healthy_servers
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
            model=config.agents.defaults.model,
            temperature=config.agents.defaults.temperature,
            max_tokens=config.agents.defaults.max_tokens,
        )
        _agent_loop.tools.register(dispatch_tool)

        _orig_defs = _agent_loop.tools.get_definitions
        _agent_loop.tools.get_definitions = lambda: [
            d for d in _orig_defs() if d["function"]["name"] == "dispatch"
        ]

    return _agent_loop
