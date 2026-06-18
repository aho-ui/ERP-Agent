import asyncio

from loguru import logger
from nanobot.agent.loop import AgentLoop
from nanobot.bus.queue import MessageBus
from nanobot.providers.litellm_provider import LiteLLMProvider

from backend.config.loader import load
from backend.agents.dispatch import DispatchTool
from backend.agents.main import (
    AgentContext, get_context, set_context, _task_queues,
)
from backend.mcp import SERVERS

__all__ = [
    "AgentContext", "get_context", "set_context", "_task_queues",
    "get_agent_loop", "rebuild", "_accepting",
    "set_daemon_loop", "trigger_rebuild_from_thread",
    "top_level_lock", "sync_provider", "wrap_mcp_tools",
]

_daemon_loop: asyncio.AbstractEventLoop | None = None


def set_daemon_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _daemon_loop
    _daemon_loop = loop


def trigger_rebuild_from_thread() -> bool:
    if _daemon_loop is None or _daemon_loop.is_closed():
        return False
    asyncio.run_coroutine_threadsafe(rebuild(), _daemon_loop)
    return True

_agent_loop: AgentLoop | None = None

_accepting = asyncio.Event()
_accepting.set()
_DRAIN_TIMEOUT = 30


async def rebuild() -> None:
    _accepting.clear()
    ev = asyncio.get_event_loop()
    deadline = ev.time() + _DRAIN_TIMEOUT
    while _task_queues and ev.time() < deadline:
        await asyncio.sleep(0.2)
    agent = get_agent_loop()
    try:
        await agent.close_mcp()
    except Exception as e:
        logger.warning(f"[agent_loop] close_mcp during rebuild: {e}")
    agent._mcp_connected = False
    agent._mcp_stack = None
    await agent._connect_mcp()
    wrap_mcp_tools(agent)
    _accepting.set()
    logger.info("[agent_loop] rebuild complete")


def _active_profile() -> dict | None:
    ctx = get_context()
    return ctx.profile or None


top_level_lock = asyncio.Lock()


def wrap_mcp_tools(loop: AgentLoop) -> None:
    # sqlite intentionally unwrapped — demo data, no per-user isolation
    import json as _json
    from backend.gateway import sign as _sign
    from backend.agents.main import get_context as _get_ctx

    for name in list(loop.tools.tool_names):
        if not name.startswith("mcp_odoo_"):
            continue
        tool = loop.tools.get(name)
        if tool is None or getattr(tool, "_erp_wrapped", False):
            continue
        original_execute = tool.execute
        op_name = name[len("mcp_odoo_"):]

        async def _wrapped(__orig=original_execute, __op=op_name, **kwargs):
            ctx = _get_ctx()
            uid = ctx.user_id
            if uid is None:
                return _json.dumps({"error": "no user context for mcp_odoo call"})
            kwargs["_auth_token"] = _sign({"uid": uid, "op": __op})
            return await __orig(**kwargs)

        tool.execute = _wrapped
        tool._erp_wrapped = True
        logger.info(f"[agent_loop] wrapped {name} with gateway token injection")


def sync_provider(loop: AgentLoop) -> None:
    active = _active_profile()
    if not active or not active.get("model"):
        return
    model = active["model"]
    key = active.get("api_key") or None
    if getattr(loop, "_erp_profile", None) == (model, key):
        return
    loop.provider = LiteLLMProvider(api_key=key, api_base=None, default_model=model)
    loop.model = model
    loop._erp_profile = (model, key)
    logger.info(f"[agent_loop] provider synced to profile (model={model})")


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
        config, provider = load()

        bus = MessageBus()
        workspace = config.workspace_path
        workspace.mkdir(parents=True, exist_ok=True)

        mcp_servers = SERVERS
        logger.info(f"[agent_loop] spawning all MCP servers: {sorted(SERVERS)}")

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
