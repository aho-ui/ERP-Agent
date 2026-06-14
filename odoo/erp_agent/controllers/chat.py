import json
import os

import requests
from werkzeug.wrappers import Response

from odoo import http
from odoo.http import request

from ._helpers import _agent_dict, _disabled_defaults, _enabled_mcps, _ensure_path

DAEMON_URL = "http://127.0.0.1:8001/chat/"


class ChatController(http.Controller):

    @http.route("/erp_agent/chat", type="http", auth="user", methods=["POST"], csrf=False)
    def chat(self, **kw):
        _ensure_path()

        try:
            body = json.loads(request.httprequest.get_data(as_text=True) or "{}")
        except json.JSONDecodeError:
            return Response("invalid JSON", status=400)

        Agent = request.env["erp_agent.agent"]
        agents = [_agent_dict(r) for r in Agent.search([])]
        disabled = _disabled_defaults(request.env)

        # resolve active profile (record rule scopes to current user)
        Profile = request.env["erp_agent.profile"]
        profile_id = body.get("profile_id") or ""
        profile_rec = None
        if profile_id:
            try:
                profile_rec = Profile.browse(int(profile_id)).exists()
            except (TypeError, ValueError):
                profile_rec = None
        if not profile_rec:
            profile_rec = Profile.search([], limit=1)
        profile = None
        if profile_rec:
            profile = {
                "id": str(profile_rec.id),
                "name": profile_rec.name or "",
                "model": profile_rec.model or "",
                "api_key": profile_rec.api_key or "",
            }

        forwarded = {
            "message": body.get("message", ""),
            "session_key": body.get("session_key", "odoo:default"),
            "uid": request.env.user.id,
            "agents": agents,
            "disabled_defaults": disabled,
            "profile": profile,
            "enabled_mcps": _enabled_mcps(request.env),
        }

        headers = {"Content-Type": "application/json"}
        api_key = os.environ.get("AGENT_API_KEY", "")
        if api_key:
            headers["X-API-Key"] = api_key

        upstream = requests.post(DAEMON_URL, json=forwarded, headers=headers,
                                 stream=True, timeout=300)

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
