import json
from datetime import datetime, timedelta

from odoo import fields, http
from odoo.http import request

from ._helpers import (
    _CALL_LINE_RE,
    _RESULT_LINE_RE,
    _agent_dict,
    _disabled_defaults,
    _ensure_path,
)


class ToolsController(http.Controller):

    @http.route("/erp_agent/tools", type="json", auth="user", methods=["POST"], csrf=False)
    def tools(self, **kw):
        _ensure_path()
        from backend import agent_loop as AL
        from backend.agents.registry import AgentRegistry

        # live tool metadata from the connected MCP wrappers
        loop = AL._agent_loop
        live: dict = {}
        if loop is not None:
            for name in loop.tools.tool_names:
                if not name.startswith("mcp_"):
                    continue
                t = loop.tools.get(name)
                if not t:
                    continue
                schema = t.parameters or {}
                props = (schema.get("properties") or {}) if isinstance(schema, dict) else {}
                required = set(schema.get("required") or []) if isinstance(schema, dict) else set()
                params = []
                for pname, pdef in props.items():
                    params.append({
                        "name": pname,
                        "type": pdef.get("type", "any") if isinstance(pdef, dict) else "any",
                        "default": pdef.get("default") if isinstance(pdef, dict) else None,
                        "required": pname in required,
                    })
                live[name] = {
                    "description": getattr(t, "description", "") or "",
                    "params": params,
                }

        # which agents allow each tool (defaults + active customs, read directly from Odoo)
        # _warm_agents(request.env)
        # tool_agents: dict = {}
        # for ag in AgentRegistry.all():
        #     for tname in ag.get("allowed_tools") or []:
        #         tool_agents.setdefault(tname, []).append(ag["name"])
        disabled = set(_disabled_defaults(request.env))
        defaults = [a for a in AgentRegistry._defaults_raw() if a["name"] not in disabled]
        customs = [_agent_dict(r) for r in request.env["erp_agent.agent"].search([])]
        by_name = {a["name"]: a for a in defaults}
        for a in customs:
            by_name[a["name"]] = a
        tool_agents: dict = {}
        for ag in by_name.values():
            for tname in ag.get("allowed_tools") or []:
                tool_agents.setdefault(tname, []).append(ag["name"])

        # DB-derived stats: aggregate over the last 90d
        Msg = request.env["erp_agent.message"].sudo()
        cutoff = datetime.now() - timedelta(days=90)
        msgs = Msg.search([
            ("role", "=", "assistant"),
            ("create_date", ">=", fields.Datetime.to_string(cutoff)),
        ], order="create_date desc", limit=5000)

        counts: dict = {}
        last_ts: dict = {}
        last_call: dict = {}
        for m in msgs:
            try:
                used = json.loads(m.tools_used or "[]")
            except Exception:
                used = []
            if not used:
                continue
            ts = m.create_date
            try:
                steps = json.loads(m.steps or "[]")
            except Exception:
                steps = []
            for t in used:
                counts[t] = counts.get(t, 0) + 1
                # latest msg wins (msgs is ordered desc by create_date)
                if t not in last_ts:
                    last_ts[t] = ts
                    args = ""
                    preview = ""
                    for s in steps:
                        if not isinstance(s, str):
                            continue
                        mc = _CALL_LINE_RE.match(s)
                        if mc and mc.group(2) == t and not args:
                            args = mc.group(3)
                        mr = _RESULT_LINE_RE.match(s)
                        if mr and mr.group(2) == t and not preview:
                            preview = mr.group(3)
                        if args and preview:
                            break
                    last_call[t] = {
                        "ts": fields.Datetime.to_string(ts) if ts else "",
                        "agent": m.agent_name or "",
                        "args": args,
                        "result_preview": preview[:300] if preview else "",
                    }

        def _ago(ts):
            if not ts:
                return "—"
            delta = datetime.now() - ts
            s = int(delta.total_seconds())
            if s < 60:
                return f"{s}s ago"
            if s < 3600:
                return f"{s // 60}m ago"
            if s < 86400:
                return f"{s // 3600}h ago"
            return f"{s // 86400}d ago"

        # build groups: every live tool + any historical tool name (in case it's no longer registered)
        all_names = set(live.keys()) | set(counts.keys())
        groups: dict = {}
        for name in all_names:
            parts = name.split("_", 2)
            server = parts[1] if name.startswith("mcp_") and len(parts) >= 2 else "other"
            meta = live.get(name, {"description": "(not currently registered)", "params": []})
            groups.setdefault(server, []).append({
                "name": name,
                "description": meta["description"],
                "params": meta["params"],
                "agents": sorted(set(tool_agents.get(name, []))),
                "calls": counts.get(name, 0),
                "last": _ago(last_ts.get(name)),
                "last_call": last_call.get(name),
            })
        for s in groups:
            groups[s].sort(key=lambda r: -r["calls"])

        return {"groups": groups}
