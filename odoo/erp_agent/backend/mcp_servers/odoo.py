import json
import os
import xmlrpc.client
from mcp.server.fastmcp import FastMCP

URL = os.environ.get("ODOO_URL", "http://localhost:8069")
DB = os.environ.get("ODOO_DB", "odoo_dev_18")
USERNAME = os.environ.get("ODOO_USER", "admin")
PASSWORD = os.environ.get("ODOO_PASSWORD", "admin")

mcp = FastMCP("odoo")


def connect():
    common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
    uid = common.authenticate(DB, USERNAME, PASSWORD, {})
    if not uid:
        raise Exception("Odoo authentication failed")
    models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")
    return uid, models


@mcp.tool()
def health() -> str:
    try:
        connect()
        # return json.dumps({"ok": True})
        return json.dumps({"status": "UP", "reason": "connected"})
    except Exception as e:
        # return json.dumps({"ok": False, "error": str(e)})
        return json.dumps({"status": "DOWN", "reason": str(e)})


def execute(uid, models, model, method, args, kwargs=None):
    return models.execute_kw(DB, uid, PASSWORD, model, method, args, kwargs or {})


# which Odoo app provides each model — surfaced in error messages so users
# know which module to install
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

# cache model-existence checks per process to avoid hammering ir.model
_model_exists_cache: dict[str, bool] = {}


def _model_exists(uid, models, name: str) -> bool:
    if name in _model_exists_cache:
        return _model_exists_cache[name]
    try:
        found = bool(execute(uid, models, "ir.model", "search",
                             [[["model", "=", name]]], {"limit": 1}))
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


def _guard(needed: list[str]):
    """Returns (uid, models) on success, or a JSON error string if any model
    in `needed` doesn't exist. Use: r = _guard([...]); if isinstance(r, str): return r"""
    uid, models = connect()
    for m in needed:
        if not _model_exists(uid, models, m):
            return _missing(m)
    return uid, models


# active connection — set by @needs before invoking the tool body, read by the
# body via `ctx.uid` / `ctx.models`. Single-threaded MCP subprocess so a module
# global is safe.
class _Ctx:
    uid = None
    models = None


ctx = _Ctx()


def needs(models_needed: list[str]):
    """Decorator: guard the listed Odoo models, set ctx.{uid,models}, then call the body.
    Returns a JSON error if any model is missing. Keeps the LLM-visible signature clean."""
    import functools

    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            r = _guard(models_needed)
            if isinstance(r, str):
                return r
            ctx.uid, ctx.models = r
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
    orders = execute(ctx.uid, ctx.models, "sale.order", "search_read", domain, {
        "fields": ["id", "name", "partner_id", "date_order", "amount_total", "state"],
        "limit": limit,
        "order": "date_order desc",
    })
    return json.dumps(orders)


@mcp.tool()
@needs(["res.partner"])
def get_customers(limit: int = 10, search: str = "", id: int = 0) -> str:
    domain = build_domain([["is_company", "=", True]], search, record_id=id)
    customers = execute(ctx.uid, ctx.models, "res.partner", "search_read", domain, {
        "fields": ["id", "name", "email", "phone", "customer_rank"],
        "limit": limit,
    })
    return json.dumps(customers)


@mcp.tool()
@needs(["res.partner"])
def get_vendors(limit: int = 10, search: str = "", id: int = 0) -> str:
    domain = build_domain([["supplier_rank", ">", 0]], search, record_id=id)
    vendors = execute(ctx.uid, ctx.models, "res.partner", "search_read", domain, {
        "fields": ["id", "name", "email", "phone", "supplier_rank"],
        "limit": limit,
    })
    return json.dumps(vendors)


@mcp.tool()
@needs(["product.product"])
def get_products(limit: int = 10, search: str = "", id: int = 0) -> str:
    domain = build_domain([["sale_ok", "=", True]], search, record_id=id)
    products = execute(ctx.uid, ctx.models, "product.product", "search_read", domain, {
        "fields": ["id", "name", "list_price", "standard_price", "type", "default_code"],
        "limit": limit,
    })
    return json.dumps(products)


@mcp.tool()
@needs(["purchase.order"])
def get_purchase_orders(limit: int = 10, search: str = "", id: int = 0) -> str:
    domain = build_domain([], search, record_id=id)
    orders = execute(ctx.uid, ctx.models, "purchase.order", "search_read", domain, {
        "fields": ["id", "name", "partner_id", "date_order", "amount_total", "state"],
        "limit": limit,
        "order": "date_order desc",
    })
    return json.dumps(orders)


@mcp.tool()
@needs(["account.move"])
def get_invoices(limit: int = 10, search: str = "", id: int = 0) -> str:
    domain = build_domain([["move_type", "=", "out_invoice"]], search, record_id=id)
    invoices = execute(ctx.uid, ctx.models, "account.move", "search_read", domain, {
        "fields": ["id", "name", "partner_id", "invoice_date", "amount_total", "state", "payment_state"],
        "limit": limit,
        "order": "invoice_date desc",
    })
    return json.dumps(invoices)


@mcp.tool()
@needs(["account.move"])
def get_vendor_bills(limit: int = 10, search: str = "", id: int = 0) -> str:
    domain = build_domain([["move_type", "=", "in_invoice"]], search, record_id=id)
    bills = execute(ctx.uid, ctx.models, "account.move", "search_read", domain, {
        "fields": ["id", "name", "partner_id", "invoice_date", "amount_total", "state", "payment_state"],
        "limit": limit,
        "order": "invoice_date desc",
    })
    return json.dumps(bills)


