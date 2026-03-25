WRITE_TOOLS = {
    "mcp_odoo_create_sales_order",
    "mcp_odoo_create_purchase_order",
    "mcp_odoo_create_customer_invoice",
    "mcp_sqlite_create_sales_order",
    "mcp_sqlite_create_purchase_order",
    "mcp_sqlite_create_customer_invoice",
}

TOOL_GUARDRAILS: dict[str, dict] = {
    "mcp_odoo_create_sales_order":        {"max_quantity": 1000},
    "mcp_odoo_create_purchase_order":     {"max_quantity": 1000},
    "mcp_odoo_create_customer_invoice":   {"max_quantity": 1000, "max_unit_price": 100_000},
    "mcp_sqlite_create_sales_order":      {"max_quantity": 1000},
    "mcp_sqlite_create_purchase_order":   {"max_quantity": 1000},
    "mcp_sqlite_create_customer_invoice": {"max_quantity": 1000, "max_unit_price": 100_000},
}
