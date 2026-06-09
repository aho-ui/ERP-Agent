import json
import tempfile
from pathlib import Path

# Daemon-readable creds for the odoo MCP subprocess. Same fallback pattern as
# demo.db: try the addon dir first, fall back to the OS temp dir if Odoo's
# service user can't write there.
_ADDON_DIR = Path(__file__).resolve().parent.parent   # odoo/erp_agent/
_FILENAME = ".odoo_backend.json"


def _resolve_path() -> Path:
    try:
        probe = _ADDON_DIR / ".write_test"
        probe.write_text("")
        probe.unlink()
        return _ADDON_DIR / _FILENAME
    except OSError:
        return Path(tempfile.gettempdir()) / ("erp_agent_" + _FILENAME)


PATH = _resolve_path()


def load() -> dict:
    if not PATH.exists():
        return {}
    try:
        data = json.loads(PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def save(url: str, db: str, user: str, password: str) -> None:
    PATH.write_text(json.dumps({
        "url": url or "",
        "db": db or "",
        "user": user or "",
        "password": password or "",
    }), encoding="utf-8")


def has_password() -> bool:
    return bool((load() or {}).get("password"))
