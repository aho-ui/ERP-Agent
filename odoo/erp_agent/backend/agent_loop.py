import asyncio
# import os  # no longer needed — env-var mutation removed with _apply_env

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
# from backend import profiles  # daemon no longer caches; profile lives on ctx (per-request bundle)

__all__ = [
    "AgentContext", "get_context", "set_context", "_task_queues",
    "get_agent_loop", "apply_runtime_config", "rebuild", "_accepting",
    "set_daemon_loop", "trigger_rebuild_from_thread",
    "top_level_lock", "sync_provider", "wrap_mcp_tools",
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
    wrap_mcp_tools(agent)
    _accepting.set()
    logger.info("[agent_loop] rebuild complete")


# _ENV_KEY_MAP = {
#     "groq": "GROQ_API_KEY",
#     "openai": "OPENAI_API_KEY",
#     "anthropic": "ANTHROPIC_API_KEY",
#     "deepseek": "DEEPSEEK_API_KEY",
#     "openrouter": "OPENROUTER_API_KEY",
# }


# def _apply_env(profile: dict | None) -> None:
#     # dropped: per-call api_key is now passed directly to litellm.acompletion via ctx.profile,
#     # so mutating process-global env vars is both unnecessary and racy under multi-user load.
#     if not profile:
#         return
#     api_key = profile.get("api_key") or ""
#     model = profile.get("model") or ""
#     if api_key and model:
#         env_var = _ENV_KEY_MAP.get(model.split("/", 1)[0])
#         if env_var:
#             os.environ[env_var] = api_key


def apply_runtime_config(profile_id: str | None = None) -> None:
    # kept as a no-op for callers in controllers; profile now travels per-request via ctx
    logger.info("[agent_loop] runtime config applied (noop — bundle path)")


def _active_profile() -> dict | None:
    # reads from per-request ctx (set by chat/views.py from the bundle)
    ctx = get_context()
    return ctx.profile or None


# serializes top-level loop.provider mutation across concurrent chat requests.
# the sub-agent path is race-free (each call passes api_key/model directly to
# litellm.acompletion via ctx.profile). only the top-level dispatch picker
# needs the loop's provider, and that's what this lock protects.
top_level_lock = asyncio.Lock()


def wrap_mcp_tools(loop: AgentLoop) -> None:
    # inject `_auth_token` into every mcp_odoo_* tool call. token is signed by
    # the daemon with the gateway secret and carries the current ctx.user_id.
    # MCP forwards it verbatim to Odoo's /internal/execute, which scopes the ORM
    # call to that user via env.with_user. sqlite tools are not wrapped — demo
    # data, no per-user isolation needed.
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
            try:
                uid_int = int(uid)
            except (TypeError, ValueError):
                return _json.dumps({"error": f"invalid uid in context: {uid!r}"})
            kwargs["_auth_token"] = _sign({"uid": uid_int, "op": __op})
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

    # do NOT mutate here — top-level provider sync happens inside chat/views.py
    # under top_level_lock so concurrent requests don't race the mutation.
    return _agent_loop
