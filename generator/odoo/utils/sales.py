import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from utils.data import CUSTOMERS, PRODUCTS

# CUSTOMERS = [
#     {"name": "Acme Corp", "email": "contact@acme.com", "is_company": True, "customer_rank": 1},
#     ...
# ]
# PRODUCTS = [
#     {"name": "Office Chair", "list_price": 299.99, "type": "consu"},
#     ...
# ]


def execute(uid, models, cfg, model, method, args, kwargs=None):
    return models.execute_kw(cfg["db"], uid, cfg["password"], model, method, args, kwargs or {})


def generate_sales(uid, models, cfg):
    print("Creating customers...")
    customer_ids = []
    for c in [c for c in CUSTOMERS if c["odoo"]]:
        cid = execute(uid, models, cfg, "res.partner", "create", [{"name": c["name"], "email": c["email"], "is_company": c["is_company"], "customer_rank": c["customer_rank"]}])
        customer_ids.append(cid)
        print(f"  Created customer: {c['name']} (id={cid})")

    print("Creating products...")
    product_ids = []
    for p in [p for p in PRODUCTS if p["odoo"]]:
        pid = execute(uid, models, cfg, "product.product", "create", [{"name": p["name"], "list_price": p["list_price"], "type": p["type"]}])
        product_ids.append(pid)
        print(f"  Created product: {p['name']} (id={pid})")

    print("Creating sales orders...")
    for i in range(10):
        customer_id = random.choice(customer_ids)
        order_id = execute(uid, models, cfg, "sale.order", "create", [{
            "partner_id": customer_id,
        }])

        line_count = random.randint(2, 3)
        for _ in range(line_count):
            product_id = random.choice(product_ids)
            execute(uid, models, cfg, "sale.order.line", "create", [{
                "order_id": order_id,
                "product_id": product_id,
                "product_uom_qty": random.randint(1, 5),
            }])

        if i < 6:
            execute(uid, models, cfg, "sale.order", "action_confirm", [[order_id]])
            print(f"  Order {order_id}: confirmed")
        else:
            print(f"  Order {order_id}: draft")

    print("Sales generation complete.")
    return product_ids
