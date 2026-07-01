import json

import requests
from werkzeug.wrappers import Response

from odoo import http
from odoo.http import request

from ._helpers import _agent_dict, _disabled_defaults, _enabled_mcps, _ensure_path, _safe_int

DAEMON_URL = "http://127.0.0.1:8001/chat/"
_DAEMON_TIMEOUT = 300
_SESSION_CONV_PREFIX = "odoo:conv:"


def _override_for_session(env, session_key):
    if not session_key or not session_key.startswith(_SESSION_CONV_PREFIX):
        return ""
    cid = _safe_int(session_key[len(_SESSION_CONV_PREFIX):])
    if not cid:
        return ""
    conv = env["erp_agent.conversation"].search([("id", "=", cid)], limit=1)
    return (conv.system_prompt_override or "") if conv else ""


class ChatController(http.Controller):

    @http.route("/erp_agent/chat", type="http", auth="user", methods=["POST"], csrf=False)
    def chat(self, **kw):
        _ensure_path()
        from backend.chat.views import API_KEY

        try:
            body = json.loads(request.httprequest.get_data(as_text=True) or "{}")
        except json.JSONDecodeError:
            return Response("invalid JSON", status=400)

        Agent = request.env["erp_agent.agent"]
        agents = [_agent_dict(r) for r in Agent.search([])]
        disabled = _disabled_defaults(request.env)

        # resolve active profile — sudo + manual user_id filter so a stale
        # profile_id in the browser (from another user's session) doesn't 403
        Profile = request.env["erp_agent.profile"].sudo()
        uid = request.env.user.id
        profile_id = body.get("profile_id") or ""
        profile_rec = None
        if profile_id:
            try:
                cand = Profile.browse(int(profile_id)).exists()
            except (TypeError, ValueError):
                cand = None
            if cand and cand.user_id.id == uid:
                profile_rec = cand
        if not profile_rec:
            profile_rec = Profile.search([("user_id", "=", uid)], limit=1)
        profile = None
        if profile_rec:
            profile = {
                "id": str(profile_rec.id),
                "name": profile_rec.name or "",
                "model": profile_rec.model or "",
                "api_key": profile_rec.api_key or "",
            }

        session_key = body.get("session_key", "odoo:default")
        forwarded = {
            "message": body.get("message", ""),
            "session_key": session_key,
            "uid": request.env.user.id,
            "is_admin": request.env.user.has_group("base.group_system"),
            "agents": agents,
            "disabled_defaults": disabled,
            "profile": profile,
            "enabled_mcps": _enabled_mcps(request.env),
            "system_prompt_override": _override_for_session(request.env, session_key),
        }

        headers = {"Content-Type": "application/json", "X-API-Key": API_KEY}
        upstream = requests.post(DAEMON_URL, json=forwarded, headers=headers,
                                 stream=True, timeout=_DAEMON_TIMEOUT)

        def relay():
            for chunk in upstream.iter_content(chunk_size=None):
                if chunk:
                    yield chunk

        return Response(
            relay(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
