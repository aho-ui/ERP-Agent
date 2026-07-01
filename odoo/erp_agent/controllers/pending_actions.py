import json
import logging

from odoo import fields, http
from odoo.http import request

from ._helpers import _ensure_path, _safe_int

_logger = logging.getLogger(__name__)
_TOOL_PREFIX = "mcp_odoo_"


def _serialize(row):
    return {
        "id": row.id,
        "user_id": row.user_id.id,
        "user_name": row.user_id.name,
        "conversation_id": row.conversation_id.id,
        "conversation_name": row.conversation_id.name or "",
        "tool_name": row.tool_name,
        "payload": row.payload_json or "",
        "status": row.status,
        "created_at": fields.Datetime.to_string(row.created_at) if row.created_at else "",
        "acted_at": fields.Datetime.to_string(row.acted_at) if row.acted_at else "",
        "result": row.result or "",
        "error": row.error or "",
    }


def _execute_tool(tool_name, payload, uid):
    _ensure_path()
    from backend.gateway import sign
    import backend.mcp_servers.odoo as odoo_tools

    if not tool_name.startswith(_TOOL_PREFIX):
        return False, f"unsupported tool: {tool_name}"
    op = tool_name[len(_TOOL_PREFIX):]
    fn = getattr(odoo_tools, op, None)
    if not callable(fn):
        return False, f"unknown tool function: {op}"

    token = sign({"uid": uid, "op": op})
    try:
        raw = fn(auth_token=token, **(payload or {}))
    except Exception as e:
        _logger.exception("[pending_actions] %s failed", tool_name)
        return False, str(e)

    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return True, str(raw)
    if isinstance(parsed, dict) and parsed.get("error"):
        return False, parsed["error"]
    return True, raw


def _append_message(conv, content):
    request.env["erp_agent.message"].create({
        "conversation_id": conv.id,
        "role": "assistant",
        "content": content,
        "agent_name": "approval",
    })


class PendingActionsController(http.Controller):

    @http.route("/erp_agent/pending_actions", type="json", auth="user", methods=["POST"], csrf=False)
    def pending_actions(self, action="list", **kw):
        Pending = request.env["erp_agent.pending_action"]
        Conv = request.env["erp_agent.conversation"]

        if action == "list":
            domain = []
            status = kw.get("status")
            if status:
                domain.append(("status", "=", status))
            conv_id = _safe_int(kw.get("conversation_id"))
            if conv_id:
                domain.append(("conversation_id", "=", conv_id))
            rows = Pending.search(domain, limit=_safe_int(kw.get("limit"), 100))
            return {"actions": [_serialize(r) for r in rows]}

        if action == "count":
            domain = [("status", "=", "pending")]
            return {"count": Pending.search_count(domain)}

        if action == "create":
            conv = Conv.search([("id", "=", _safe_int(kw.get("conversation_id")))], limit=1)
            if not conv:
                return {"ok": False, "error": "unknown conversation"}
            tool_name = kw.get("tool_name") or ""
            if not tool_name:
                return {"ok": False, "error": "tool_name required"}
            payload = kw.get("payload")
            if isinstance(payload, dict):
                payload_json = json.dumps(payload)
            elif isinstance(payload, str):
                payload_json = payload
            else:
                payload_json = json.dumps(payload or {})
            row = Pending.create({
                "conversation_id": conv.id,
                "tool_name": tool_name,
                "payload_json": payload_json,
            })
            return {"ok": True, "action": _serialize(row)}

        if action == "approve":
            if not request.env.user.has_group("base.group_system"):
                return {"ok": False, "error": "admin only"}
            row = Pending.search([("id", "=", _safe_int(kw.get("id")))], limit=1)
            if not row:
                return {"ok": False, "error": "not found"}
            if row.status != "pending":
                return {"ok": False, "error": f"already {row.status}"}
            try:
                payload = json.loads(row.payload_json or "{}")
            except ValueError:
                payload = {}
            ok, result_or_error = _execute_tool(row.tool_name, payload, row.user_id.id)
            now = fields.Datetime.now()
            if ok:
                row.write({
                    "status": "executed",
                    "acted_at": now,
                    "result": result_or_error,
                })
                _append_message(row.conversation_id, f"Approved action #{row.id} ({row.tool_name}): {result_or_error}")
            else:
                row.write({
                    "status": "failed",
                    "acted_at": now,
                    "error": result_or_error,
                })
                _append_message(row.conversation_id, f"Action #{row.id} ({row.tool_name}) failed on execution: {result_or_error}")
            return {"ok": ok, "action": _serialize(row)}

        if action == "reject":
            if not request.env.user.has_group("base.group_system"):
                return {"ok": False, "error": "admin only"}
            row = Pending.search([("id", "=", _safe_int(kw.get("id")))], limit=1)
            if not row:
                return {"ok": False, "error": "not found"}
            if row.status != "pending":
                return {"ok": False, "error": f"already {row.status}"}
            row.write({
                "status": "rejected",
                "acted_at": fields.Datetime.now(),
            })
            _append_message(row.conversation_id, f"Action #{row.id} ({row.tool_name}) rejected by user.")
            return {"ok": True, "action": _serialize(row)}

        return {"error": f"unknown action {action!r}"}
