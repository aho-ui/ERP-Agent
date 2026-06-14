import contextvars
import functools
import json
import os
import urllib.error
import urllib.request

from mcp.server.fastmcp import FastMCP

# import xmlrpc.client  # dropped — MCP no longer authenticates against Odoo XML-RPC;
                        # all ORM calls go through Odoo's /erp_agent/internal/execute
                        # route, which validates a daemon-signed token and switches
                        # the env to the requesting user (record rules apply).

# URL = os.environ.get("ODOO_URL", "http://localhost:8069")
# DB = os.environ.get("ODOO_DB", "odoo_dev_18")
# USERNAME = os.environ.get("ODOO_USER", "admin")
# PASSWORD = os.environ.get("ODOO_PASSWORD", "admin")
EXEC_URL = os.environ.get(
    "ERP_AGENT_EXEC_URL",
    "http://localhost:8069/erp_agent/internal/execute",
)

mcp = FastMCP("odoo")

# carries the per-call daemon-signed token from `needs()` into the tool body's
# `_exec()` calls. ContextVar isolates per asyncio task / per sync invocation.
_token: contextvars.ContextVar[str | None] = contextvars.ContextVar("mcp_odoo_token", default=None)

# legacy in-process state — replaced by _token + per-call HTTP exec
# _uid: contextvars.ContextVar[int | None] = contextvars.ContextVar("mcp_uid", default=None)
# _models: contextvars.ContextVar = contextvars.ContextVar("mcp_models", default=None)


# def connect():
#     common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
#     uid = common.authenticate(DB, USERNAME, PASSWORD, {})
#     if not uid:
#         raise Exception("Odoo authentication failed")
#     models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")
#     return uid, models


@mcp.tool()
def health() -> str:
    try:
        # cheap reachability probe — POST without a body returns 400, GET returns 405,
        # either response proves the daemon route is up
        req = urllib.request.Request(EXEC_URL, method="GET")
        try:
            urllib.request.urlopen(req, timeout=5)
        except urllib.error.HTTPError:
            pass
        return json.dumps({"status": "UP", "reason": "connected"})
    except Exception as e:
        return json.dumps({"status": "DOWN", "reason": str(e)})


# def execute(uid, models, model, method, args, kwargs=None):
#     return models.execute_kw(DB, uid, PASSWORD, model, method, args, kwargs or {})


