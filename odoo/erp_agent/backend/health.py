import json
import time

from loguru import logger

from backend.mcp import SERVERS

# 0 = subprocess dead/unreachable, 1 = alive but DB down, 2 = healthy
_START = time.time()
_HISTORY_MAX = 120                          # samples kept per server (~1h at the 30s tick)
_servers: dict[str, dict] = {}              # name -> {state, reason, since, history:[(ts,state)]}


async def probe(registry, server: str) -> tuple[int, str]:
    tool = registry.get(f"mcp_{server}_health")
    if tool is None:
        return 0, "subprocess not connected"
    raw = await tool.execute()
    if not isinstance(raw, str) or raw.startswith("(MCP tool call"):
        return 0, raw if isinstance(raw, str) else "dead session"
    try:
        data = json.loads(raw)
    except Exception:
        return 1, "malformed health response"
    state = 2 if data.get("status") == "UP" else 1
    return state, data.get("reason", "")


async def probe_all(registry) -> dict[str, int]:
    now = time.time()
    out: dict[str, int] = {}
    for name in SERVERS:
        state, reason = await probe(registry, name)
        rec = _servers.get(name)
        since = now if (rec is None or rec["state"] != state) else rec["since"]
        history = (rec["history"] if rec else [])
        history = (history + [(now, state)])[-_HISTORY_MAX:]
        _servers[name] = {"state": state, "reason": reason, "since": since, "history": history}
        out[name] = state
    logger.debug(f"[health] states: {out}")
    return out


def healthy_servers(force: bool = False) -> set[str]:
    return {name for name, rec in _servers.items() if rec["state"] == 2}


def snapshot() -> dict:
    now = time.time()
    return {
        "backend_uptime": now - _START,
        "servers": {
            name: {
                "state": rec["state"],
                "reason": rec["reason"],
                "uptime": (now - rec["since"]) if rec["state"] == 2 else 0,
                "history": [{"ago": round(now - ts), "state": st} for ts, st in rec["history"]],
            }
            for name, rec in _servers.items()
        },
    }