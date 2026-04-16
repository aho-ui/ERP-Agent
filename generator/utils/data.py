CUSTOMERS = [
    {"name": "Acme Corp",            "email": "contact@acme.com",           "phone": "+1-555-0101", "is_company": True, "customer_rank": 1, "sqlite": True, "odoo": True},
    {"name": "Globex Industries",    "email": "info@globex.com",            "phone": "+1-555-0102", "is_company": True, "customer_rank": 1, "sqlite": True, "odoo": True},
    {"name": "Initech Solutions",    "email": "hello@initech.com",          "phone": "+1-555-0103", "is_company": True, "customer_rank": 1, "sqlite": True, "odoo": True},
    {"name": "Umbrella Ltd",         "email": "sales@umbrella.com",         "phone": "+1-555-0104", "is_company": True, "customer_rank": 1, "sqlite": True, "odoo": True},
    {"name": "Stark Enterprises",    "email": "info@stark.com",             "phone": "+1-555-0105", "is_company": True, "customer_rank": 1, "sqlite": True, "odoo": True},
    {"name": "Wayne Industries",     "email": "contact@wayne.com",          "phone": "+1-555-0106", "is_company": True, "customer_rank": 1, "sqlite": True, "odoo": False},
    {"name": "Cyberdyne Systems",    "email": "info@cyberdyne.com",         "phone": "+1-555-0107", "is_company": True, "customer_rank": 1, "sqlite": True, "odoo": False},
    {"name": "Weyland Corp",         "email": "hello@weyland.com",          "phone": "+1-555-0108", "is_company": True, "customer_rank": 1, "sqlite": True, "odoo": False},
    {"name": "Oscorp Technologies",  "email": "sales@oscorp.com",           "phone": "+1-555-0109", "is_company": True, "customer_rank": 1, "sqlite": True, "odoo": False},
    {"name": "Massive Dynamic",      "email": "info@massivedynamic.com",    "phone": "+1-555-0110", "is_company": True, "customer_rank": 1, "sqlite": True, "odoo": False},
]

PRODUCTS = [
    {"name": "Office Chair",        "list_price": 299.99, "standard_price": 130.00, "type": "consu",   "default_code": "OFF-CHR", "sqlite": True, "odoo": True},
    {"name": "Standing Desk",       "list_price": 599.99, "standard_price": 270.00, "type": "consu",   "default_code": "STD-DSK", "sqlite": True, "odoo": True},
    {"name": "Laptop Stand",        "list_price":  49.99, "standard_price":  20.00, "type": "consu",   "default_code": "LPT-STD", "sqlite": True, "odoo": True},
    {"name": "Wireless Mouse",      "list_price":  39.99, "standard_price":  15.00, "type": "consu",   "default_code": "WRL-MSE", "sqlite": True, "odoo": True},
    {"name": "Mechanical Keyboard", "list_price": 129.99, "standard_price":  55.00, "type": "consu",   "default_code": "MCH-KBD", "sqlite": True, "odoo": True},
    {"name": 'Monitor 27"',         "list_price": 449.99, "standard_price": 200.00, "type": "consu",   "default_code": "MON-27",  "sqlite": True, "odoo": True},
    {"name": "USB Hub",             "list_price":  29.99, "standard_price":  10.00, "type": "consu",   "default_code": "USB-HUB", "sqlite": True, "odoo": True},
    {"name": "Webcam HD",           "list_price":  89.99, "standard_price":  38.00, "type": "consu",   "default_code": "WEB-HD",  "sqlite": True, "odoo": True},
    {"name": "IT Support",          "list_price": 150.00, "standard_price":   0.00, "type": "service", "default_code": "SVC-IT",  "sqlite": True, "odoo": True},
    {"name": "Consulting Hour",     "list_price": 200.00, "standard_price":   0.00, "type": "service", "default_code": "SVC-CNS", "sqlite": True, "odoo": True},
    {"name": "Network Switch",      "list_price": 189.99, "standard_price":  80.00, "type": "consu",   "default_code": "NET-SWT", "sqlite": True, "odoo": False},
    {"name": "UPS Battery",         "list_price": 249.99, "standard_price": 100.00, "type": "consu",   "default_code": "UPS-BAT", "sqlite": True, "odoo": False},
    {"name": "Docking Station",     "list_price": 179.99, "standard_price":  75.00, "type": "consu",   "default_code": "DCK-STN", "sqlite": True, "odoo": False},
    {"name": "Headset Pro",         "list_price": 119.99, "standard_price":  48.00, "type": "consu",   "default_code": "HDS-PRO", "sqlite": True, "odoo": False},
    {"name": "Smart Projector",     "list_price": 899.99, "standard_price": 400.00, "type": "consu",   "default_code": "PRJ-SMT", "sqlite": True, "odoo": False},
]

