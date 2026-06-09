from odoo import http
from odoo.http import request

from ._helpers import _ensure_path


class OdooBackendController(http.Controller):

    @http.route("/erp_agent/odoo_backend", type="json", auth="user", methods=["POST"], csrf=False)
    def odoo_backend(self, action="get", **kw):
        _ensure_path()
        from backend import odoo_backend as OB
        from backend import mcp as MCP
        from backend import agent_loop as AL
        icp = request.env["ir.config_parameter"].sudo()

        if action == "get":
            cfg = OB.load() or {}
            # default DB to the request's current Odoo DB so the user doesn't
            # have to type it most of the time
            return {
                "url": cfg.get("url") or icp.get_param("erp_agent.odoo_url", "http://localhost:8069"),
                "db": cfg.get("db") or icp.get_param("erp_agent.odoo_db", request.env.cr.dbname),
                "user": cfg.get("user") or icp.get_param("erp_agent.odoo_user", ""),
                "has_password": OB.has_password(),
            }

        if action == "save":
            url = (kw.get("url") or "").strip()
            db = (kw.get("db") or "").strip()
            user = (kw.get("user") or "").strip()
            # blank password = keep existing one (same convention as profiles)
            password = kw.get("password") or ""
            if not password:
                password = (OB.load() or {}).get("password", "")
            OB.save(url, db, user, password)
            icp.set_param("erp_agent.odoo_url", url)
            icp.set_param("erp_agent.odoo_db", db)
            icp.set_param("erp_agent.odoo_user", user)
            MCP.reload_odoo_env()
            rebuilt = AL.trigger_rebuild_from_thread()
            return {"ok": True, "rebuilt": rebuilt}

        return {"error": f"unknown action {action!r}"}
