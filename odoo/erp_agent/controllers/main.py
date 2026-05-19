import socket
import sys
from pathlib import Path

from odoo import http
from odoo.http import request

_ADDON_DIR = Path(__file__).resolve().parents[1]  # erp_agent/

MODEL_PRESETS = [
    "openai/gpt-4o-mini",
    "openai/gpt-4o",
    "openai/gpt-4-turbo",
    "anthropic/claude-3-5-sonnet-20241022",
    "anthropic/claude-3-haiku-20240307",
    "groq/llama-3.1-70b-versatile",
    "groq/qwen/qwen3-32b",
    "deepseek/deepseek-chat",
]


def _ensure_path():
    if str(_ADDON_DIR) not in sys.path:
        sys.path.insert(0, str(_ADDON_DIR))


def _is_running():
    try:
        with socket.create_connection(("127.0.0.1", 8001), timeout=1):
            return True
    except OSError:
        return False


def _apply_runtime_config(profile_id):
    try:
        from backend.agent_loop import apply_runtime_config
        apply_runtime_config(profile_id)
    except Exception:
        pass


def _mask(p):
    if not p:
        return None
    return {
        "id": p["id"],
        "name": p["name"],
        "model": p["model"],
        "api_key_set": bool(p.get("api_key")),
    }


class ErpAgentController(http.Controller):

    @http.route("/erp_agent/status", type="json", auth="user", methods=["POST"], csrf=False)
    def status(self):
        return {"running": _is_running()}

    @http.route("/erp_agent/logs", type="json", auth="user", methods=["POST"], csrf=False)
    def logs(self):
        from odoo.addons.erp_agent.server import LOG_BUFFER
        return {"logs": list(LOG_BUFFER), "running": _is_running()}

    @http.route("/erp_agent/profile", type="json", auth="user", methods=["POST"], csrf=False)
    def profile(self, action="list", **kw):
        _ensure_path()
        from backend import profiles as P

        icp = request.env["ir.config_parameter"].sudo()

        if action == "list":
            return {
                "profiles": [_mask(p) for p in P.refresh(icp)],
                "models": MODEL_PRESETS,
            }

        if action == "get":
            P.refresh(icp)
            return {"profile": _mask(P.get(kw.get("id", "")))}

        if action == "create":
            p = P.create(icp, kw.get("name", ""), kw.get("model", ""), kw.get("api_key", ""))
            _apply_runtime_config(p["id"])
            return {"ok": True, "profile": _mask(p)}

        if action == "update":
            p = P.update(
                icp,
                kw.get("id", ""),
                name=kw.get("name"),
                model=kw.get("model"),
                api_key=kw.get("api_key"),
            )
            if p:
                _apply_runtime_config(p["id"])
            return {"ok": bool(p), "profile": _mask(p)}

        if action == "delete":
            return {"ok": P.delete(icp, kw.get("id", ""))}

        return {"error": f"unknown action {action!r}"}
