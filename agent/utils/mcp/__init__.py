import json
import os
import re
from pathlib import Path

import yaml
from nanobot.config.schema import MCPServerConfig

_HERE = Path(__file__).parent


def _expand_env(v):
    if isinstance(v, str):
        return re.sub(r"\$\{(\w+)\}", lambda m: os.getenv(m.group(1), ""), v)
    if isinstance(v, list):
        return [_expand_env(x) for x in v]
    if isinstance(v, dict):
        return {k: _expand_env(x) for k, x in v.items()}
    return v


def _load_servers() -> dict[str, MCPServerConfig]:
    path = _HERE / "servers.yaml"
    if not path.exists():
        return {}
    with path.open() as f:
        data = yaml.safe_load(f) or []
    result: dict[str, MCPServerConfig] = {}
    for entry in data:
        name = entry.pop("name")
        result[name] = MCPServerConfig(**_expand_env(entry))
    return result


SERVERS: dict[str, MCPServerConfig] = _load_servers()

_health_cache: dict[str, bool] = {}


def _registry():
    # lazy: avoid circular import — main.py imports from this module too
    from agent.framework.nanobot import main
    loop = main.get_agent_loop()
    return loop.tools._tools


def healthy_servers() -> set[str]:
    # OLD: scanned tool registry
    # if not SERVERS:
    #     return set()
    # try:
    #     tools = _registry()
    # except Exception:
    #     return set()
    # names: set[str] = set()
    # for tool_name in tools:
    #     if tool_name.startswith("mcp_"):
    #         parts = tool_name.split("_", 2)
    #         if len(parts) >= 2:
    #             names.add(parts[1])
    # return names
    return {name for name, ok in _health_cache.items() if ok}


async def _call_tool(server: str, tool: str):
    full = f"mcp_{server}_{tool}"
    try:
        handle = _registry().get(full)
    except Exception:
        return None
    if not handle:
        return None
    try:
        raw = await handle.execute()
        return json.loads(raw) if isinstance(raw, str) else raw
    except Exception:
        return None


async def health() -> dict[str, bool]:
    results: dict[str, bool] = {}
    for name in SERVERS:
        data = await _call_tool(name, "health")
        results[name] = bool(data and data.get("ok"))
    _health_cache.clear()
    _health_cache.update(results)
    return results


async def dashboard_stats(name: str) -> dict | None:
    return await _call_tool(name, "dashboard_stats")
