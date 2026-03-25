import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils.sales import generate_sales
from utils.vendors import generate_vendors
from utils.purchase import generate_purchase
from utils.invoices import generate_invoices

DB_PATH = Path(__file__).resolve().parents[2] / "demo.db"


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def reset(conn: sqlite3.Connection):
    print("Resetting demo database...")
    conn.executescript("""
        DROP TABLE IF EXISTS vendor_bills;
        DROP TABLE IF EXISTS invoices;
        DROP TABLE IF EXISTS purchase_orders;
        DROP TABLE IF EXISTS sales_orders;
        DROP TABLE IF EXISTS products;
        DROP TABLE IF EXISTS vendors;
        DROP TABLE IF EXISTS customers;
    """)
    conn.executescript("""
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            name TEXT, email TEXT, phone TEXT, customer_rank INTEGER DEFAULT 1
        );
        CREATE TABLE vendors (
            id INTEGER PRIMARY KEY,
            name TEXT, email TEXT, phone TEXT, supplier_rank INTEGER DEFAULT 1
        );
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT, list_price REAL, standard_price REAL,
            type TEXT DEFAULT 'consu', default_code TEXT
        );
        CREATE TABLE sales_orders (
            id INTEGER PRIMARY KEY,
            name TEXT, partner_id INTEGER, partner_name TEXT,
            date_order TEXT, amount_total REAL, state TEXT DEFAULT 'sale'
        );
        CREATE TABLE purchase_orders (
            id INTEGER PRIMARY KEY,
            name TEXT, partner_id INTEGER, partner_name TEXT,
            date_order TEXT, amount_total REAL, state TEXT DEFAULT 'purchase'
        );
        CREATE TABLE invoices (
            id INTEGER PRIMARY KEY,
            name TEXT, partner_id INTEGER, partner_name TEXT,
            invoice_date TEXT, amount_total REAL,
            state TEXT DEFAULT 'posted', payment_state TEXT DEFAULT 'not_paid'
        );
        CREATE TABLE vendor_bills (
            id INTEGER PRIMARY KEY,
            name TEXT, partner_id INTEGER, partner_name TEXT,
            invoice_date TEXT, amount_total REAL,
            state TEXT DEFAULT 'posted', payment_state TEXT DEFAULT 'not_paid'
        );
    """)
    conn.commit()
    print("Reset complete.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sales", action="store_true")
    parser.add_argument("--vendors", action="store_true")
    parser.add_argument("--purchase", action="store_true")
    parser.add_argument("--invoices", action="store_true")
    parser.add_argument("--reset", action="store_true", help="Wipe and regenerate all data")
    args = parser.parse_args()

    run_all = not any([args.sales, args.vendors, args.purchase, args.invoices])

    conn = connect()
    print(f"Connected to {DB_PATH}")

    if args.reset or run_all:
        reset(conn)

    customer_ids, product_ids = None, None

    if args.sales or run_all:
        customer_ids, product_ids = generate_sales(conn)

    if args.vendors or run_all:
        generate_vendors(conn)

    if args.purchase or run_all:
        if not product_ids:
            product_ids = [row[0] for row in conn.execute("SELECT id FROM products").fetchall()]
        vendor_ids = [row[0] for row in conn.execute("SELECT id FROM vendors").fetchall()]
        generate_purchase(conn, vendor_ids, product_ids)

    if args.invoices or run_all:
        if not customer_ids:
            customer_ids = [row[0] for row in conn.execute("SELECT id FROM customers").fetchall()]
        if not product_ids:
            product_ids = [row[0] for row in conn.execute("SELECT id FROM products").fetchall()]
        generate_invoices(conn, customer_ids, product_ids)

    print("Done.")


def check() -> bool:
    try:
        conn = connect()
        conn.close()
        return True
    except Exception:
        return False


def run():
    conn = connect()
    reset(conn)
    customer_ids, product_ids = generate_sales(conn)
    generate_vendors(conn)
    vendor_ids = [row[0] for row in conn.execute("SELECT id FROM vendors").fetchall()]
    generate_purchase(conn, vendor_ids, product_ids)
    generate_invoices(conn, customer_ids, product_ids)


if __name__ == "__main__":
    main()
