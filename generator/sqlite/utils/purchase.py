import random
import sqlite3

DATES = [
    "2025-10-02", "2025-10-09", "2025-10-16", "2025-10-23",
    "2025-11-06", "2025-11-13", "2025-11-20",
    "2025-12-04", "2025-12-11", "2025-12-18",
    "2026-01-08", "2026-01-15", "2026-01-22",
    "2026-02-05", "2026-02-12", "2026-02-19",
    "2026-03-05", "2026-03-12",
]

STATES = ["purchase", "purchase", "purchase", "done", "done", "draft"]


def generate_purchase(conn: sqlite3.Connection, vendor_ids: list, product_ids: list):
    print("Creating purchase orders...")
    for _ in range(15):
        vendor_id = random.choice(vendor_ids)
        vendor_name = conn.execute("SELECT name FROM vendors WHERE id=?", [vendor_id]).fetchone()[0]
        date = random.choice(DATES)
        state = random.choice(STATES)

        line_count = random.randint(1, 3)
        amount = 0.0
        for _ in range(line_count):
            pid = random.choice(product_ids)
            price = conn.execute("SELECT standard_price FROM products WHERE id=?", [pid]).fetchone()[0]
            qty = random.randint(1, 10)
            amount += round(price * qty, 2)
        amount = round(amount, 2)

        count = conn.execute("SELECT COUNT(*) FROM purchase_orders").fetchone()[0]
        name = f"PO/{count + 1:03d}"
        conn.execute(
            "INSERT INTO purchase_orders (name, partner_id, partner_name, date_order, amount_total, state) VALUES (?, ?, ?, ?, ?, ?)",
            [name, vendor_id, vendor_name, date, amount, state],
        )
        print(f"  {name}: {vendor_name} — {amount} ({state})")

    conn.commit()
    print("Purchase order generation complete.")
