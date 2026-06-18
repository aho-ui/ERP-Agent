import json

from odoo import http
from odoo.http import request

from ._helpers import _parse_steps, _safe_int


class ConversationsController(http.Controller):

    @http.route("/erp_agent/conversation", type="json", auth="user", methods=["POST"], csrf=False)
    def conversation(self, action="list", **kw):
        Conv = request.env["erp_agent.conversation"]
        Msg = request.env["erp_agent.message"]

        def _own(cid):
            cid = _safe_int(cid)
            if not cid:
                return Conv.browse()
            return Conv.search([("id", "=", cid)], limit=1)

        if action == "list":
            recs = Conv.search([])
            return {"conversations": [{"id": c.id, "name": c.name} for c in recs]}

        if action == "create":
            c = Conv.create({"name": kw.get("name") or "Conversation"})
            return {"ok": True, "conversation": {"id": c.id, "name": c.name}}

        if action == "rename":
            c = _own(kw.get("id"))
            if c and kw.get("name"):
                c.name = kw["name"]
            return {"ok": bool(c)}

        if action == "delete":
            c = _own(kw.get("id"))
            if c:
                c.unlink()
            return {"ok": True}

        if action == "messages":
            c = _own(kw.get("id"))
            if not c:
                return {"messages": []}
            return {"messages": [
                {
                    "role": m.role,
                    "content": m.content or "",
                    "artifacts": m.artifacts or "",
                    "steps": m.steps or "",
                    "tools_used": m.tools_used or "",
                    "agent_name": m.agent_name or "",
                }
                for m in c.message_ids
            ]}

        if action == "append":
            c = _own(kw.get("id"))
            if not c:
                return {"ok": False}
            steps_raw = kw.get("steps") or ""
            tools, agent = _parse_steps(steps_raw)
            Msg.create({
                "conversation_id": c.id,
                "role": kw.get("role") or "assistant",
                "content": kw.get("content") or "",
                "artifacts": kw.get("artifacts") or "",
                "steps": steps_raw,
                "tools_used": json.dumps(tools) if tools else "",
                "agent_name": agent or "",
            })
            return {"ok": True}

        return {"error": f"unknown action {action!r}"}
