import json
from datetime import datetime, timedelta

from odoo import fields, http
from odoo.http import request


def _aggregate_window(msgs):
    totals = {"sqlite": 0, "odoo": 0}
    daily = {}
    per_agent = {}
    tool_counts = {}
    step_total = 0
    step_msgs = 0
    for m in msgs:
        try:
            tools = json.loads(m.tools_used or "[]")
        except Exception:
            tools = []
        servers = set()
        for t in tools:
            tool_counts[t] = tool_counts.get(t, 0) + 1
            parts = t.split("_", 2)
            if len(parts) >= 2 and parts[0] == "mcp":
                servers.add(parts[1])
        for s in servers:
            totals[s] = totals.get(s, 0) + 1
        if m.create_date:
            day = m.create_date.date().isoformat()
            daily[day] = daily.get(day, 0) + 1
        if m.agent_name:
            per_agent[m.agent_name] = per_agent.get(m.agent_name, 0) + 1
        try:
            steps = json.loads(m.steps or "[]")
            if isinstance(steps, list) and steps:
                step_total += len(steps)
                step_msgs += 1
        except Exception:
            pass
    return totals, daily, per_agent, tool_counts, step_total, step_msgs


def _daily_series(Msg, cutoff, daily, days):
    err_msgs = Msg.search([
        ("role", "=", "error"),
        ("create_date", ">=", fields.Datetime.to_string(cutoff)),
    ], limit=2000)
    err_daily = {}
    for em in err_msgs:
        if em.create_date:
            day = em.create_date.date().isoformat()
            err_daily[day] = err_daily.get(day, 0) + 1

    today = datetime.now().date()
    history, errors = [], []
    for i in range(days):
        d = today - timedelta(days=days - 1 - i)
        key = d.isoformat()
        history.append({"day": key, "count": daily.get(key, 0)})
        errors.append(err_daily.get(key, 0))
    return history, errors


def _build_calls(msgs, is_admin, Msg):
    calls = []
    for m in msgs[:50]:
        try:
            tools = json.loads(m.tools_used or "[]")
        except Exception:
            tools = []
        try:
            steps = json.loads(m.steps or "[]")
        except Exception:
            steps = []
        prior = Msg.search([
            ("conversation_id", "=", m.conversation_id.id),
            ("id", "<", m.id),
            ("role", "=", "user"),
        ], order="id desc", limit=1)
        calls.append({
            "id": m.id,
            "ts": fields.Datetime.to_string(m.create_date) if m.create_date else "",
            "agent": m.agent_name or "",
            "actions": len(tools),
            "user": m.conversation_id.user_id.name if is_admin else "",
            "query": (prior.content or "") if prior else "",
            "result": (m.content or "")[:2000],
            "tools": tools,
            "steps": steps,
        })
    return calls


class ActivityController(http.Controller):

    @http.route("/erp_agent/activity", type="json", auth="user", methods=["POST"], csrf=False)
    def activity(self, days=50, **kw):
        try:
            days = max(1, min(90, int(days)))
        except (TypeError, ValueError):
            days = 50
        is_admin = request.env.user.has_group("base.group_system")
        Msg = request.env["erp_agent.message"]
        if is_admin:
            Msg = Msg.sudo()
        cutoff = datetime.now() - timedelta(days=days)
        msgs = Msg.search([
            ("role", "=", "assistant"),
            ("create_date", ">=", fields.Datetime.to_string(cutoff)),
        ], order="create_date desc", limit=2000)

        totals, daily, per_agent, tool_counts, step_total, step_msgs = _aggregate_window(msgs)
        history, errors = _daily_series(Msg, cutoff, daily, days)

        per_agent_list = sorted(
            [{"name": n, "count": c} for n, c in per_agent.items()],
            key=lambda x: -x["count"],
        )
        top_tools = sorted(
            [{"name": n, "count": c} for n, c in tool_counts.items()],
            key=lambda x: -x["count"],
        )[:5]
        avg_steps = round(step_total / step_msgs, 1) if step_msgs else 0

        return {
            "is_admin": is_admin,
            "totals": totals,
            "history": history,
            "errors": errors,
            "calls": _build_calls(msgs, is_admin, Msg),
            "per_agent": per_agent_list,
            "top_tools": top_tools,
            "avg_steps": avg_steps,
        }
