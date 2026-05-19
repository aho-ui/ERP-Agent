import asyncio
from contextvars import ContextVar
from dataclasses import dataclass, replace

_task_queues: dict[int, asyncio.Queue] = {}


@dataclass
class AgentContext:
    user_role: str = "admin"
    user_id: str | None = None
    run_id: str | None = None
    source: str = "odoo"
    bot_id: str | None = None
    profile_id: str | None = None


_ctx: ContextVar[AgentContext] = ContextVar("agent_ctx", default=AgentContext())


def set_context(**kwargs) -> None:
    _ctx.set(replace(_ctx.get(), **kwargs))


def get_context() -> AgentContext:
    return _ctx.get()


def healthy_servers() -> set[str]:
    from backend.health import healthy_servers as _check
    return _check()
