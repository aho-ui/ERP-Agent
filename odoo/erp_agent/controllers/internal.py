import json

from werkzeug.wrappers import Response

from odoo import http
from odoo.http import request

from ._helpers import _ensure_path


def _err(msg, status=400):
    return Response(json.dumps({"error": msg}), status=status, mimetype="application/json")


class InternalController(http.Controller):

    @http.route("/erp_agent/internal/execute", type="http", auth="public",
                methods=["POST"], csrf=False)
    def execute(self, **kw):
        _ensure_path()
        from backend.gateway import verify

        try:
            body = json.loads(request.httprequest.get_data(as_text=True) or "{}")
        except json.JSONDecodeError:
            return _err("invalid JSON", 400)

        token = body.get("token")
        if not token:
            return _err("missing token", 401)
        payload = verify(token)
        if payload is None:
            return _err("invalid or expired token", 401)

        uid = payload.get("uid")
        if not uid:
            return _err("token missing uid", 401)

        model = body.get("model")
        method = body.get("method")
        args = body.get("args") or []
        kwargs = body.get("kwargs") or {}
        if not model or not method:
            return _err("model and method required", 400)

        try:
            # switch identity to the requesting user — Odoo record rules + ACLs apply
            env = request.env(user=int(uid))
            recordset = env[model]
            fn = getattr(recordset, method, None)
            if fn is None or not callable(fn):
                return _err(f"unknown method: {model}.{method}", 400)
            result = fn(*args, **kwargs)
        except Exception as e:
            return _err(f"execution failed: {type(e).__name__}: {e}", 500)

        return Response(
            json.dumps({"result": result}, default=str),
            mimetype="application/json",
        )
