from pathlib import Path
from typing import Literal

import yaml

_TEMPLATES_PATH = Path(__file__).resolve().parent / "templates.yaml"

_Status = Literal["ok", "not_found"]


class AgentRegistry:
    _cache: list[dict] | None = None

    @classmethod
    def invalidate(cls) -> None:
        cls._cache = None

    @classmethod
    def all(cls) -> list[dict]:
        if cls._cache is None:
            with open(_TEMPLATES_PATH, "r", encoding="utf-8") as f:
                cls._cache = yaml.safe_load(f)
        return cls._cache

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
