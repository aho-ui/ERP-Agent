from pathlib import Path
from typing import Literal

import yaml

from backend.agents.main import get_context

_TEMPLATES_PATH = Path(__file__).resolve().parent / "templates.yaml"

_Status = Literal["ok", "not_found"]


class AgentRegistry:
    _cache: list[dict] | None = None

    @classmethod
    def invalidate(cls) -> None:
        cls._cache = None

    @classmethod
    def _defaults_raw(cls) -> list[dict]:
        if cls._cache is None:
            with open(_TEMPLATES_PATH, "r", encoding="utf-8") as f:
                cls._cache = yaml.safe_load(f) or []
        return cls._cache

    @classmethod
    def default_names(cls) -> list[str]:
        return [a["name"] for a in cls._defaults_raw()]

    @classmethod
    def all(cls) -> list[dict]:
        ctx = get_context()
        custom = ctx.agents or []
        disabled = set(ctx.disabled_defaults or [])
        defaults = [a for a in cls._defaults_raw() if a["name"] not in disabled]
        by_name = {a["name"]: a for a in defaults}
        for a in custom:
            by_name[a["name"]] = a   # custom overrides a default of the same name
        return list(by_name.values())

    @classmethod
    async def aall(cls) -> list[dict]:
        return cls.all()

    @classmethod
    def available(cls, healthy: set[str]) -> list[dict]:
        ctx = get_context()
        enabled = set(ctx.enabled_mcps) if ctx.enabled_mcps is not None else None
        effective = healthy & enabled if enabled is not None else healthy
        return [
            a for a in cls.all()
            if all(
                t.split("_")[1] in effective
                for t in a["allowed_tools"]
                if t.startswith("mcp_")
            )
        ]

    @classmethod
    async def aavailable(cls, healthy: set[str]) -> list[dict]:
        return cls.available(healthy)

    @classmethod
    async def resolve(cls, name: str) -> tuple[dict | None, _Status]:
        for a in cls.all():
            if a["name"] == name:
                return (a, "ok")
        return (None, "not_found")
