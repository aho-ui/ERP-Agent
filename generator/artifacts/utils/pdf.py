def purchase_order() -> bytes:
    from agent.utils.documents.po import generate_po_pdf
    data = {
        "po_number": "PO/0087",
        "date": "2026-04-17",
        "vendor": {
            "name": "Acme Supplies Ltd",
            "address": "14 Industrial Park, Suite 300\nDallas, TX 75201\nUnited States",
        },
        "lines": [
            {"product": "Office Chair Pro — Ergonomic Mesh",     "qty": 20,  "unit_price": 299.99,  "total": 5999.80},
            {"product": "Standing Desk Elite — 72\"",             "qty": 10,  "unit_price": 649.00,  "total": 6490.00},
            {"product": "Monitor 27\" 4K IPS — Anti-Glare",      "qty": 15,  "unit_price": 425.00,  "total": 6375.00},
            {"product": "Ergonomic Keyboard — Mechanical TKL",   "qty": 25,  "unit_price": 89.99,   "total": 2249.75},
            {"product": "Wireless Headset — Noise Cancelling",   "qty": 20,  "unit_price": 149.00,  "total": 2980.00},
            {"product": "Laptop Stand — Adjustable Aluminium",   "qty": 30,  "unit_price": 59.99,   "total": 1799.70},
            {"product": "USB-C Hub 10-port — 100W PD",           "qty": 25,  "unit_price": 79.99,   "total": 1999.75},
            {"product": "Conference Webcam HD — 4K Auto-Focus",  "qty": 8,   "unit_price": 210.00,  "total": 1680.00},
            {"product": "Desk Lamp LED — Wireless Charge Base",  "qty": 20,  "unit_price": 44.99,   "total": 899.80},
            {"product": "Cable Management Kit — 50pc",           "qty": 15,  "unit_price": 24.99,   "total": 374.85},
        ],
        "subtotal": 30848.65,
        "tax": 3084.87,
        "total": 33933.52,
        "notes": (
            "Delivery required by 2026-05-01. All items must be individually packaged and labeled "
            "with SKU and PO reference. Partial shipments not accepted. Please confirm availability "
            "within 3 business days. Payment terms: NET 30."
        ),
    }
    return generate_po_pdf(data)
