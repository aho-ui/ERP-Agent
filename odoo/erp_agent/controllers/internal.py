import json
import logging

from werkzeug.wrappers import Response

from odoo import http, models
from odoo.http import request

from ._helpers import _ensure_path

_logger = logging.getLogger(__name__)

_ensure_path()
from backend.tool_meta import TOOL_ALLOWED_OPS as _TOOL_ALLOWED_OPS


def _err(msg, status=400):
    return Response(json.dumps({"error": msg}), status=status, mimetype="application/json")


class InternalController(http.Controller):

    @http.route("/erp_agent/internal/seed_products", type="http", auth="user",
                methods=["GET"], csrf=False)
    def seed_products(self, **kw):
        if not request.env.user.has_group("base.group_system"):
            return Response(json.dumps({"error": "admin only"}), status=403, mimetype="application/json")
        Product = request.env["product.product"].sudo()
        existing = Product.search_count([])
        if existing:
            return Response(
                json.dumps({"ok": True, "created": 0, "existing": existing}),
                mimetype="application/json",
            )
        seed = [
            {"name": "Demo Widget", "list_price": 19.99, "standard_price": 7.5, "type": "consu"},
            {"name": "Demo Gadget", "list_price": 49.00, "standard_price": 22.0, "type": "consu"},
        ]
        created = Product.create(seed)
        return Response(
            json.dumps({"ok": True, "created": len(created), "ids": created.ids}),
            mimetype="application/json",
        )

    @http.route("/erp_agent/internal/health", type="http", auth="public",
                methods=["GET"], csrf=False)
    def health(self, **kw):
        try:
            request.env["ir.model"].sudo().search([], limit=1)
        except Exception as e:
            _logger.exception("[internal] health probe failed")
            return Response(
                json.dumps({"status": "DOWN", "reason": f"db query failed: {type(e).__name__}"}),
                status=503,
                mimetype="application/json",
            )
        return Response(
            json.dumps({"status": "UP", "reason": "ok"}),
            mimetype="application/json",
        )

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

        op = payload.get("op")
        allowed = _TOOL_ALLOWED_OPS.get(op, set())
        if (model, method) not in allowed:
            return _err("operation not allowed for this token", 403)

        try:
            env = request.env(user=int(uid))
            recordset = env[model]
            if not hasattr(recordset, method):
                return _err(f"unknown method: {model}.{method}", 400)
            # Mimic Odoo's execute_kw: if first positional arg looks like a list of ids,
            # browse them and dispatch the method on the resulting recordset.
            if args and isinstance(args[0], list) and args[0] and all(isinstance(x, int) and not isinstance(x, bool) for x in args[0]):
                target = env[model].browse(args[0])
                fn = getattr(target, method)
                result = fn(*args[1:], **kwargs)
            else:
                fn = getattr(recordset, method)
                result = fn(*args, **kwargs)
        except Exception:
            _logger.exception("[internal] %s.%s failed", model, method)
            return _err("execution failed", 500)

        if isinstance(result, models.BaseModel):
            result = result.id if len(result) == 1 else result.ids

        return Response(
            json.dumps({"result": result}, default=str),
            mimetype="application/json",
        )
