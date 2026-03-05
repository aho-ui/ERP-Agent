import random


def execute(uid, models, cfg, model, method, args, kwargs=None):
    return models.execute_kw(cfg["db"], uid, cfg["password"], model, method, args, kwargs or {})


def generate_purchase(uid, models, cfg, vendor_ids, product_ids):
    print("Creating purchase orders...")
    for i in range(10):
        vendor_id = random.choice(vendor_ids)
        order_id = execute(uid, models, cfg, "purchase.order", "create", [{
            "partner_id": vendor_id,
        }])

        line_count = random.randint(2, 3)
        for _ in range(line_count):
            product_id = random.choice(product_ids)
            execute(uid, models, cfg, "purchase.order.line", "create", [{
                "order_id": order_id,
                "product_id": product_id,
                "product_qty": random.randint(1, 10),
                "price_unit": round(random.uniform(10.0, 400.0), 2),
            }])

        if i < 6:
            execute(uid, models, cfg, "purchase.order", "button_confirm", [[order_id]])
            print(f"  PO {order_id}: confirmed")
        else:
            print(f"  PO {order_id}: draft")

    print("Purchase order generation complete.")
