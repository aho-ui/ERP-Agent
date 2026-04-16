import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from utils.data import VENDORS

# VENDORS = [
#     ("TechSupply Co", "orders@techsupply.com", "+1-555-0201"),
#     ...
# ]


def generate_vendors(conn: sqlite3.Connection):
    print("Creating vendors...")
    vendor_ids = []
    for v in [v for v in VENDORS if v["sqlite"]]:
        cur = conn.execute(
            "INSERT INTO vendors (name, email, phone) VALUES (?, ?, ?)",
            [v["name"], v["email"], v["phone"]],
        )
        vendor_ids.append(cur.lastrowid)
        print(f"  Vendor: {v['name']} (id={cur.lastrowid})")
    conn.commit()
    print("Vendor generation complete.")
    return vendor_ids
