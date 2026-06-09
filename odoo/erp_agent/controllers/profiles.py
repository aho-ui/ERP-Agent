from odoo import http
from odoo.http import request

from ._helpers import MODEL_PRESETS, _apply_runtime_config, _ensure_path, _mask


class ProfilesController(http.Controller):

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
