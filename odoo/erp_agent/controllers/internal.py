import json
import logging

from werkzeug.wrappers import Response

from odoo import http
from odoo.http import request

from ._helpers import _ensure_path

_logger = logging.getLogger(__name__)

_BASE_OPS = {("ir.model", "search")}

_TOOL_ALLOWED_OPS = {
    "get_sales_orders":        _BASE_OPS | {("sale.order", "search_read")},
    "get_customers":           _BASE_OPS | {("res.partner", "search_read")},
    "get_vendors":             _BASE_OPS | {("res.partner", "search_read")},
    "get_products":            _BASE_OPS | {("product.product", "search_read")},
    "get_purchase_orders":     _BASE_OPS | {("purchase.order", "search_read")},
    "get_invoices":            _BASE_OPS | {("account.move", "search_read")},
    "get_vendor_bills":        _BASE_OPS | {("account.move", "search_read")},
    "create_sales_order":      _BASE_OPS | {
        ("product.product", "read"),
        ("sale.order", "create"),
        ("sale.order.line", "create"),
    },
    "create_purchase_order":   _BASE_OPS | {
        ("product.product", "read"),
        ("purchase.order", "create"),
        ("purchase.order.line", "create"),
        ("purchase.order", "button_confirm"),
    },
    "create_customer_invoice": _BASE_OPS | {
        ("product.product", "read"),
        ("account.move", "create"),
        ("account.move", "action_post"),
    },
    "create_vendor_bill":      _BASE_OPS | {
        ("product.product", "read"),
        ("account.move", "create"),
        ("account.move", "action_post"),
    },
    "confirm_sales_order":     _BASE_OPS | {
        ("sale.order", "button_confirm"),
        ("sale.order", "read"),
    },
    "register_payment":        _BASE_OPS | {
        ("account.move", "read"),
        ("account.payment", "create"),
        ("account.payment", "action_post"),
    },
    "update_sales_order":      _BASE_OPS | {("sale.order", "write")},
    "update_purchase_order":   _BASE_OPS | {("purchase.order", "write")},
    "update_invoice":          _BASE_OPS | {("account.move", "write")},
    "dashboard_stats":         _BASE_OPS | {
        ("sale.order", "search"),
        ("res.partner", "search"),
        ("product.product", "search"),
        ("purchase.order", "search"),
        ("account.move", "search"),
    },
}


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

        op = payload.get("op")
        allowed = _TOOL_ALLOWED_OPS.get(op, set())
        if (model, method) not in allowed:
            return _err("operation not allowed for this token", 403)

        try:
            env = request.env(user=int(uid))
            recordset = env[model]
            fn = getattr(recordset, method, None)
            if fn is None or not callable(fn):
                return _err(f"unknown method: {model}.{method}", 400)
            result = fn(*args, **kwargs)
        except Exception:
            _logger.exception("[internal] %s.%s failed", model, method)
            return _err("execution failed", 500)

        return Response(
            json.dumps({"result": result}, default=str),
            mimetype="application/json",
        )
