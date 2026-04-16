import json
import sqlite3
from pathlib import Path
from mcp.server.fastmcp import FastMCP

DB_PATH = Path(__file__).resolve().parents[2] / "demo.db"

mcp = FastMCP("sqlite")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def health() -> bool:
    try:
        conn = get_conn()
        conn.execute("SELECT 1 FROM customers LIMIT 1")
        conn.close()
        return True
    except Exception:
        return False



def _rows(cursor) -> list[dict]:
    return [dict(row) for row in cursor.fetchall()]


@mcp.tool()
def get_sales_orders(limit: int = 10, search: str = "", id: int = 0) -> str:
    conn = get_conn()
    q = "SELECT id, name, partner_id, partner_name, date_order, amount_total, state FROM sales_orders WHERE 1=1"
    params: list = []
    if id:
        q += " AND id = ?"
        params.append(id)
    if search:
        q += " AND name LIKE ?"
        params.append(f"%{search}%")
    q += " ORDER BY date_order DESC LIMIT ?"
    params.append(limit)
    return json.dumps(_rows(conn.execute(q, params)))


@mcp.tool()
def get_customers(limit: int = 10, search: str = "", id: int = 0) -> str:
    conn = get_conn()
    q = "SELECT id, name, email, phone, customer_rank FROM customers WHERE 1=1"
    params: list = []
    if id:
        q += " AND id = ?"
        params.append(id)
    if search:
        q += " AND name LIKE ?"
        params.append(f"%{search}%")
    q += " LIMIT ?"
    params.append(limit)
    return json.dumps(_rows(conn.execute(q, params)))


@mcp.tool()
def get_vendors(limit: int = 10, search: str = "", id: int = 0) -> str:
    conn = get_conn()
    q = "SELECT id, name, email, phone, supplier_rank FROM vendors WHERE 1=1"
    params: list = []
    if id:
        q += " AND id = ?"
        params.append(id)
    if search:
        q += " AND name LIKE ?"
        params.append(f"%{search}%")
    q += " LIMIT ?"
    params.append(limit)
    return json.dumps(_rows(conn.execute(q, params)))


@mcp.tool()
def get_products(limit: int = 10, search: str = "", id: int = 0) -> str:
    conn = get_conn()
    q = "SELECT id, name, list_price, standard_price, type, default_code FROM products WHERE 1=1"
    params: list = []
    if id:
        q += " AND id = ?"
        params.append(id)
    if search:
        q += " AND name LIKE ?"
        params.append(f"%{search}%")
    q += " LIMIT ?"
    params.append(limit)
    return json.dumps(_rows(conn.execute(q, params)))


@mcp.tool()
def get_purchase_orders(limit: int = 10, search: str = "", id: int = 0) -> str:
    conn = get_conn()
    q = "SELECT id, name, partner_id, partner_name, date_order, amount_total, state FROM purchase_orders WHERE 1=1"
    params: list = []
    if id:
        q += " AND id = ?"
        params.append(id)
    if search:
        q += " AND name LIKE ?"
        params.append(f"%{search}%")
    q += " ORDER BY date_order DESC LIMIT ?"
    params.append(limit)
    return json.dumps(_rows(conn.execute(q, params)))


@mcp.tool()
def get_invoices(limit: int = 10, search: str = "", id: int = 0) -> str:
    conn = get_conn()
    q = "SELECT id, name, partner_id, partner_name, invoice_date, amount_total, state, payment_state FROM invoices WHERE 1=1"
    params: list = []
    if id:
        q += " AND id = ?"
        params.append(id)
    if search:
        q += " AND name LIKE ?"
        params.append(f"%{search}%")
    q += " ORDER BY invoice_date DESC LIMIT ?"
    params.append(limit)
    return json.dumps(_rows(conn.execute(q, params)))


@mcp.tool()
def get_vendor_bills(limit: int = 10, search: str = "", id: int = 0) -> str:
    conn = get_conn()
    q = "SELECT id, name, partner_id, partner_name, invoice_date, amount_total, state, payment_state FROM vendor_bills WHERE 1=1"
    params: list = []
    if id:
        q += " AND id = ?"
        params.append(id)
    if search:
        q += " AND name LIKE ?"
        params.append(f"%{search}%")
    q += " ORDER BY invoice_date DESC LIMIT ?"
    params.append(limit)
    return json.dumps(_rows(conn.execute(q, params)))


