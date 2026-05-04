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
        return json.dumps({"ok": True})
    except Exception as e:
        return json.dumps({"ok": False, "error": str(e)})


def execute(uid, models, model, method, args, kwargs=None):
    return models.execute_kw(DB, uid, PASSWORD, model, method, args, kwargs or {})


def build_domain(base: list, search: str, field: str = "name", record_id: int = 0) -> list:
    domain = base[:]
    if record_id:
        domain.append(["id", "=", record_id])
    if search:
        domain.append([field, "ilike", search])
    return [domain]


@mcp.tool()
def get_sales_orders(limit: int = 10, search: str = "", id: int = 0) -> str:
    uid, models = connect()
    domain = build_domain([], search, record_id=id)
    orders = execute(uid, models, "sale.order", "search_read", domain, {
        "fields": ["id", "name", "partner_id", "date_order", "amount_total", "state"],
        "limit": limit,
        "order": "date_order desc",
    })
    return json.dumps(orders)


@mcp.tool()
def get_customers(limit: int = 10, search: str = "", id: int = 0) -> str:
    uid, models = connect()
    domain = build_domain([["is_company", "=", True]], search, record_id=id)
    customers = execute(uid, models, "res.partner", "search_read", domain, {
        "fields": ["id", "name", "email", "phone", "customer_rank"],
        "limit": limit,
    })
    return json.dumps(customers)


@mcp.tool()
def get_vendors(limit: int = 10, search: str = "", id: int = 0) -> str:
    uid, models = connect()
    domain = build_domain([["supplier_rank", ">", 0]], search, record_id=id)
    vendors = execute(uid, models, "res.partner", "search_read", domain, {
        "fields": ["id", "name", "email", "phone", "supplier_rank"],
        "limit": limit,
    })
    return json.dumps(vendors)


@mcp.tool()
def get_products(limit: int = 10, search: str = "", id: int = 0) -> str:
    uid, models = connect()
    domain = build_domain([["sale_ok", "=", True]], search, record_id=id)
    products = execute(uid, models, "product.product", "search_read", domain, {
        "fields": ["id", "name", "list_price", "standard_price", "type", "default_code"],
        "limit": limit,
    })
    return json.dumps(products)


@mcp.tool()
def get_purchase_orders(limit: int = 10, search: str = "", id: int = 0) -> str:
    uid, models = connect()
    domain = build_domain([], search, record_id=id)
    orders = execute(uid, models, "purchase.order", "search_read", domain, {
        "fields": ["id", "name", "partner_id", "date_order", "amount_total", "state"],
        "limit": limit,
        "order": "date_order desc",
    })
    return json.dumps(orders)


@mcp.tool()
def get_invoices(limit: int = 10, search: str = "", id: int = 0) -> str:
    uid, models = connect()
    domain = build_domain([["move_type", "=", "out_invoice"]], search, record_id=id)
    invoices = execute(uid, models, "account.move", "search_read", domain, {
        "fields": ["id", "name", "partner_id", "invoice_date", "amount_total", "state", "payment_state"],
        "limit": limit,
        "order": "invoice_date desc",
    })
    return json.dumps(invoices)


@mcp.tool()
def get_vendor_bills(limit: int = 10, search: str = "", id: int = 0) -> str:
    uid, models = connect()
    domain = build_domain([["move_type", "=", "in_invoice"]], search, record_id=id)
    bills = execute(uid, models, "account.move", "search_read", domain, {
        "fields": ["id", "name", "partner_id", "invoice_date", "amount_total", "state", "payment_state"],
        "limit": limit,
        "order": "invoice_date desc",
    })
    return json.dumps(bills)


@mcp.tool()
def create_sales_order(partner_id: int, product_id: int, quantity: float) -> str:
    uid, models = connect()
    product = execute(uid, models, "product.product", "read", [[product_id]], {"fields": ["list_price"]})[0]
    order_id = execute(uid, models, "sale.order", "create", [{"partner_id": partner_id}])
    execute(uid, models, "sale.order.line", "create", [{
        "order_id": order_id,
        "product_id": product_id,
        "product_uom_qty": quantity,
        "price_unit": product["list_price"],
    }])
    return json.dumps({"order_id": order_id})


