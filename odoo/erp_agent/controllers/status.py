from odoo import http
from odoo.http import request

from ._helpers import (
    _KNOWN_MCPS,
    _disabled_mcps,
    _ensure_path,
    _is_running,
    _save_disabled_mcps,
)


def _is_admin():
    return request.env.user.has_group("base.group_system")


class StatusController(http.Controller):

    @http.route("/erp_agent/status", type="json", auth="user", methods=["POST"], csrf=False)
    def status(self):
        return {"running": _is_running()}

    @http.route("/erp_agent/logs", type="json", auth="user", methods=["POST"], csrf=False)
    def logs(self):
        from odoo.addons.erp_agent.server import LOG_BUFFER
        return {"logs": list(LOG_BUFFER), "running": _is_running()}

    @http.route("/erp_agent/rebuild", type="json", auth="user", methods=["POST"], csrf=False)
    def rebuild(self):
        if not _is_admin():
            return {"ok": False, "error": "admin only"}
        _ensure_path()
        from backend import agent_loop as AL
        return {"ok": AL.trigger_rebuild_from_thread()}

    @http.route("/erp_agent/health", type="json", auth="user", methods=["POST"], csrf=False)
    def health(self):
        disabled = _disabled_mcps(request.env)
        meta = {
            "known_mcps": _KNOWN_MCPS,
            "disabled_mcps": disabled,
            "is_admin": _is_admin(),
        }
        if not _is_running():
            return {"running": False, "backend_uptime": 0, "servers": {}, **meta}
        _ensure_path()
        try:
            from backend.health import snapshot
            return {"running": True, **snapshot(), **meta}
        except Exception:
            return {"running": True, "backend_uptime": 0, "servers": {}, **meta}

    @http.route("/erp_agent/mcp_toggle", type="json", auth="user", methods=["POST"], csrf=False)
    def mcp_toggle(self, name="", enabled=True, **kw):
        if not _is_admin():
            return {"ok": False, "error": "admin only"}
        if name not in _KNOWN_MCPS:
            return {"ok": False, "error": f"unknown mcp: {name!r}"}
        disabled = set(_disabled_mcps(request.env))
        if enabled:
            disabled.discard(name)
        else:
            disabled.add(name)
        _save_disabled_mcps(request.env, list(disabled))
        return {"ok": True, "disabled_mcps": sorted(disabled)}
