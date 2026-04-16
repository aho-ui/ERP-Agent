import random
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from utils.data import CUSTOMERS, PRODUCTS, SALES_DATES, SALES_STATES

# CUSTOMERS = [
#     ("Acme Corp", "contact@acme.com", "+1-555-0101"),
#     ...
# ]
# PRODUCTS = [
#     ("Office Chair", 299.99, 130.00, "consu", "OFF-CHR"),
#     ...
# ]
# DATES = [...]
# STATES = [...]


def generate_sales(conn: sqlite3.Connection):
    print("Creating customers...")
    customer_ids = []
    for c in [c for c in CUSTOMERS if c["sqlite"]]:
        cur = conn.execute(
            "INSERT INTO customers (name, email, phone) VALUES (?, ?, ?)",
            [c["name"], c["email"], c["phone"]],
        )
        customer_ids.append(cur.lastrowid)
        print(f"  Customer: {c['name']} (id={cur.lastrowid})")

    print("Creating products...")
    product_ids = []
    for p in [p for p in PRODUCTS if p["sqlite"]]:
        cur = conn.execute(
            "INSERT INTO products (name, list_price, standard_price, type, default_code) VALUES (?, ?, ?, ?, ?)",
            [p["name"], p["list_price"], p["standard_price"], p["type"], p["default_code"]],
        )
        product_ids.append(cur.lastrowid)
        print(f"  Product: {p['name']} (id={cur.lastrowid})")

    print("Creating sales orders...")
    for i in range(20):
        customer_id = random.choice(customer_ids)
        customer_name = conn.execute("SELECT name FROM customers WHERE id=?", [customer_id]).fetchone()[0]
        date = random.choice(SALES_DATES)
        state = random.choice(SALES_STATES)

        line_count = random.randint(1, 3)
        amount = 0.0
        for _ in range(line_count):
            pid = random.choice(product_ids)
            price = conn.execute("SELECT list_price FROM products WHERE id=?", [pid]).fetchone()[0]
            qty = random.randint(1, 5)
            amount += round(price * qty, 2)
        amount = round(amount, 2)

        count = conn.execute("SELECT COUNT(*) FROM sales_orders").fetchone()[0]
        name = f"SO/{count + 1:03d}"
        conn.execute(
            "INSERT INTO sales_orders (name, partner_id, partner_name, date_order, amount_total, state) VALUES (?, ?, ?, ?, ?, ?)",
            [name, customer_id, customer_name, date, amount, state],
        )
        print(f"  {name}: {customer_name} — {amount} ({state})")

    conn.commit()
    print("Sales generation complete.")
    return customer_ids, product_ids