@mcp.tool()
def create_purchase_order(vendor_id: int, product_id: int, quantity: float) -> str:
    uid, models = connect()
    product = execute(uid, models, "product.product", "read", [[product_id]], {"fields": ["standard_price"]})[0]
    order_id = execute(uid, models, "purchase.order", "create", [{"partner_id": vendor_id}])
    execute(uid, models, "purchase.order.line", "create", [{
        "order_id": order_id,
        "product_id": product_id,
        "product_qty": quantity,
        "price_unit": product["standard_price"],
    }])
    execute(uid, models, "purchase.order", "button_confirm", [[order_id]])
    return json.dumps({"order_id": order_id})


@mcp.tool()
def create_customer_invoice(partner_id: int, product_id: int, quantity: float, price_unit: float) -> str:
    uid, models = connect()
    product = execute(uid, models, "product.product", "read", [[product_id]], {"fields": ["name"]})[0]
    invoice_id = execute(uid, models, "account.move", "create", [{
        "move_type": "out_invoice",
        "partner_id": partner_id,
        "invoice_line_ids": [(0, 0, {
            "name": product["name"],
            "quantity": quantity,
            "price_unit": price_unit,
        })],
    }])
    execute(uid, models, "account.move", "action_post", [[invoice_id]])
    return json.dumps({"invoice_id": invoice_id})


@mcp.tool()
def create_vendor_bill(vendor_id: int, product_id: int, quantity: float, price_unit: float) -> str:
    uid, models = connect()
    product = execute(uid, models, "product.product", "read", [[product_id]], {"fields": ["name"]})[0]
    bill_id = execute(uid, models, "account.move", "create", [{
        "move_type": "in_invoice",
        "partner_id": vendor_id,
        "invoice_line_ids": [(0, 0, {
            "name": product["name"],
            "quantity": quantity,
            "price_unit": price_unit,
        })],
    }])
    execute(uid, models, "account.move", "action_post", [[bill_id]])
    return json.dumps({"bill_id": bill_id})


@mcp.tool()
def confirm_sales_order(order_id: int) -> str:
    uid, models = connect()
    execute(uid, models, "sale.order", "button_confirm", [[order_id]])
    order = execute(uid, models, "sale.order", "read", [[order_id]], {"fields": ["id", "name", "state"]})[0]
    return json.dumps({"order_id": order_id, "name": order["name"], "state": order["state"]})


@mcp.tool()
def register_payment(invoice_id: int, amount: float) -> str:
    uid, models = connect()
    invoice = execute(uid, models, "account.move", "read", [[invoice_id]], {"fields": ["id", "partner_id", "move_type"]})[0]
    is_outbound = invoice["move_type"] == "in_invoice"
    payment_id = execute(uid, models, "account.payment", "create", [{
        "amount": amount,
        "partner_id": invoice["partner_id"][0],
        "payment_type": "outbound" if is_outbound else "inbound",
        "partner_type": "vendor" if is_outbound else "customer",
    }])
    execute(uid, models, "account.payment", "action_post", [[payment_id]])
    return json.dumps({"payment_id": payment_id, "amount": amount})


@mcp.tool()
def update_sales_order(order_id: int, partner_id: int = None, notes: str = None) -> str:
    uid, models = connect()
    updates = {}
    if partner_id is not None:
        updates["partner_id"] = partner_id
    if notes is not None:
        updates["note"] = notes
    if not updates:
        return json.dumps({"error": "No fields to update"})
    execute(uid, models, "sale.order", "write", [[order_id], updates])
    return json.dumps({"order_id": order_id, "updated_fields": list(updates.keys())})


@mcp.tool()
def update_purchase_order(order_id: int, partner_id: int = None, notes: str = None) -> str:
    uid, models = connect()
    updates = {}
    if partner_id is not None:
        updates["partner_id"] = partner_id
    if notes is not None:
        updates["note"] = notes
    if not updates:
        return json.dumps({"error": "No fields to update"})
    execute(uid, models, "purchase.order", "write", [[order_id], updates])
    return json.dumps({"order_id": order_id, "updated_fields": list(updates.keys())})


@mcp.tool()
def update_invoice(invoice_id: int, partner_id: int = None, notes: str = None) -> str:
    uid, models = connect()
    updates = {}
    if partner_id is not None:
        updates["partner_id"] = partner_id
    if notes is not None:
        updates["narration"] = notes
    if not updates:
        return json.dumps({"error": "No fields to update"})
    execute(uid, models, "account.move", "write", [[invoice_id], updates])
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
#   mcp.run(transport="sse", host="0.0.0.0", port=8001)
