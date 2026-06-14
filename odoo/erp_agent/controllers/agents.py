import json

from odoo import http
from odoo.http import request

from ._helpers import (
    _agent_dict,
    _available_tool_names,
    _disabled_defaults,
    _ensure_path,
    _save_disabled_defaults,
)


class AgentsController(http.Controller):

    @http.route("/erp_agent/agent", type="json", auth="user", methods=["POST"], csrf=False)
    def agent(self, action="list", **kw):
        _ensure_path()
        from backend.agents.registry import AgentRegistry
        # NO sudo: record rule scopes reads/writes to the requesting user's agents.
        # user_id defaults to env.user on create (see models/agent.py).
        Agent = request.env["erp_agent.agent"]

        if action == "list":
            # _warm_agents(request.env)  # daemon no longer caches — bundle path
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
            # default toggles use the "default:<name>" id from the list payload
            if isinstance(target, str) and target.startswith("default:"):
                name = target.split(":", 1)[1]
                disabled = set(_disabled_defaults(request.env))
                if value:
                    disabled.discard(name)
                else:
                    disabled.add(name)
                _save_disabled_defaults(request.env, list(disabled))
                # _warm_agents(request.env)  # daemon no longer caches — bundle path
                return {"ok": True}
            try:
                r = Agent.with_context(active_test=False).browse(int(target)).exists()
            except (TypeError, ValueError):
                r = Agent.browse()
            if r:
                r.active = value
                # _warm_agents(request.env)  # daemon no longer caches — bundle path
            return {"ok": bool(r)}

        if action == "create":
            r = Agent.create({
                "name": kw.get("name") or "agent",
                "description": kw.get("description") or "",
                "system_prompt": kw.get("system_prompt") or "",
                "allowed_tools": json.dumps(kw.get("allowed_tools") or []),
            })
            # _warm_agents(request.env)  # daemon no longer caches — bundle path
            return {"ok": True, "agent": _agent_dict(r)}

        if action == "update":
            try:
                r = Agent.with_context(active_test=False).browse(int(kw.get("id"))).exists()
            except (TypeError, ValueError):
                r = Agent.browse()
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
                # _warm_agents(request.env)  # daemon no longer caches — bundle path
            return {"ok": bool(r)}

        if action == "delete":
            try:
                r = Agent.with_context(active_test=False).browse(int(kw.get("id"))).exists()
            except (TypeError, ValueError):
                r = Agent.browse()
            if r:
                r.unlink()
                # _warm_agents(request.env)  # daemon no longer caches — bundle path
            return {"ok": True}

        return {"error": f"unknown action {action!r}"}
