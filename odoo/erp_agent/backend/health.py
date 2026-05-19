import os
import sqlite3
import time
import xmlrpc.client

from loguru import logger

from backend.mcp_servers.seed import DB_PATH as _SQLITE_DB

_CACHE_TTL = 30
_cache: dict[str, tuple[float, bool]] = {}


def _check_odoo() -> bool:
    url = os.environ.get("ODOO_URL", "http://localhost:8069")
    db = os.environ.get("ODOO_DB", "odoo_dev_18")
    user = os.environ.get("ODOO_USER", "admin")
    pwd = os.environ.get("ODOO_PASSWORD", "admin")
    try:
        common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
        uid = common.authenticate(db, user, pwd, {})
        return bool(uid)
    except Exception as e:
        logger.warning(f"[health] odoo check failed: {e}")
        return False


def _check_sqlite() -> bool:
    if not _SQLITE_DB.exists():
        return False
    try:
        conn = sqlite3.connect(_SQLITE_DB)
        conn.execute("SELECT 1 FROM customers LIMIT 1")
        conn.close()
        return True
    except Exception as e:
        logger.warning(f"[health] sqlite check failed: {e}")
        return False


_CHECKERS = {
    "odoo": _check_odoo,
    "sqlite": _check_sqlite,
}


def healthy_servers(force: bool = False) -> set[str]:
    healthy: set[str] = set()
    now = time.time()
    for name, check in _CHECKERS.items():
        cached = _cache.get(name)
        if not force and cached and now - cached[0] < _CACHE_TTL:
            ok = cached[1]
        else:
            ok = check()
            _cache[name] = (now, ok)
        if ok:
            healthy.add(name)
    return healthy
