from odoo import http
from odoo.http import request

from ._helpers import MODEL_PRESETS, _ensure_path, _mask, _safe_int


def _to_dict(rec):
    return {
        "id": str(rec.id),
        "name": rec.name or "",
        "model": rec.model or "",
        "api_key": rec.api_key or "",
    }


class ProfilesController(http.Controller):

    @http.route("/erp_agent/profile", type="json", auth="user", methods=["POST"], csrf=False)
    def profile(self, action="list", **kw):
        _ensure_path()
        # NO sudo: record rule scopes to current user's profiles only.
        Profile = request.env["erp_agent.profile"]

        if action == "list":
            return {
                "profiles": [_mask(_to_dict(r)) for r in Profile.search([])],
                "models": MODEL_PRESETS,
            }

        if action == "get":
            rec = Profile.browse(_safe_int(kw.get("id"))).exists()
            return {"profile": _mask(_to_dict(rec)) if rec else None}

        if action == "create":
            rec = Profile.create({
                "name": kw.get("name", ""),
                "model": kw.get("model", ""),
                "api_key": kw.get("api_key", ""),
            })
            return {"ok": True, "profile": _mask(_to_dict(rec))}

        if action == "update":
            rec = Profile.browse(_safe_int(kw.get("id"))).exists()
            if rec:
                vals = {}
                if kw.get("name") is not None:
                    vals["name"] = kw["name"]
                if kw.get("model") is not None:
                    vals["model"] = kw["model"]
                # blank api_key = keep existing
                if kw.get("api_key"):
                    vals["api_key"] = kw["api_key"]
                if vals:
                    rec.write(vals)
            return {"ok": bool(rec), "profile": _mask(_to_dict(rec)) if rec else None}

        if action == "delete":
            rec = Profile.browse(_safe_int(kw.get("id"))).exists()
            if rec:
                rec.unlink()
            return {"ok": bool(rec)}

        return {"error": f"unknown action {action!r}"}
