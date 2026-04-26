def sales_table() -> bytes:
    from agent.utils.table_image import render_table_image
    columns = ["Order", "Customer", "Date", "Salesperson", "Product", "Qty", "Unit Price", "Discount", "Tax", "Subtotal", "Total", "Status", "Payment"]
    rows = [
        ["SO/0041", "Acme Corp",         "2026-01-05", "J. Miller",  "Office Chair Pro",      10, "$299.99", "5%",  "10%", "$2,849.91",  "$3,134.90",  "sale",      "paid"],
        ["SO/0042", "Globex Inc",        "2026-01-12", "S. Chen",    "Standing Desk Elite",    5, "$649.00", "0%",  "10%", "$3,245.00",  "$3,569.50",  "sale",      "paid"],
        ["SO/0043", "Initech Ltd",       "2026-01-19", "J. Miller",  "Monitor 27\" 4K",        8, "$425.00", "8%",  "10%", "$3,128.00",  "$3,440.80",  "sale",      "not_paid"],
        ["SO/0044", "Umbrella Co",       "2026-01-28", "R. Patel",   "Ergonomic Keyboard",    20, "$89.99",  "0%",  "10%", "$1,799.80",  "$1,979.78",  "sale",      "paid"],
        ["SO/0045", "Stark Industries",  "2026-02-03", "S. Chen",    "Server Rack Unit",       2, "$3,200.00","10%","10%", "$5,760.00",  "$6,336.00",  "sale",      "partial"],
        ["SO/0046", "Wayne Enterprises", "2026-02-11", "R. Patel",   "Wireless Headset",      15, "$149.00", "0%",  "10%", "$2,235.00",  "$2,458.50",  "sale",      "paid"],
        ["SO/0047", "Cyberdyne Corp",    "2026-02-18", "J. Miller",  "Laptop Stand",          30, "$59.99",  "5%",  "10%", "$1,709.71",  "$1,880.68",  "draft",     "not_paid"],
        ["SO/0048", "Oscorp Ltd",        "2026-02-25", "S. Chen",    "USB-C Hub 10-port",     25, "$79.99",  "0%",  "10%", "$1,999.75",  "$2,199.73",  "sale",      "paid"],
        ["SO/0049", "Rekall Inc",        "2026-03-04", "R. Patel",   "Conference Webcam HD",  12, "$210.00", "3%",  "10%", "$2,440.80",  "$2,684.88",  "sale",      "not_paid"],
        ["SO/0050", "Weyland Corp",      "2026-03-10", "J. Miller",  "NAS Storage 8TB",        4, "$899.00", "0%",  "10%", "$3,596.00",  "$3,955.60",  "cancelled", "refunded"],
        ["SO/0051", "Acme Corp",         "2026-03-17", "S. Chen",    "Desk Lamp LED",         18, "$44.99",  "10%", "10%", "$728.84",    "$801.72",    "sale",      "paid"],
        ["SO/0052", "Globex Inc",        "2026-03-24", "R. Patel",   "Smart Whiteboard 65\"",  1, "$4,200.00","5%", "10%", "$3,990.00",  "$4,389.00",  "draft",     "not_paid"],
    ]
    return render_table_image(columns, rows)


def invoice_table() -> bytes:
    from agent.utils.table_image import render_table_image
    columns = ["Invoice", "Customer", "Issue Date", "Due Date", "Currency", "Subtotal", "Tax (10%)", "Total", "Paid", "Balance", "State", "Payment State", "Days Overdue"]
    rows = [
        ["INV/0091", "Acme Corp",         "2026-01-06", "2026-02-05", "USD", "$2,849.91",  "$284.99",  "$3,134.90",  "$3,134.90",  "$0.00",      "posted",    "paid",      "-"],
        ["INV/0092", "Globex Inc",        "2026-01-13", "2026-02-12", "USD", "$3,245.00",  "$324.50",  "$3,569.50",  "$3,569.50",  "$0.00",      "posted",    "paid",      "-"],
        ["INV/0093", "Initech Ltd",       "2026-01-20", "2026-02-19", "USD", "$3,128.00",  "$312.80",  "$3,440.80",  "$0.00",      "$3,440.80",  "posted",    "not_paid",  "57"],
        ["INV/0094", "Umbrella Co",       "2026-01-29", "2026-02-28", "USD", "$1,799.80",  "$179.98",  "$1,979.78",  "$1,979.78",  "$0.00",      "posted",    "paid",      "-"],
        ["INV/0095", "Stark Industries",  "2026-02-04", "2026-03-06", "USD", "$5,760.00",  "$576.00",  "$6,336.00",  "$3,000.00",  "$3,336.00",  "posted",    "partial",   "42"],
        ["INV/0096", "Wayne Enterprises", "2026-02-12", "2026-03-14", "USD", "$2,235.00",  "$223.50",  "$2,458.50",  "$2,458.50",  "$0.00",      "posted",    "paid",      "-"],
        ["INV/0097", "Cyberdyne Corp",    "2026-02-19", "2026-03-21", "USD", "$1,709.71",  "$170.97",  "$1,880.68",  "$0.00",      "$1,880.68",  "draft",     "not_paid",  "27"],
        ["INV/0098", "Oscorp Ltd",        "2026-02-26", "2026-03-28", "USD", "$1,999.75",  "$199.98",  "$2,199.73",  "$2,199.73",  "$0.00",      "posted",    "paid",      "-"],
        ["INV/0099", "Rekall Inc",        "2026-03-05", "2026-04-04", "USD", "$2,440.80",  "$244.08",  "$2,684.88",  "$0.00",      "$2,684.88",  "posted",    "not_paid",  "13"],
        ["INV/0100", "Weyland Corp",      "2026-03-11", "2026-04-10", "USD", "$3,596.00",  "$359.60",  "$3,955.60",  "$3,955.60",  "$0.00",      "cancel",    "refunded",  "-"],
        ["INV/0101", "Acme Corp",         "2026-03-18", "2026-04-17", "USD", "$728.84",    "$72.88",   "$801.72",    "$801.72",    "$0.00",      "posted",    "paid",      "-"],
        ["INV/0102", "Globex Inc",        "2026-03-25", "2026-04-24", "USD", "$3,990.00",  "$399.00",  "$4,389.00",  "$0.00",      "$4,389.00",  "draft",     "not_paid",  "-"],
    ]
    return render_table_image(columns, rows)