@mcp.tool()
@needs(["sale.order", "sale.order.line", "product.product"])
def create_sales_order(partner_id: int, product_id: int, quantity: float) -> str:
    product = execute(ctx.uid, ctx.models, "product.product", "read", [[product_id]], {"fields": ["list_price"]})[0]
    order_id = execute(ctx.uid, ctx.models, "sale.order", "create", [{"partner_id": partner_id}])
    execute(ctx.uid, ctx.models, "sale.order.line", "create", [{
        "order_id": order_id,
        "product_id": product_id,
        "product_uom_qty": quantity,
        "price_unit": product["list_price"],
    }])
    return json.dumps({"order_id": order_id})


@mcp.tool()
@needs(["purchase.order", "purchase.order.line", "product.product"])
def create_purchase_order(vendor_id: int, product_id: int, quantity: float) -> str:
    product = execute(ctx.uid, ctx.models, "product.product", "read", [[product_id]], {"fields": ["standard_price"]})[0]
    order_id = execute(ctx.uid, ctx.models, "purchase.order", "create", [{"partner_id": vendor_id}])
    execute(ctx.uid, ctx.models, "purchase.order.line", "create", [{
        "order_id": order_id,
        "product_id": product_id,
        "product_qty": quantity,
        "price_unit": product["standard_price"],
    }])
    execute(ctx.uid, ctx.models, "purchase.order", "button_confirm", [[order_id]])
    return json.dumps({"order_id": order_id})


@mcp.tool()
@needs(["account.move", "product.product"])
def create_customer_invoice(partner_id: int, product_id: int, quantity: float, price_unit: float) -> str:
    product = execute(ctx.uid, ctx.models, "product.product", "read", [[product_id]], {"fields": ["name"]})[0]
    invoice_id = execute(ctx.uid, ctx.models, "account.move", "create", [{
        "move_type": "out_invoice",
        "partner_id": partner_id,
        "invoice_line_ids": [(0, 0, {
            "name": product["name"],
            "quantity": quantity,
            "price_unit": price_unit,
        })],
    }])
    execute(ctx.uid, ctx.models, "account.move", "action_post", [[invoice_id]])
    return json.dumps({"invoice_id": invoice_id})


@mcp.tool()
@needs(["account.move", "product.product"])
def create_vendor_bill(vendor_id: int, product_id: int, quantity: float, price_unit: float) -> str:
    product = execute(ctx.uid, ctx.models, "product.product", "read", [[product_id]], {"fields": ["name"]})[0]
    bill_id = execute(ctx.uid, ctx.models, "account.move", "create", [{
        "move_type": "in_invoice",
        "partner_id": vendor_id,
        "invoice_line_ids": [(0, 0, {
            "name": product["name"],
            "quantity": quantity,
            "price_unit": price_unit,
        })],
    }])
    execute(ctx.uid, ctx.models, "account.move", "action_post", [[bill_id]])
    return json.dumps({"bill_id": bill_id})


@mcp.tool()
@needs(["sale.order"])
def confirm_sales_order(order_id: int) -> str:
    execute(ctx.uid, ctx.models, "sale.order", "button_confirm", [[order_id]])
    order = execute(ctx.uid, ctx.models, "sale.order", "read", [[order_id]], {"fields": ["id", "name", "state"]})[0]
    return json.dumps({"order_id": order_id, "name": order["name"], "state": order["state"]})


@mcp.tool()
@needs(["account.move", "account.payment"])
def register_payment(invoice_id: int, amount: float) -> str:
    invoice = execute(ctx.uid, ctx.models, "account.move", "read", [[invoice_id]], {"fields": ["id", "partner_id", "move_type"]})[0]
    is_outbound = invoice["move_type"] == "in_invoice"
    payment_id = execute(ctx.uid, ctx.models, "account.payment", "create", [{
        "amount": amount,
        "partner_id": invoice["partner_id"][0],
        "payment_type": "outbound" if is_outbound else "inbound",
        "partner_type": "vendor" if is_outbound else "customer",
    }])
    execute(ctx.uid, ctx.models, "account.payment", "action_post", [[payment_id]])
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
    execute(ctx.uid, ctx.models, "sale.order", "write", [[order_id], updates])
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
    execute(ctx.uid, ctx.models, "purchase.order", "write", [[order_id], updates])
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
    execute(ctx.uid, ctx.models, "account.move", "write", [[invoice_id], updates])
    return json.dumps({"invoice_id": invoice_id, "updated_fields": list(updates.keys())})


@mcp.tool()
def dashboard_stats() -> str:
    try:
        uid, models = connect()
        open_sales = len(execute(uid, models, "sale.order", "search", [[["state", "in", ["draft", "sale"]]]], {"limit": 10000}))
        total_customers = len(execute(uid, models, "res.partner", "search", [[["is_company", "=", True], ["customer_rank", ">", 0]]], {"limit": 10000}))
        total_products = len(execute(uid, models, "product.product", "search", [[["sale_ok", "=", True]]], {"limit": 10000}))
        open_purchase = len(execute(uid, models, "purchase.order", "search", [[["state", "in", ["draft", "purchase"]]]], {"limit": 10000}))
        unpaid_invoices = len(execute(uid, models, "account.move", "search", [[["move_type", "=", "out_invoice"], ["payment_state", "in", ["not_paid", "partial"]]]], {"limit": 10000}))
        return json.dumps({
            "open_sales_orders": open_sales,
            "total_customers": total_customers,
            "total_products": total_products,
            "open_purchase_orders": open_purchase,
            "unpaid_invoices": unpaid_invoices,
        })
    except Exception:
        return json.dumps({})


if __name__ == "__main__":
    mcp.run(transport="stdio")
