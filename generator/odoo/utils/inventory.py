import random


def execute(uid, models, cfg, model, method, args, kwargs=None):
    return models.execute_kw(cfg["db"], uid, cfg["password"], model, method, args, kwargs or {})


def generate_inventory(uid, models, cfg, product_ids):
    print("Setting stock quantities...")
    locations = execute(uid, models, cfg, "stock.location", "search_read",
        [[["usage", "=", "internal"], ["complete_name", "ilike", "WH/Stock"]]],
        {"fields": ["id", "complete_name"], "limit": 1},
    )
    if not locations:
        print("  No internal stock location found, skipping.")
        return
    location_id = locations[0]["id"]

    for product_id in product_ids:
        qty = random.randint(20, 200)
        quant_ids = execute(uid, models, cfg, "stock.quant", "search",
            [[["product_id", "=", product_id], ["location_id", "=", location_id]]],
        )
        if quant_ids:
            execute(uid, models, cfg, "stock.quant", "write",
                [quant_ids, {"inventory_quantity": qty}],
            )
            execute(uid, models, cfg, "stock.quant", "action_apply_inventory", [quant_ids])
        else:
            quant_id = execute(uid, models, cfg, "stock.quant", "create", [{
                "product_id": product_id,
                "location_id": location_id,
                "inventory_quantity": qty,
            }])
            execute(uid, models, cfg, "stock.quant", "action_apply_inventory", [[quant_id]])
        print(f"  Product {product_id}: stock set to {qty}")

    print("Creating reorder rules...")
    warehouse = execute(uid, models, cfg, "stock.warehouse", "search_read",
        [[]],
        {"fields": ["id", "name", "lot_stock_id"], "limit": 1},
    )
    if not warehouse:
        print("  No warehouse found, skipping reorder rules.")
        return
    wh = warehouse[0]

    for product_id in product_ids:
        existing = execute(uid, models, cfg, "stock.warehouse.orderpoint", "search",
            [[["product_id", "=", product_id], ["warehouse_id", "=", wh["id"]]]],
        )
        if existing:
            print(f"  Reorder rule for product {product_id} already exists, skipping.")
            continue
        min_qty = random.randint(5, 20)
        max_qty = min_qty + random.randint(30, 80)
        execute(uid, models, cfg, "stock.warehouse.orderpoint", "create", [{
            "product_id": product_id,
            "warehouse_id": wh["id"],
            "location_id": wh["lot_stock_id"][0],
            "product_min_qty": min_qty,
            "product_max_qty": max_qty,
            "qty_multiple": 1,
        }])
        print(f"  Reorder rule for product {product_id}: min={min_qty}, max={max_qty}")

    print("Inventory generation complete.")
