import asyncio
import os

from loguru import logger
from nanobot.agent.loop import AgentLoop
from nanobot.bus.queue import MessageBus
from nanobot.providers.litellm_provider import LiteLLMProvider

from backend.config.loader import load
from backend.agents.dispatch import DispatchTool
from backend.agents.main import (
    AgentContext, get_context, set_context, _task_queues,
)
# from backend.health import healthy_servers   # moved to monitor; loop no longer filters
from backend.mcp import SERVERS
from backend import profiles

__all__ = [
    "AgentContext", "get_context", "set_context", "_task_queues",
    "get_agent_loop", "apply_runtime_config", "rebuild", "_accepting",
    "set_daemon_loop", "trigger_rebuild_from_thread",
]

_daemon_loop: asyncio.AbstractEventLoop | None = None


def set_daemon_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _daemon_loop
    _daemon_loop = loop


def trigger_rebuild_from_thread() -> bool:
    # called from the Odoo controller thread; schedules rebuild on the
    # daemon's loop. Returns False if the daemon isn't up yet.
    if _daemon_loop is None or _daemon_loop.is_closed():
        return False
    asyncio.run_coroutine_threadsafe(rebuild(), _daemon_loop)
    return True

_agent_loop: AgentLoop | None = None

_accepting = asyncio.Event()
_accepting.set()                  # cleared while a rebuild drains in-flight requests
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
    _accepting.set()
    logger.info("[agent_loop] rebuild complete")


_ENV_KEY_MAP = {
    "groq": "GROQ_API_KEY",
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
}


def _apply_env(profile: dict | None) -> None:
    if not profile:
        return
    api_key = profile.get("api_key") or ""
    model = profile.get("model") or ""
    if api_key and model:
        env_var = _ENV_KEY_MAP.get(model.split("/", 1)[0])
        if env_var:
            os.environ[env_var] = api_key


def apply_runtime_config(profile_id: str | None = None) -> None:
    _apply_env(profiles.get(profile_id) if profile_id else None)

    # global _agent_loop
    # _agent_loop = None
    logger.info("[agent_loop] runtime config applied")


def _active_profile() -> dict | None:
    ctx = get_context()
    active = profiles.get(ctx.profile_id) if ctx.profile_id else None
    if active is None:
        allp = profiles.list_profiles()
        active = allp[0] if allp else None
    return active


def _sync_provider(loop: AgentLoop) -> None:
    active = _active_profile()
    if not active or not active.get("model"):
        return
    _apply_env(active)
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
        active = _active_profile()
        _apply_env(active)

        config, provider = load()
        if active and active.get("model"):
            config.agents.defaults.model = active["model"]
            provider = LiteLLMProvider(
                api_key=active.get("api_key") or None,
                api_base=None,
                default_model=active["model"],
            )

        bus = MessageBus()
        workspace = config.workspace_path
        workspace.mkdir(parents=True, exist_ok=True)

        # healthy = healthy_servers(force=True)
        # mcp_servers = {name: cfg for name, cfg in SERVERS.items() if name in healthy}
        # logger.info(f"[agent_loop] healthy MCP servers: {sorted(healthy) or 'none'}")
        # pass SERVERS by reference (no copy) so reload_odoo_env() mutations
        # to SERVERS["odoo"].env are visible when rebuild() re-spawns
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

    _sync_provider(_agent_loop)
    return _agent_loop