VENDORS = [
    {"name": "TechSupply Co",       "email": "orders@techsupply.com",       "phone": "+1-555-0201", "is_company": True, "supplier_rank": 1, "sqlite": True, "odoo": True},
    {"name": "Office Depot Pro",    "email": "b2b@officedepotpro.com",      "phone": "+1-555-0202", "is_company": True, "supplier_rank": 1, "sqlite": True, "odoo": True},
    {"name": "GlobalParts Ltd",     "email": "sales@globalparts.com",       "phone": "+1-555-0203", "is_company": True, "supplier_rank": 1, "sqlite": True, "odoo": True},
    {"name": "FastShip Supplies",   "email": "contact@fastship.com",        "phone": "+1-555-0204", "is_company": True, "supplier_rank": 1, "sqlite": True, "odoo": True},
    {"name": "PrimeTech Wholesale", "email": "wholesale@primetech.com",     "phone": "+1-555-0205", "is_company": True, "supplier_rank": 1, "sqlite": True, "odoo": True},
    {"name": "BlueStar Supplies",   "email": "orders@bluestar.com",         "phone": "+1-555-0206", "is_company": True, "supplier_rank": 1, "sqlite": True, "odoo": False},
    {"name": "Delta Components",    "email": "sales@delta.com",             "phone": "+1-555-0207", "is_company": True, "supplier_rank": 1, "sqlite": True, "odoo": False},
    {"name": "Metro Materials",     "email": "contact@metro.com",           "phone": "+1-555-0208", "is_company": True, "supplier_rank": 1, "sqlite": True, "odoo": False},
]

SALES_DATES = [
    "2025-10-01", "2025-10-08", "2025-10-15", "2025-10-22", "2025-10-29",
    "2025-11-05", "2025-11-12", "2025-11-19", "2025-11-26",
    "2025-12-03", "2025-12-10", "2025-12-17",
    "2026-01-07", "2026-01-14", "2026-01-21", "2026-01-28",
    "2026-02-04", "2026-02-11", "2026-02-18", "2026-02-25",
    "2026-03-04", "2026-03-11",
]

PURCHASE_DATES = [
    "2025-10-02", "2025-10-09", "2025-10-16", "2025-10-23",
    "2025-11-06", "2025-11-13", "2025-11-20",
    "2025-12-04", "2025-12-11", "2025-12-18",
    "2026-01-08", "2026-01-15", "2026-01-22",
    "2026-02-05", "2026-02-12", "2026-02-19",
    "2026-03-05", "2026-03-12",
]

SALES_STATES = ["sale", "sale", "sale", "sale", "done", "done", "draft"]
PURCHASE_STATES = ["purchase", "purchase", "purchase", "done", "done", "draft"]
PAYMENT_STATES = ["paid", "paid", "not_paid", "not_paid", "partial"]

# odoo-only
DEPARTMENTS = ["Sales", "Finance", "Procurement", "Operations", "Supply Chain"]

EMPLOYEES = [
    {"name": "Alice Chen",    "job_title": "Sales Manager",         "department": "Sales"},
    {"name": "Bob Martinez",  "job_title": "Financial Analyst",     "department": "Finance"},
    {"name": "Carol Smith",   "job_title": "Procurement Officer",   "department": "Procurement"},
    {"name": "David Lee",     "job_title": "Operations Lead",       "department": "Operations"},
    {"name": "Eva Johnson",   "job_title": "Supply Chain Manager",  "department": "Supply Chain"},
    {"name": "Frank Wilson",  "job_title": "Sales Representative",  "department": "Sales"},
    {"name": "Grace Kim",     "job_title": "Finance Manager",       "department": "Finance"},
    {"name": "Henry Brown",   "job_title": "Warehouse Coordinator", "department": "Operations"},
]
