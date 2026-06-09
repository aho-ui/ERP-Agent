from pathlib import Path
from typing import Literal

import yaml

_TEMPLATES_PATH = Path(__file__).resolve().parent / "templates.yaml"

_Status = Literal["ok", "not_found"]


class AgentRegistry:
    _cache: list[dict] | None = None
    _custom: list[dict] = []                  # active customs (warmed by controller)
    _disabled_defaults: set[str] = set()      # default agent names turned OFF globally

    @classmethod
    def invalidate(cls) -> None:
        cls._cache = None

    @classmethod
    def set_state(cls, custom: list[dict], disabled_defaults: list[str]) -> None:
        cls._custom = custom or []
        cls._disabled_defaults = set(disabled_defaults or [])

    @classmethod
    def set_custom(cls, agents: list[dict]) -> None:
        cls._custom = agents or []

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
        defaults = [a for a in cls._defaults_raw() if a["name"] not in cls._disabled_defaults]
        by_name = {a["name"]: a for a in defaults}
        for a in cls._custom:
            by_name[a["name"]] = a   # custom overrides a default of the same name
        return list(by_name.values())

    @classmethod
    async def aall(cls) -> list[dict]:
        return cls.all()

    @classmethod
    def available(cls, healthy: set[str]) -> list[dict]:
        return [
            a for a in cls.all()
            if all(
                t.split("_")[1] in healthy
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