def _exec(model: str, method: str, args=None, kwargs=None):
    token = _token.get()
    if not token:
        raise RuntimeError("no auth token in context — call must be initiated via Odoo /erp_agent/chat")
    body = {
        "token": token,
        "model": model,
        "method": method,
        "args": list(args or []),
        "kwargs": dict(kwargs or {}),
    }
    req = urllib.request.Request(
        EXEC_URL,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            data = json.loads(e.read().decode("utf-8"))
        except Exception:
            raise RuntimeError(f"HTTP {e.code}: {e.reason}")
        raise RuntimeError(data.get("error", f"HTTP {e.code}"))
    if "error" in data:
        raise RuntimeError(data["error"])
    return data.get("result")


_MODEL_APP = {
    "sale.order": "Sales",
    "sale.order.line": "Sales",
    "purchase.order": "Purchase",
    "purchase.order.line": "Purchase",
    "account.move": "Accounting / Invoicing",
    "account.payment": "Accounting / Invoicing",
    "product.product": "Inventory / Sales",
    "res.partner": "Contacts",
}

_model_exists_cache: dict[str, bool] = {}


def _model_exists(name: str) -> bool:
    if name in _model_exists_cache:
        return _model_exists_cache[name]
    try:
        found = bool(_exec("ir.model", "search", [[["model", "=", name]]], {"limit": 1}))
    except Exception:
        found = False
    _model_exists_cache[name] = found
    return found


def _missing(model: str) -> str:
    app = _MODEL_APP.get(model, "the relevant Odoo app")
    return json.dumps({
        "error": f"Model '{model}' is not installed on this Odoo instance. "
                 f"Install the {app} module and try again."
    })


def needs(models_needed: list[str]):
    """Decorator: pull the daemon-signed `_auth_token` out of kwargs, install on
    the ContextVar, then check that every required Odoo model exists for this
    user. Returns a JSON error string if either step fails. Keeps the LLM-visible
    tool signature clean (no `_auth_token` in the public schema)."""

    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            token = kwargs.pop("_auth_token", None)
            if not token:
                return json.dumps({
                    "error": "missing auth token (chat must be initiated through Odoo controller)"
                })
            _token.set(token)
            for m in models_needed:
                if not _model_exists(m):
                    return _missing(m)
            return fn(*args, **kwargs)
        return wrapper
    return deco


def build_domain(base: list, search: str, field: str = "name", record_id: int = 0) -> list:
    domain = base[:]
    if record_id:
        domain.append(["id", "=", record_id])
    if search:
        domain.append([field, "ilike", search])
    return [domain]


@mcp.tool()
@needs(["sale.order"])
def get_sales_orders(limit: int = 10, search: str = "", id: int = 0) -> str:
    domain = build_domain([], search, record_id=id)
    orders = _exec("sale.order", "search_read", domain, {
        "fields": ["id", "name", "partner_id", "date_order", "amount_total", "state"],
        "limit": limit,
        "order": "date_order desc",
    })
    return json.dumps(orders)


@mcp.tool()
@needs(["res.partner"])
def get_customers(limit: int = 10, search: str = "", id: int = 0) -> str:
    domain = build_domain([["is_company", "=", True]], search, record_id=id)
    customers = _exec("res.partner", "search_read", domain, {
        "fields": ["id", "name", "email", "phone", "customer_rank"],
        "limit": limit,
    })
    return json.dumps(customers)


@mcp.tool()
@needs(["res.partner"])
def get_vendors(limit: int = 10, search: str = "", id: int = 0) -> str:
    domain = build_domain([["supplier_rank", ">", 0]], search, record_id=id)
    vendors = _exec("res.partner", "search_read", domain, {
        "fields": ["id", "name", "email", "phone", "supplier_rank"],
        "limit": limit,
    })
    return json.dumps(vendors)


@mcp.tool()
@needs(["product.product"])
def get_products(limit: int = 10, search: str = "", id: int = 0) -> str:
    domain = build_domain([["sale_ok", "=", True]], search, record_id=id)
    products = _exec("product.product", "search_read", domain, {
        "fields": ["id", "name", "list_price", "standard_price", "type", "default_code"],
        "limit": limit,
    })
    return json.dumps(products)


@mcp.tool()
@needs(["purchase.order"])
def get_purchase_orders(limit: int = 10, search: str = "", id: int = 0) -> str:
    domain = build_domain([], search, record_id=id)
    orders = _exec("purchase.order", "search_read", domain, {
        "fields": ["id", "name", "partner_id", "date_order", "amount_total", "state"],
        "limit": limit,
        "order": "date_order desc",
    })
    return json.dumps(orders)


@mcp.tool()
@needs(["account.move"])
def get_invoices(limit: int = 10, search: str = "", id: int = 0) -> str:
    domain = build_domain([["move_type", "=", "out_invoice"]], search, record_id=id)
    invoices = _exec("account.move", "search_read", domain, {
        "fields": ["id", "name", "partner_id", "invoice_date", "amount_total", "state", "payment_state"],
        "limit": limit,
        "order": "invoice_date desc",
    })
    return json.dumps(invoices)


@mcp.tool()
@needs(["account.move"])
def get_vendor_bills(limit: int = 10, search: str = "", id: int = 0) -> str:
    domain = build_domain([["move_type", "=", "in_invoice"]], search, record_id=id)
    bills = _exec("account.move", "search_read", domain, {
        "fields": ["id", "name", "partner_id", "invoice_date", "amount_total", "state", "payment_state"],
        "limit": limit,
        "order": "invoice_date desc",
    })
    return json.dumps(bills)


@mcp.tool()
@needs(["sale.order", "sale.order.line", "product.product"])
def create_sales_order(partner_id: int, product_id: int, quantity: float) -> str:
    product = _exec("product.product", "read", [[product_id]], {"fields": ["list_price"]})[0]
    order_id = _exec("sale.order", "create", [{"partner_id": partner_id}])
    _exec("sale.order.line", "create", [{
        "order_id": order_id,
        "product_id": product_id,
        "product_uom_qty": quantity,
        "price_unit": product["list_price"],
    }])
    return json.dumps({"order_id": order_id})


@mcp.tool()
@needs(["purchase.order", "purchase.order.line", "product.product"])
def create_purchase_order(vendor_id: int, product_id: int, quantity: float) -> str:
    product = _exec("product.product", "read", [[product_id]], {"fields": ["standard_price"]})[0]
    order_id = _exec("purchase.order", "create", [{"partner_id": vendor_id}])
    _exec("purchase.order.line", "create", [{
        "order_id": order_id,
        "product_id": product_id,
        "product_qty": quantity,
        "price_unit": product["standard_price"],
    }])
    _exec("purchase.order", "button_confirm", [[order_id]])
    return json.dumps({"order_id": order_id})


@mcp.tool()
@needs(["account.move", "product.product"])
def create_customer_invoice(partner_id: int, product_id: int, quantity: float, price_unit: float) -> str:
    product = _exec("product.product", "read", [[product_id]], {"fields": ["name"]})[0]
    invoice_id = _exec("account.move", "create", [{
        "move_type": "out_invoice",
        "partner_id": partner_id,
        "invoice_line_ids": [(0, 0, {
            "name": product["name"],
            "quantity": quantity,
            "price_unit": price_unit,
        })],
    }])
    _exec("account.move", "action_post", [[invoice_id]])
    return json.dumps({"invoice_id": invoice_id})


@mcp.tool()
@needs(["account.move", "product.product"])
def create_vendor_bill(vendor_id: int, product_id: int, quantity: float, price_unit: float) -> str:
    product = _exec("product.product", "read", [[product_id]], {"fields": ["name"]})[0]
    bill_id = _exec("account.move", "create", [{
        "move_type": "in_invoice",
        "partner_id": vendor_id,
        "invoice_line_ids": [(0, 0, {
            "name": product["name"],
            "quantity": quantity,
            "price_unit": price_unit,
        })],
    }])
    _exec("account.move", "action_post", [[bill_id]])
    return json.dumps({"bill_id": bill_id})


@mcp.tool()
@needs(["sale.order"])
def confirm_sales_order(order_id: int) -> str:
    _exec("sale.order", "button_confirm", [[order_id]])
    order = _exec("sale.order", "read", [[order_id]], {"fields": ["id", "name", "state"]})[0]
    return json.dumps({"order_id": order_id, "name": order["name"], "state": order["state"]})


@mcp.tool()
@needs(["account.move", "account.payment"])
def register_payment(invoice_id: int, amount: float) -> str:
    invoice = _exec("account.move", "read", [[invoice_id]], {"fields": ["id", "partner_id", "move_type"]})[0]
    is_outbound = invoice["move_type"] == "in_invoice"
    payment_id = _exec("account.payment", "create", [{
        "amount": amount,
        "partner_id": invoice["partner_id"][0],
        "payment_type": "outbound" if is_outbound else "inbound",
        "partner_type": "vendor" if is_outbound else "customer",
    }])
    _exec("account.payment", "action_post", [[payment_id]])
    return json.dumps({"payment_id": payment_id, "amount": amount})


@mcp.tool()
@needs(["sale.order"])
def update_sales_order(order_id: int, partner_id: int = None, notes: str = None) -> str:
    updates = {}
    if partner_id is not None:
        updates["partner_id"] = partner_id
    if notes is not None:
        updates["note"] = notes
    if not updates:
        return json.dumps({"error": "No fields to update"})
    _exec("sale.order", "write", [[order_id], updates])
    return json.dumps({"order_id": order_id, "updated_fields": list(updates.keys())})


@mcp.tool()
@needs(["purchase.order"])
def update_purchase_order(order_id: int, partner_id: int = None, notes: str = None) -> str:
    updates = {}
    if partner_id is not None:
        updates["partner_id"] = partner_id
    if notes is not None:
        updates["note"] = notes
    if not updates:
        return json.dumps({"error": "No fields to update"})
    _exec("purchase.order", "write", [[order_id], updates])
    return json.dumps({"order_id": order_id, "updated_fields": list(updates.keys())})


@mcp.tool()
@needs(["account.move"])
def update_invoice(invoice_id: int, partner_id: int = None, notes: str = None) -> str:
    updates = {}
    if partner_id is not None:
        updates["partner_id"] = partner_id
    if notes is not None:
        updates["narration"] = notes
    if not updates:
        return json.dumps({"error": "No fields to update"})
    _exec("account.move", "write", [[invoice_id], updates])
    return json.dumps({"invoice_id": invoice_id, "updated_fields": list(updates.keys())})


@mcp.tool()
def dashboard_stats() -> str:
    # NOTE: dashboard_stats has no @needs decorator and therefore no token; it
    # can't authenticate against the per-user /internal/execute route. Until
    # this tool is wired to receive a token (or removed), it returns an empty
    # payload so it doesn't crash the UI.
    return json.dumps({})
    # try:
    #     uid, models = connect()
    #     open_sales = len(execute(uid, models, "sale.order", "search", [[["state", "in", ["draft", "sale"]]]], {"limit": 10000}))
    #     total_customers = len(execute(uid, models, "res.partner", "search", [[["is_company", "=", True], ["customer_rank", ">", 0]]], {"limit": 10000}))
    #     total_products = len(execute(uid, models, "product.product", "search", [[["sale_ok", "=", True]]], {"limit": 10000}))
    #     open_purchase = len(execute(uid, models, "purchase.order", "search", [[["state", "in", ["draft", "purchase"]]]], {"limit": 10000}))
    #     unpaid_invoices = len(execute(uid, models, "account.move", "search", [[["move_type", "=", "out_invoice"], ["payment_state", "in", ["not_paid", "partial"]]]], {"limit": 10000}))
    #     return json.dumps({
    #         "open_sales_orders": open_sales,
    #         "total_customers": total_customers,
    #         "total_products": total_products,
    #         "open_purchase_orders": open_purchase,
    #         "unpaid_invoices": unpaid_invoices,
    #     })
    # except Exception:
    #     return json.dumps({})


if __name__ == "__main__":
    mcp.run(transport="stdio")
