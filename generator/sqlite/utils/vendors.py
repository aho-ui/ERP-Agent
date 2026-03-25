import sqlite3

VENDORS = [
    ("TechSupply Co", "orders@techsupply.com", "+1-555-0201"),
    ("Office Depot Pro", "b2b@officedepotpro.com", "+1-555-0202"),
    ("GlobalParts Ltd", "sales@globalparts.com", "+1-555-0203"),
    ("FastShip Supplies", "contact@fastship.com", "+1-555-0204"),
    ("PrimeTech Wholesale", "wholesale@primetech.com", "+1-555-0205"),
    ("BlueStar Supplies", "orders@bluestar.com", "+1-555-0206"),
    ("Delta Components", "sales@delta.com", "+1-555-0207"),
    ("Metro Materials", "contact@metro.com", "+1-555-0208"),
]


def generate_vendors(conn: sqlite3.Connection):
    print("Creating vendors...")
    vendor_ids = []
    for name, email, phone in VENDORS:
        cur = conn.execute(
            "INSERT INTO vendors (name, email, phone) VALUES (?, ?, ?)",
            [name, email, phone],
        )
        vendor_ids.append(cur.lastrowid)
        print(f"  Vendor: {name} (id={cur.lastrowid})")
    conn.commit()
    print("Vendor generation complete.")
    return vendor_ids
