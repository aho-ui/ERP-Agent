import json

from odoo import http
from odoo.http import request

from ._helpers import (
    _agent_dict,
    _available_tool_names,
    _disabled_defaults,
    _ensure_path,
    _safe_int,
    _save_disabled_defaults,
)

_DEFAULT_PREFIX = "default:"


class AgentsController(http.Controller):

    @http.route("/erp_agent/agent", type="json", auth="user", methods=["POST"], csrf=False)
    def agent(self, action="list", **kw):
        _ensure_path()
        from backend.agents.registry import AgentRegistry
        # NO sudo: record rule scopes reads/writes to the requesting user's agents.
        # user_id defaults to env.user on create (see models/agent.py).
        Agent = request.env["erp_agent.agent"]

        if action == "list":
            disabled = set(_disabled_defaults(request.env))
            defaults = AgentRegistry._defaults_raw()
            default_items = [{
                "id": "default:" + a["name"],
                "name": a["name"],
                "description": a.get("description", ""),
                "system_prompt": a.get("system_prompt", ""),
                "allowed_tools": a.get("allowed_tools", []),
                "is_default": True,
                "active": a["name"] not in disabled,
            } for a in defaults]
            # include inactive customs too so the UI can toggle them back on
            custom_recs = Agent.with_context(active_test=False).search([])
            custom_items = [{
                **_agent_dict(r),
                "id": r.id,
                "is_default": False,
                "active": bool(r.active),
            } for r in custom_recs]
            return {
                "agents": default_items + custom_items,
                "tools": _available_tool_names(),
            }

        if action == "toggle":
            target = kw.get("id")
            value = bool(kw.get("active"))
            if isinstance(target, str) and target.startswith(_DEFAULT_PREFIX):
                name = target[len(_DEFAULT_PREFIX):]
                disabled = set(_disabled_defaults(request.env))
                if value:
                    disabled.discard(name)
                else:
                    disabled.add(name)
                _save_disabled_defaults(request.env, list(disabled))
                return {"ok": True}
            r = Agent.with_context(active_test=False).browse(_safe_int(target)).exists()
            if r:
                r.active = value
            return {"ok": bool(r)}

        if action == "create":
            r = Agent.create({
                "name": kw.get("name") or "agent",
                "description": kw.get("description") or "",
                "system_prompt": kw.get("system_prompt") or "",
                "allowed_tools": json.dumps(kw.get("allowed_tools") or []),
            })
            return {"ok": True, "agent": _agent_dict(r)}

        if action == "update":
            r = Agent.with_context(active_test=False).browse(_safe_int(kw.get("id"))).exists()
            if r:
                vals = {}
                if kw.get("name") is not None:
                    vals["name"] = kw["name"]
                if kw.get("description") is not None:
                    vals["description"] = kw["description"]
                if kw.get("system_prompt") is not None:
                    vals["system_prompt"] = kw["system_prompt"]
                if kw.get("allowed_tools") is not None:
                    vals["allowed_tools"] = json.dumps(kw.get("allowed_tools") or [])
                r.write(vals)
            return {"ok": bool(r)}

        if action == "delete":
            r = Agent.with_context(active_test=False).browse(_safe_int(kw.get("id"))).exists()
            if r:
                r.unlink()
            return {"ok": bool(r)}

        return {"error": f"unknown action {action!r}"}