@mcp.tool()
def create_sales_order(partner_id: int, product_id: int, quantity: float) -> str:
    conn = get_conn()
    customer = conn.execute("SELECT name FROM customers WHERE id = ?", [partner_id]).fetchone()
    if not customer:
        return json.dumps({"error": f"Customer {partner_id} not found"})
    product = conn.execute("SELECT list_price FROM products WHERE id = ?", [product_id]).fetchone()
    if not product:
        return json.dumps({"error": f"Product {product_id} not found"})
    amount = round(product["list_price"] * quantity, 2)
    count = conn.execute("SELECT COUNT(*) FROM sales_orders").fetchone()[0]
    name = f"SO/{count + 1:03d}"
    cur = conn.execute(
        "INSERT INTO sales_orders (name, partner_id, partner_name, date_order, amount_total) VALUES (?, ?, ?, date('now'), ?)",
        [name, partner_id, customer["name"], amount],
    )
    conn.commit()
    return json.dumps({"order_id": cur.lastrowid})


@mcp.tool()
def create_purchase_order(vendor_id: int, product_id: int, quantity: float) -> str:
    conn = get_conn()
    vendor = conn.execute("SELECT name FROM vendors WHERE id = ?", [vendor_id]).fetchone()
    if not vendor:
        return json.dumps({"error": f"Vendor {vendor_id} not found"})
    product = conn.execute("SELECT standard_price FROM products WHERE id = ?", [product_id]).fetchone()
    if not product:
        return json.dumps({"error": f"Product {product_id} not found"})
    amount = round(product["standard_price"] * quantity, 2)
    count = conn.execute("SELECT COUNT(*) FROM purchase_orders").fetchone()[0]
    name = f"PO/{count + 1:03d}"
    cur = conn.execute(
        "INSERT INTO purchase_orders (name, partner_id, partner_name, date_order, amount_total) VALUES (?, ?, ?, date('now'), ?)",
        [name, vendor_id, vendor["name"], amount],
    )
    conn.commit()
    return json.dumps({"order_id": cur.lastrowid})


@mcp.tool()
def create_customer_invoice(partner_id: int, product_id: int, quantity: float, price_unit: float) -> str:
    conn = get_conn()
    customer = conn.execute("SELECT name FROM customers WHERE id = ?", [partner_id]).fetchone()
    if not customer:
        return json.dumps({"error": f"Customer {partner_id} not found"})
    amount = round(price_unit * quantity, 2)
    count = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
    name = f"INV/{count + 1:03d}"
    cur = conn.execute(
        "INSERT INTO invoices (name, partner_id, partner_name, invoice_date, amount_total) VALUES (?, ?, ?, date('now'), ?)",
        [name, partner_id, customer["name"], amount],
    )
    conn.commit()
    return json.dumps({"invoice_id": cur.lastrowid})


@mcp.tool()
def create_vendor_bill(vendor_id: int, product_id: int, quantity: float, price_unit: float) -> str:
    conn = get_conn()
    vendor = conn.execute("SELECT name FROM vendors WHERE id = ?", [vendor_id]).fetchone()
    if not vendor:
        return json.dumps({"error": f"Vendor {vendor_id} not found"})
    amount = round(price_unit * quantity, 2)
    count = conn.execute("SELECT COUNT(*) FROM vendor_bills").fetchone()[0]
    name = f"BILL/{count + 1:03d}"
    cur = conn.execute(
        "INSERT INTO vendor_bills (name, partner_id, partner_name, invoice_date, amount_total) VALUES (?, ?, ?, date('now'), ?)",
        [name, vendor_id, vendor["name"], amount],
    )
    conn.commit()
    return json.dumps({"bill_id": cur.lastrowid})


