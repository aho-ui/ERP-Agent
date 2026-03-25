import random
import sqlite3

CUSTOMERS = [
    ("Acme Corp", "contact@acme.com", "+1-555-0101"),
    ("Globex Industries", "info@globex.com", "+1-555-0102"),
    ("Initech Solutions", "hello@initech.com", "+1-555-0103"),
    ("Umbrella Ltd", "sales@umbrella.com", "+1-555-0104"),
    ("Stark Enterprises", "info@stark.com", "+1-555-0105"),
    ("Wayne Industries", "contact@wayne.com", "+1-555-0106"),
    ("Cyberdyne Systems", "info@cyberdyne.com", "+1-555-0107"),
    ("Weyland Corp", "hello@weyland.com", "+1-555-0108"),
    ("Oscorp Technologies", "sales@oscorp.com", "+1-555-0109"),
    ("Massive Dynamic", "info@massivedynamic.com", "+1-555-0110"),
]

PRODUCTS = [
    ("Office Chair", 299.99, 130.00, "consu", "OFF-CHR"),
    ("Standing Desk", 599.99, 270.00, "consu", "STD-DSK"),
    ("Laptop Stand", 49.99, 20.00, "consu", "LPT-STD"),
    ("Wireless Mouse", 39.99, 15.00, "consu", "WRL-MSE"),
    ("Mechanical Keyboard", 129.99, 55.00, "consu", "MCH-KBD"),
    ('Monitor 27"', 449.99, 200.00, "consu", "MON-27"),
    ("USB Hub", 29.99, 10.00, "consu", "USB-HUB"),
    ("Webcam HD", 89.99, 38.00, "consu", "WEB-HD"),
    ("IT Support", 150.00, 0.00, "service", "SVC-IT"),
    ("Consulting Hour", 200.00, 0.00, "service", "SVC-CNS"),
    ("Network Switch", 189.99, 80.00, "consu", "NET-SWT"),
    ("UPS Battery", 249.99, 100.00, "consu", "UPS-BAT"),
    ("Docking Station", 179.99, 75.00, "consu", "DCK-STN"),
    ("Headset Pro", 119.99, 48.00, "consu", "HDS-PRO"),
    ("Smart Projector", 899.99, 400.00, "consu", "PRJ-SMT"),
]

DATES = [
    "2025-10-01", "2025-10-08", "2025-10-15", "2025-10-22", "2025-10-29",
    "2025-11-05", "2025-11-12", "2025-11-19", "2025-11-26",
    "2025-12-03", "2025-12-10", "2025-12-17",
    "2026-01-07", "2026-01-14", "2026-01-21", "2026-01-28",
    "2026-02-04", "2026-02-11", "2026-02-18", "2026-02-25",
    "2026-03-04", "2026-03-11",
]

STATES = ["sale", "sale", "sale", "sale", "done", "done", "draft"]


def generate_sales(conn: sqlite3.Connection):
    print("Creating customers...")
    customer_ids = []
    for name, email, phone in CUSTOMERS:
        cur = conn.execute(
            "INSERT INTO customers (name, email, phone) VALUES (?, ?, ?)",
            [name, email, phone],
        )
        customer_ids.append(cur.lastrowid)
        print(f"  Customer: {name} (id={cur.lastrowid})")

    print("Creating products...")
    product_ids = []
    for name, list_price, standard_price, ptype, code in PRODUCTS:
        cur = conn.execute(
            "INSERT INTO products (name, list_price, standard_price, type, default_code) VALUES (?, ?, ?, ?, ?)",
            [name, list_price, standard_price, ptype, code],
        )
        product_ids.append(cur.lastrowid)
        print(f"  Product: {name} (id={cur.lastrowid})")

    print("Creating sales orders...")
    for i in range(20):
        customer_id = random.choice(customer_ids)
        customer_name = conn.execute("SELECT name FROM customers WHERE id=?", [customer_id]).fetchone()[0]
        date = random.choice(DATES)
        state = random.choice(STATES)

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
