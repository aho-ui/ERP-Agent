from odoo import http

from ._helpers import _ensure_path, _is_running


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
        _ensure_path()
        from backend import agent_loop as AL
        return {"ok": AL.trigger_rebuild_from_thread()}

    @http.route("/erp_agent/health", type="json", auth="user", methods=["POST"], csrf=False)
    def health(self):
        if not _is_running():
            return {"running": False, "backend_uptime": 0, "servers": {}}
        _ensure_path()
        try:
            from backend.health import snapshot
            return {"running": True, **snapshot()}
        except Exception:
            return {"running": True, "backend_uptime": 0, "servers": {}}