@mcp.tool()
def confirm_sales_order(order_id: int) -> str:
    conn = get_conn()
    order = conn.execute("SELECT id, name, state FROM sales_orders WHERE id = ?", [order_id]).fetchone()
    if not order:
        return json.dumps({"error": f"Order {order_id} not found"})
    conn.execute("UPDATE sales_orders SET state = ? WHERE id = ?", ["confirmed", order_id])
    conn.commit()
    return json.dumps({"order_id": order_id, "name": order["name"], "state": "confirmed"})


@mcp.tool()
def register_payment(invoice_id: int, amount: float) -> str:
    conn = get_conn()
    invoice = conn.execute("SELECT id, payment_state FROM invoices WHERE id = ?", [invoice_id]).fetchone()
    if not invoice:
        bill = conn.execute("SELECT id, payment_state FROM vendor_bills WHERE id = ?", [invoice_id]).fetchone()
        if not bill:
            return json.dumps({"error": f"Invoice/bill {invoice_id} not found"})
        conn.execute("UPDATE vendor_bills SET payment_state = ? WHERE id = ?", ["paid", invoice_id])
        conn.commit()
        return json.dumps({"payment_id": invoice_id, "amount": amount, "status": "paid"})
    conn.execute("UPDATE invoices SET payment_state = ? WHERE id = ?", ["paid", invoice_id])
    conn.commit()
    return json.dumps({"payment_id": invoice_id, "amount": amount, "status": "paid"})


@mcp.tool()
def update_sales_order(order_id: int, partner_id: int = None, notes: str = None) -> str:
    conn = get_conn()
    updates = []
    params = []
    if partner_id is not None:
        updates.append("partner_id = ?")
        params.append(partner_id)
    if notes is not None:
        updates.append("notes = ?")
        params.append(notes)
    if not updates:
        return json.dumps({"error": "No fields to update"})
    params.append(order_id)
    q = f"UPDATE sales_orders SET {', '.join(updates)} WHERE id = ?"
    conn.execute(q, params)
    conn.commit()
    updated = [k for k in ["partner_id", "notes"] if k in [u.split(" ")[0] for u in updates]]
    return json.dumps({"order_id": order_id, "updated_fields": updated})


@mcp.tool()
def update_purchase_order(order_id: int, partner_id: int = None, notes: str = None) -> str:
    conn = get_conn()
    updates = []
    params = []
    if partner_id is not None:
        updates.append("partner_id = ?")
        params.append(partner_id)
    if notes is not None:
        updates.append("notes = ?")
        params.append(notes)
    if not updates:
        return json.dumps({"error": "No fields to update"})
    params.append(order_id)
    q = f"UPDATE purchase_orders SET {', '.join(updates)} WHERE id = ?"
    conn.execute(q, params)
    conn.commit()
    updated = [k for k in ["partner_id", "notes"] if k in [u.split(" ")[0] for u in updates]]
    return json.dumps({"order_id": order_id, "updated_fields": updated})


@mcp.tool()
def update_invoice(invoice_id: int, partner_id: int = None, notes: str = None) -> str:
    conn = get_conn()
    updates = []
    params = []
    if partner_id is not None:
        updates.append("partner_id = ?")
        params.append(partner_id)
    if notes is not None:
        updates.append("notes = ?")
        params.append(notes)
    if not updates:
        return json.dumps({"error": "No fields to update"})
    params.append(invoice_id)
    q = f"UPDATE invoices SET {', '.join(updates)} WHERE id = ?"
    conn.execute(q, params)
    conn.commit()
    updated = [k for k in ["partner_id", "notes"] if k in [u.split(" ")[0] for u in updates]]
    return json.dumps({"invoice_id": invoice_id, "updated_fields": updated})


def dashboard_stats() -> dict | None:
    try:
        conn = get_conn()
        sales = conn.execute("SELECT COUNT(*) FROM sales_orders").fetchone()[0]
        customers = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        products = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        purchases = conn.execute("SELECT COUNT(*) FROM purchase_orders").fetchone()[0]
        invoices = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
        conn.close()
        return {
            "total_sales_orders": sales,
            "total_customers": customers,
            "total_products": products,
            "total_purchase_orders": purchases,
            "total_invoices": invoices,
        }
    except Exception:
        return None


if __name__ == "__main__":
    mcp.run(transport="stdio")
