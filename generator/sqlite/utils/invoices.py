import random
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from utils.data import PAYMENT_STATES

# PAYMENT_STATES = ["paid", "paid", "not_paid", "not_paid", "partial"]


def generate_invoices(conn: sqlite3.Connection, customer_ids: list, product_ids: list):
    print("Creating customer invoices...")
    for _ in range(15):
        customer_id = random.choice(customer_ids)
        customer_name = conn.execute("SELECT name FROM customers WHERE id=?", [customer_id]).fetchone()[0]
        pid = random.choice(product_ids)
        price = conn.execute("SELECT list_price FROM products WHERE id=?", [pid]).fetchone()[0]
        qty = random.randint(1, 5)
        amount = round(price * qty, 2)
        payment_state = random.choice(PAYMENT_STATES)

        count = conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0]
        name = f"INV/{count + 1:03d}"
        conn.execute(
            "INSERT INTO invoices (name, partner_id, partner_name, invoice_date, amount_total, state, payment_state) VALUES (?, ?, ?, date('now', ?), ?, 'posted', ?)",
            [name, customer_id, customer_name, f"-{random.randint(0, 90)} days", amount, payment_state],
        )
        print(f"  {name}: {customer_name} — {amount} ({payment_state})")

    print("Creating vendor bills...")
    vendor_ids = [row[0] for row in conn.execute("SELECT id FROM vendors").fetchall()]
    for _ in range(10):
        vendor_id = random.choice(vendor_ids)
        vendor_name = conn.execute("SELECT name FROM vendors WHERE id=?", [vendor_id]).fetchone()[0]
        pid = random.choice(product_ids)
        price = conn.execute("SELECT standard_price FROM products WHERE id=?", [pid]).fetchone()[0]
        qty = random.randint(1, 10)
        amount = round(price * qty, 2)
        payment_state = random.choice(PAYMENT_STATES)

        count = conn.execute("SELECT COUNT(*) FROM vendor_bills").fetchone()[0]
        name = f"BILL/{count + 1:03d}"
        conn.execute(
            "INSERT INTO vendor_bills (name, partner_id, partner_name, invoice_date, amount_total, state, payment_state) VALUES (?, ?, ?, date('now', ?), ?, 'posted', ?)",
            [name, vendor_id, vendor_name, f"-{random.randint(0, 90)} days", amount, payment_state],
        )
        print(f"  {name}: {vendor_name} — {amount} ({payment_state})")

    conn.commit()
    print("Invoice generation complete.")
