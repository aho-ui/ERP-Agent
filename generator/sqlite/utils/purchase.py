import random
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from utils.data import PURCHASE_DATES, PURCHASE_STATES

# DATES = [...]
# STATES = [...]


def generate_purchase(conn: sqlite3.Connection, vendor_ids: list, product_ids: list):
    print("Creating purchase orders...")
    for _ in range(15):
        vendor_id = random.choice(vendor_ids)
        vendor_name = conn.execute("SELECT name FROM vendors WHERE id=?", [vendor_id]).fetchone()[0]
        date = random.choice(PURCHASE_DATES)
        state = random.choice(PURCHASE_STATES)

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
