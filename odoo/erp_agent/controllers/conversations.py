import json
import re

from odoo import http
from odoo.http import request

from ._helpers import _ensure_path, _parse_steps, _parse_tokens_from_steps, _safe_int


def _safe_filename(name):
    safe = re.sub(r"[^A-Za-z0-9_-]+", "-", name or "").strip("-")
    return safe or "conversation"


def _format_markdown(conv):
    lines = [f"# {conv.name or 'Conversation'}", ""]
    for m in conv.message_ids:
        role = m.role or "?"
        if role == "user":
            label = "## You"
        elif role == "assistant":
            label = f"## Assistant — {m.agent_name}" if m.agent_name else "## Assistant"
        elif role == "error":
            label = "## Error"
        else:
            label = f"## {role}"
        lines.append(label)
        lines.append("")
        lines.append(m.content or "")
        lines.append("")
    return "\n".join(lines)


class ConversationsController(http.Controller):

    @http.route("/erp_agent/conversation", type="json", auth="user", methods=["POST"], csrf=False)
    def conversation(self, action="list", **kw):
        _ensure_path()
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
            return {
                "messages": [
                    {
                        "role": m.role,
                        "content": m.content or "",
                        "artifacts": m.artifacts or "",
                        "steps": m.steps or "",
                        "tools_used": m.tools_used or "",
                        "agent_name": m.agent_name or "",
                    }
                    for m in c.message_ids
                ],
                "system_prompt_override": c.system_prompt_override or "",
            }

        if action == "get_system_prompt":
            c = _own(kw.get("id"))
            if not c:
                return {"ok": False, "prompt": ""}
            return {"ok": True, "prompt": c.system_prompt_override or ""}

        if action == "set_system_prompt":
            c = _own(kw.get("id"))
            if not c:
                return {"ok": False}
            c.system_prompt_override = (kw.get("prompt") or "").strip()
            return {"ok": True}

        if action == "export":
            c = _own(kw.get("id"))
            if not c:
                return {"ok": False}
            return {
                "ok": True,
                "filename": f"{_safe_filename(c.name)}.md",
                "markdown": _format_markdown(c),
            }

        if action == "search":
            q = (kw.get("query") or "").strip()
            if len(q) < 2:
                return {"results": []}
            hits = Msg.search([
                ("content", "ilike", q),
                ("role", "in", ["user", "assistant"]),
            ], order="create_date desc", limit=100)
            seen = set()
            results = []
            for m in hits:
                cid = m.conversation_id.id
                if cid in seen:
                    continue
                seen.add(cid)
                content = m.content or ""
                snippet = content[:150] + ("..." if len(content) > 150 else "")
                results.append({
                    "conv_id": cid,
                    "conv_name": m.conversation_id.name or "Conversation",
                    "snippet": snippet,
                    "message_id": m.id,
                })
                if len(results) >= 20:
                    break
            return {"results": results}

        if action == "append":
            c = _own(kw.get("id"))
            if not c:
                return {"ok": False}
            steps_raw = kw.get("steps") or ""
            tools, agent = _parse_steps(steps_raw)
            prompt_tokens, completion_tokens, model, cost_usd = _parse_tokens_from_steps(steps_raw)
            Msg.create({
                "conversation_id": c.id,
                "role": kw.get("role") or "assistant",
                "content": kw.get("content") or "",
                "artifacts": kw.get("artifacts") or "",
                "steps": steps_raw,
                "tools_used": json.dumps(tools) if tools else "",
                "agent_name": agent or "",
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "model": model,
                "cost_usd": cost_usd,
            })
            return {"ok": True}

        return {"error": f"unknown action {action!r}"}
