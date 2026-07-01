from datetime import datetime, timedelta

from odoo import fields, http
from odoo.http import request


class UsageController(http.Controller):

    @http.route("/erp_agent/usage", type="json", auth="user", methods=["POST"], csrf=False)
    def usage(self, days=30, **kw):
        if not request.env.user.has_group("base.group_system"):
            return {"error": "admin only"}
        try:
            days = max(1, min(365, int(days)))
        except (TypeError, ValueError):
            days = 30

        Msg = request.env["erp_agent.message"].sudo()
        cutoff = datetime.now() - timedelta(days=days)
        msgs = Msg.search([
            ("role", "=", "assistant"),
            ("create_date", ">=", fields.Datetime.to_string(cutoff)),
            ("prompt_tokens", ">", 0),
        ], limit=20000)

        per_user, per_model, per_day = {}, {}, {}
        total_prompt = total_completion = 0
        total_cost = 0.0

        for m in msgs:
            user = m.conversation_id.user_id.name or "Unknown"
            model = m.model or "unknown"
            day = m.create_date.date().isoformat() if m.create_date else "unknown"
            ptok = m.prompt_tokens or 0
            ctok = m.completion_tokens or 0
            cost = m.cost_usd or 0.0

            total_prompt += ptok
            total_completion += ctok
            total_cost += cost

            for bucket, key in ((per_user, user), (per_model, model)):
                rec = bucket.setdefault(key, {"prompt": 0, "completion": 0, "cost": 0.0, "msgs": 0})
                rec["prompt"] += ptok
                rec["completion"] += ctok
                rec["cost"] += cost
                rec["msgs"] += 1

            d = per_day.setdefault(day, {"cost": 0.0, "tokens": 0})
            d["cost"] += cost
            d["tokens"] += ptok + ctok

        today = datetime.now().date()
        history = []
        for i in range(days):
            d = today - timedelta(days=days - 1 - i)
            key = d.isoformat()
            slot = per_day.get(key, {"cost": 0.0, "tokens": 0})
            history.append({
                "day": key,
                "cost": round(slot["cost"], 4),
                "tokens": slot["tokens"],
            })

        def _flatten(bucket):
            return sorted(
                [
                    {"name": n, "prompt": s["prompt"], "completion": s["completion"],
                     "msgs": s["msgs"], "cost": round(s["cost"], 4)}
                    for n, s in bucket.items()
                ],
                key=lambda x: -x["cost"],
            )

        return {
            "days": days,
            "totals": {
                "prompt_tokens": total_prompt,
                "completion_tokens": total_completion,
                "cost_usd": round(total_cost, 4),
                "messages": len(msgs),
            },
            "per_user": _flatten(per_user),
            "per_model": _flatten(per_model),
            "history": history,
        }
