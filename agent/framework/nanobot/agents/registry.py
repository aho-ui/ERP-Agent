from typing import Literal

from agent.models import AgentTemplate


_Status = Literal["ok", "disabled", "not_found"]


def _to_dict(t) -> dict:
    return {
        "name": t.name,
        "description": t.description,
        "system_prompt": t.instructions,
        "allowed_tools": t.allowed_tools,
        "tool_config": t.tool_config,
        "requires_write_access": t.requires_write_access,
        "is_active": t.is_active,
        "is_default": t.is_default,
    }


# `a` prefix = async (Django ORM convention). all/available are sync; aall/aavailable are async.
class AgentRegistry:
    _cache: list[dict] | None = None

    @classmethod
    def invalidate(cls) -> None:
        cls._cache = None

    @classmethod
    def all(cls) -> list[dict]:
        if cls._cache is None:
            cls._cache = [_to_dict(t) for t in AgentTemplate.objects.all()]
        return cls._cache

    @classmethod
    async def aall(cls) -> list[dict]:
        if cls._cache is None:
            cls._cache = [_to_dict(t) async for t in AgentTemplate.objects.all()]
        return cls._cache

    @classmethod
    def available(cls, healthy: set[str]) -> list[dict]:
        return [
            a for a in cls.all()
            if a["is_active"] and all(
                t.split("_")[1] in healthy
                for t in a["allowed_tools"]
                if t.startswith("mcp_")
            )
        ]

    @classmethod
    async def aavailable(cls, healthy: set[str]) -> list[dict]:
        agents = await cls.aall()
        return [
            a for a in agents
            if a["is_active"] and all(
                t.split("_")[1] in healthy
                for t in a["allowed_tools"]
                if t.startswith("mcp_")
            )
        ]

    @classmethod
    async def resolve(cls, name: str) -> tuple[dict | None, _Status]:
        for a in await cls.aall():
            if a["name"] == name:
                return (a, "ok" if a["is_active"] else "disabled")
        return (None, "not_found")
