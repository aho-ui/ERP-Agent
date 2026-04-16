import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from utils.data import VENDORS

# VENDORS = [
#     {"name": "TechSupply Co", "email": "orders@techsupply.com", "is_company": True, "supplier_rank": 1},
#     ...
# ]


def execute(uid, models, cfg, model, method, args, kwargs=None):
    return models.execute_kw(cfg["db"], uid, cfg["password"], model, method, args, kwargs or {})


def generate_vendors(uid, models, cfg, product_ids):
    print("Creating vendors...")
    vendor_ids = []
    for v in [v for v in VENDORS if v["odoo"]]:
        vid = execute(uid, models, cfg, "res.partner", "create", [{"name": v["name"], "email": v["email"], "is_company": v["is_company"], "supplier_rank": v["supplier_rank"]}])
        vendor_ids.append(vid)
        print(f"  Created vendor: {v['name']} (id={vid})")

    print("Creating vendor pricelists...")
    for product_id in product_ids:
        vendor_id = random.choice(vendor_ids)
        price = round(random.uniform(10.0, 400.0), 2)
        execute(uid, models, cfg, "product.supplierinfo", "create", [{
            "partner_id": vendor_id,
            "product_tmpl_id": execute(uid, models, cfg, "product.product", "read", [[product_id]], {"fields": ["product_tmpl_id"]})[0]["product_tmpl_id"][0],
            "price": price,
            "min_qty": 1,
        }])

    print("Vendor generation complete.")
    return vendor_ids
