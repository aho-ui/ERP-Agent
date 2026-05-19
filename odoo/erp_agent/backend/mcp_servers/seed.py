import sqlite3
import tempfile
from datetime import date, timedelta
from pathlib import Path


def _resolve_db_path() -> Path:
    plugin_dir = Path(__file__).resolve().parent
    try:
        plugin_dir.mkdir(parents=True, exist_ok=True)
        probe = plugin_dir / ".write_test"
        probe.write_text("")
        probe.unlink()
        return plugin_dir / "demo.db"
    except OSError:
        return Path(tempfile.gettempdir()) / "erp_agent_demo.db"


DB_PATH = _resolve_db_path()

_SCHEMA = """
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
"""

_CUSTOMERS = [
    ("Acme Corp", "ops@acme.test", "555-0101"),
    ("Globex Inc", "billing@globex.test", "555-0102"),
    ("Initech Ltd", "ap@initech.test", "555-0103"),
    ("Umbrella Co", "buyer@umbrella.test", "555-0104"),
    ("Stark Industries", "sales@stark.test", "555-0105"),
]

_VENDORS = [
    ("Wayne Supply", "sales@wayne.test", "555-0201"),
    ("Hooli Logistics", "ops@hooli.test", "555-0202"),
    ("Pied Piper Parts", "shipping@pp.test", "555-0203"),
    ("Tyrell Components", "vendor@tyrell.test", "555-0204"),
    ("Cyberdyne Goods", "supply@cyberdyne.test", "555-0205"),
]

_PRODUCTS = [
    ("Widget Mk1", 19.99, 7.50, "WID-001"),
    ("Widget Mk2", 29.99, 12.00, "WID-002"),
    ("Gadget Pro", 99.00, 42.00, "GAD-PRO"),
    ("Gizmo Lite", 14.50, 5.25, "GIZ-LIT"),
    ("Sprocket Bundle", 49.00, 18.00, "SPR-BND"),
]


def _seed(conn: sqlite3.Connection) -> None:
    conn.executemany(
        "INSERT INTO customers (name, email, phone) VALUES (?, ?, ?)", _CUSTOMERS
    )
    conn.executemany(
        "INSERT INTO vendors (name, email, phone) VALUES (?, ?, ?)", _VENDORS
    )
    conn.executemany(
        "INSERT INTO products (name, list_price, standard_price, default_code) VALUES (?, ?, ?, ?)",
        _PRODUCTS,
    )

    today = date.today()

    sales = []
    for i in range(5):
        cust_id = (i % 5) + 1
        cust_name = _CUSTOMERS[i % 5][0]
        amount = round((i + 1) * 19.99 * 3, 2)
        sales.append((
            f"SO{1000 + i}", cust_id, cust_name,
            (today - timedelta(days=i * 2)).isoformat(), amount, "sale",
        ))
    conn.executemany(
        "INSERT INTO sales_orders (name, partner_id, partner_name, date_order, amount_total, state) VALUES (?, ?, ?, ?, ?, ?)",
        sales,
    )

    purchases = []
    for i in range(5):
        v_id = (i % 5) + 1
        v_name = _VENDORS[i % 5][0]
        amount = round((i + 1) * 12.00 * 4, 2)
        purchases.append((
            f"PO{2000 + i}", v_id, v_name,
            (today - timedelta(days=i * 3)).isoformat(), amount, "purchase",
        ))
    conn.executemany(
        "INSERT INTO purchase_orders (name, partner_id, partner_name, date_order, amount_total, state) VALUES (?, ?, ?, ?, ?, ?)",
        purchases,
    )

    invoices = []
    for i in range(5):
        cust_id = (i % 5) + 1
        cust_name = _CUSTOMERS[i % 5][0]
        amount = round((i + 1) * 19.99 * 2, 2)
        invoices.append((
            f"INV{3000 + i}", cust_id, cust_name,
            (today - timedelta(days=i)).isoformat(), amount, "posted",
            "paid" if i % 2 == 0 else "not_paid",
        ))
    conn.executemany(
        "INSERT INTO invoices (name, partner_id, partner_name, invoice_date, amount_total, state, payment_state) VALUES (?, ?, ?, ?, ?, ?, ?)",
        invoices,
    )

    bills = []
    for i in range(5):
        v_id = (i % 5) + 1
        v_name = _VENDORS[i % 5][0]
        amount = round((i + 1) * 12.00 * 2, 2)
        bills.append((
            f"BILL{4000 + i}", v_id, v_name,
            (today - timedelta(days=i + 1)).isoformat(), amount, "posted",
            "paid" if i % 3 == 0 else "not_paid",
        ))
    conn.executemany(
        "INSERT INTO vendor_bills (name, partner_id, partner_name, invoice_date, amount_total, state, payment_state) VALUES (?, ?, ?, ?, ?, ?, ?)",
        bills,
    )

    conn.commit()


def ensure_seeded() -> None:
    if DB_PATH.exists():
        return
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(_SCHEMA)
        _seed(conn)
    finally:
        conn.close()
