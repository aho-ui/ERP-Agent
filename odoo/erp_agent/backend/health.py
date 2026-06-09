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


# #######################
# old code (replaced by the registry-based tristate probe above):
#
# import os
# import sqlite3
# import time
# import xmlrpc.client
#
# from backend.mcp_servers.seed import DB_PATH as _SQLITE_DB
#
# _CACHE_TTL = 30
# _cache: dict[str, tuple[float, bool]] = {}
#
#
# def _check_odoo() -> bool:
#     url = os.environ.get("ODOO_URL", "http://localhost:8069")
#     db = os.environ.get("ODOO_DB", "odoo_dev_18")
#     user = os.environ.get("ODOO_USER", "admin")
#     pwd = os.environ.get("ODOO_PASSWORD", "admin")
#     try:
#         common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
#         uid = common.authenticate(db, user, pwd, {})
#         return bool(uid)
#     except Exception as e:
#         logger.warning(f"[health] odoo check failed: {e}")
#         return False
#
#
# def _check_sqlite() -> bool:
#     if not _SQLITE_DB.exists():
#         return False
#     try:
#         conn = sqlite3.connect(_SQLITE_DB)
#         conn.execute("SELECT 1 FROM customers LIMIT 1")
#         conn.close()
#         return True
#     except Exception as e:
#         logger.warning(f"[health] sqlite check failed: {e}")
#         return False
#
#
# _CHECKERS = {
#     "odoo": _check_odoo,
#     "sqlite": _check_sqlite,
# }
#
#
# def healthy_servers(force: bool = False) -> set[str]:
#     healthy: set[str] = set()
#     now = time.time()
#     for name, check in _CHECKERS.items():
#         cached = _cache.get(name)
#         if not force and cached and now - cached[0] < _CACHE_TTL:
#             ok = cached[1]
#         else:
#             ok = check()
#             _cache[name] = (now, ok)
#         if ok:
#             healthy.add(name)
#     return healthy
# ###################
