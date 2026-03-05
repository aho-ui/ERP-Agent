import random


def execute(uid, models, cfg, model, method, args, kwargs=None):
    return models.execute_kw(cfg["db"], uid, cfg["password"], model, method, args, kwargs or {})


def generate_invoices(uid, models, cfg):
    print("Creating customer invoices...")
    sale_orders = execute(uid, models, cfg, "sale.order", "search_read",
        [[["state", "=", "sale"]]],
        {"fields": ["partner_id"], "limit": 20},
    )
    seen = set()
    customers = []
    for so in sale_orders:
        pid = so["partner_id"][0]
        if pid not in seen:
            seen.add(pid)
            customers.append({"id": pid, "name": so["partner_id"][1]})
        if len(customers) >= 6:
            break

    products = execute(uid, models, cfg, "product.product", "search_read",
        [[["sale_ok", "=", True]]],
        {"fields": ["id", "name", "list_price"], "limit": 10},
    )
    for customer in customers:
        product = random.choice(products)
        invoice_id = execute(uid, models, cfg, "account.move", "create", [{
            "move_type": "out_invoice",
            "partner_id": customer["id"],
            "invoice_line_ids": [(0, 0, {
                "name": product["name"],
                "quantity": random.randint(1, 5),
                "price_unit": product["list_price"],
            })],
        }])
        execute(uid, models, cfg, "account.move", "action_post", [[invoice_id]])
        print(f"  Customer invoice {invoice_id} for {customer['name']}: posted")

    print("Creating vendor bills...")
    confirmed_pos = execute(uid, models, cfg, "purchase.order", "search_read",
        [[["state", "in", ["purchase", "done"]]]],
        {"fields": ["id", "name", "partner_id"], "limit": 6},
    )
    for po in confirmed_pos:
        bill_id = execute(uid, models, cfg, "account.move", "create", [{
            "move_type": "in_invoice",
            "partner_id": po["partner_id"][0],
            "invoice_origin": po["name"],
            "invoice_line_ids": [(0, 0, {
                "name": f"Bill for {po['name']}",
                "quantity": random.randint(1, 10),
                "price_unit": round(random.uniform(10.0, 300.0), 2),
            })],
        }])
        execute(uid, models, cfg, "account.move", "action_post", [[bill_id]])
        print(f"  Vendor bill {bill_id} for {po['name']}: posted")

    print("Invoice generation complete.")
