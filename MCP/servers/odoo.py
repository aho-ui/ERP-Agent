import json
import xmlrpc.client
from mcp.server.fastmcp import FastMCP

URL = "http://localhost:8069"
DB = "odoo_dev_18"
USERNAME = "admin"
PASSWORD = "admin"

mcp = FastMCP("odoo")


def connect():
    common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
    uid = common.authenticate(DB, USERNAME, PASSWORD, {})
    if not uid:
        raise Exception("Odoo authentication failed")
    models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")
    return uid, models


def execute(uid, models, model, method, args, kwargs=None):
    return models.execute_kw(DB, uid, PASSWORD, model, method, args, kwargs or {})


def build_domain(base: list, search: str, field: str = "name") -> list:
    if search:
        return [base + [[field, "ilike", search]]]
    return [base]


@mcp.tool()
def get_sales_orders(limit: int = 10, search: str = "") -> str:
    uid, models = connect()
    domain = build_domain([], search)
    orders = execute(uid, models, "sale.order", "search_read", domain, {
        "fields": ["id", "name", "partner_id", "date_order", "amount_total", "state"],
        "limit": limit,
        "order": "date_order desc",
    })
    return json.dumps(orders)


@mcp.tool()
def get_customers(limit: int = 10, search: str = "") -> str:
    uid, models = connect()
    domain = build_domain([["is_company", "=", True]], search)
    customers = execute(uid, models, "res.partner", "search_read", domain, {
        "fields": ["id", "name", "email", "phone", "customer_rank"],
        "limit": limit,
    })
    return json.dumps(customers)


@mcp.tool()
def get_vendors(limit: int = 10, search: str = "") -> str:
    uid, models = connect()
    domain = build_domain([["supplier_rank", ">", 0]], search)
    vendors = execute(uid, models, "res.partner", "search_read", domain, {
        "fields": ["id", "name", "email", "phone", "supplier_rank"],
        "limit": limit,
    })
    return json.dumps(vendors)


@mcp.tool()
def get_products(limit: int = 10, search: str = "") -> str:
    uid, models = connect()
    domain = build_domain([["sale_ok", "=", True]], search)
    products = execute(uid, models, "product.product", "search_read", domain, {
        "fields": ["id", "name", "list_price", "type", "default_code"],
        "limit": limit,
    })
    return json.dumps(products)


@mcp.tool()
def get_purchase_orders(limit: int = 10, search: str = "") -> str:
    uid, models = connect()
    domain = build_domain([], search)
    orders = execute(uid, models, "purchase.order", "search_read", domain, {
        "fields": ["id", "name", "partner_id", "date_order", "amount_total", "state"],
        "limit": limit,
        "order": "date_order desc",
    })
    return json.dumps(orders)


@mcp.tool()
def get_invoices(limit: int = 10, search: str = "") -> str:
    uid, models = connect()
    domain = build_domain([["move_type", "=", "out_invoice"]], search)
    invoices = execute(uid, models, "account.move", "search_read", domain, {
        "fields": ["id", "name", "partner_id", "invoice_date", "amount_total", "state", "payment_state"],
        "limit": limit,
        "order": "invoice_date desc",
    })
    return json.dumps(invoices)


@mcp.tool()
def get_vendor_bills(limit: int = 10, search: str = "") -> str:
    uid, models = connect()
    domain = build_domain([["move_type", "=", "in_invoice"]], search)
    bills = execute(uid, models, "account.move", "search_read", domain, {
        "fields": ["id", "name", "partner_id", "invoice_date", "amount_total", "state", "payment_state"],
        "limit": limit,
        "order": "invoice_date desc",
    })
    return json.dumps(bills)


@mcp.tool()
def create_sales_order(partner_id: int, product_id: int, quantity: float, price_unit: float) -> str:
    uid, models = connect()
    order_id = execute(uid, models, "sale.order", "create", [{"partner_id": partner_id}])
    execute(uid, models, "sale.order.line", "create", [{
        "order_id": order_id,
        "product_id": product_id,
        "product_uom_qty": quantity,
        "price_unit": price_unit,
    }])
    return json.dumps({"order_id": order_id})


@mcp.tool()
def create_purchase_order(vendor_id: int, product_id: int, quantity: float, price_unit: float) -> str:
    uid, models = connect()
    order_id = execute(uid, models, "purchase.order", "create", [{"partner_id": vendor_id}])
    execute(uid, models, "purchase.order.line", "create", [{
        "order_id": order_id,
        "product_id": product_id,
        "product_qty": quantity,
        "price_unit": price_unit,
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


if __name__ == "__main__":
    mcp.run(transport="stdio")
#   mcp.run(transport="sse", host="0.0.0.0", port=8001)
