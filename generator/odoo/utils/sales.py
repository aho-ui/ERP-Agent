import random

CUSTOMERS = [
    {"name": "Acme Corp", "email": "contact@acme.com", "is_company": True, "customer_rank": 1},
    {"name": "Globex Industries", "email": "info@globex.com", "is_company": True, "customer_rank": 1},
    {"name": "Initech Solutions", "email": "hello@initech.com", "is_company": True, "customer_rank": 1},
    {"name": "Umbrella Ltd", "email": "sales@umbrella.com", "is_company": True, "customer_rank": 1},
    {"name": "Stark Enterprises", "email": "info@stark.com", "is_company": True, "customer_rank": 1},
]

PRODUCTS = [
    {"name": "Office Chair", "list_price": 299.99, "type": "consu"},
    {"name": "Standing Desk", "list_price": 599.99, "type": "consu"},
    {"name": "Laptop Stand", "list_price": 49.99, "type": "consu"},
    {"name": "Wireless Mouse", "list_price": 39.99, "type": "consu"},
    {"name": "Mechanical Keyboard", "list_price": 129.99, "type": "consu"},
    {"name": "Monitor 27\"", "list_price": 449.99, "type": "consu"},
    {"name": "USB Hub", "list_price": 29.99, "type": "consu"},
    {"name": "Webcam HD", "list_price": 89.99, "type": "consu"},
    {"name": "IT Support", "list_price": 150.00, "type": "service"},
    {"name": "Consulting Hour", "list_price": 200.00, "type": "service"},
]


def execute(uid, models, cfg, model, method, args, kwargs=None):
    return models.execute_kw(cfg["db"], uid, cfg["password"], model, method, args, kwargs or {})


def generate_sales(uid, models, cfg):
    print("Creating customers...")
    customer_ids = []
    for c in CUSTOMERS:
        cid = execute(uid, models, cfg, "res.partner", "create", [c])
        customer_ids.append(cid)
        print(f"  Created customer: {c['name']} (id={cid})")

    print("Creating products...")
    product_ids = []
    for p in PRODUCTS:
        pid = execute(uid, models, cfg, "product.product", "create", [p])
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
