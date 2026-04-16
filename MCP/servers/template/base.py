import json
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------
# Set up any credentials or config needed to connect to the ERP.
# Load from environment variables where possible.
#
# Example (Odoo):
#   URL = os.environ.get("ERP_URL")
#   DB  = os.environ.get("ERP_DB")
#
# Example (SQLite):
#   DB_PATH = Path(__file__).resolve().parents[N] / "demo.db"

mcp = FastMCP("<erp_name>")


def connect():
    # Return whatever connection object(s) the ERP requires.
    # Raise an exception if the connection fails so health() can catch it.
    raise NotImplementedError


def health() -> bool:
    # Used by the backend to decide which MCP server to activate.
    # Return True only if the ERP is reachable and responding.
    try:
        connect()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Read tools
# ---------------------------------------------------------------------------
# All read tools share the same signature:
#   limit  — max records to return
#   search — optional name/keyword filter (case-insensitive)
#   id     — optional exact record lookup by primary key
#
# Return value must be json.dumps(list[dict]) so the agent can parse it.

@mcp.tool()
def get_sales_orders(limit: int = 10, search: str = "", id: int = 0) -> str:
    # Fields to include: id, name, partner_id, partner_name, date_order, amount_total, state
    raise NotImplementedError


@mcp.tool()
def get_purchase_orders(limit: int = 10, search: str = "", id: int = 0) -> str:
    # Fields to include: id, name, partner_id, partner_name, date_order, amount_total, state
    raise NotImplementedError


@mcp.tool()
def get_invoices(limit: int = 10, search: str = "", id: int = 0) -> str:
    # Customer invoices only (move_type = out_invoice or equivalent).
    # Fields to include: id, name, partner_id, partner_name, invoice_date, amount_total, state, payment_state
    raise NotImplementedError


@mcp.tool()
def get_vendor_bills(limit: int = 10, search: str = "", id: int = 0) -> str:
    # Vendor bills only (move_type = in_invoice or equivalent).
    # Fields to include: id, name, partner_id, partner_name, invoice_date, amount_total, state, payment_state
    raise NotImplementedError


@mcp.tool()
def get_customers(limit: int = 10, search: str = "", id: int = 0) -> str:
    # Fields to include: id, name, email, phone, customer_rank
    raise NotImplementedError


@mcp.tool()
def get_vendors(limit: int = 10, search: str = "", id: int = 0) -> str:
    # Fields to include: id, name, email, phone, supplier_rank
    raise NotImplementedError


@mcp.tool()
def get_products(limit: int = 10, search: str = "", id: int = 0) -> str:
    # Fields to include: id, name, list_price, standard_price, type, default_code
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Write tools
# ---------------------------------------------------------------------------
# Write tools are called only after the agent has received explicit confirmation.
# Return json.dumps({"<entity>_id": <id>}) on success.

@mcp.tool()
def create_sales_order(partner_id: int, product_id: int, quantity: float) -> str:
    # 1. Validate partner and product exist.
    # 2. Calculate amount from list_price * quantity.
    # 3. Create the order record, return its id.
    raise NotImplementedError


@mcp.tool()
def create_purchase_order(vendor_id: int, product_id: int, quantity: float) -> str:
    # 1. Validate vendor and product exist.
    # 2. Calculate amount from standard_price * quantity.
    # 3. Create and confirm the order, return its id.
    raise NotImplementedError


@mcp.tool()
def create_customer_invoice(partner_id: int, product_id: int, quantity: float, price_unit: float) -> str:
    # 1. Validate customer exists.
    # 2. Create invoice with one line, post it, return its id.
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Dashboard stats
# ---------------------------------------------------------------------------
# Called by the backend on startup to populate the dashboard.
# Return a flat dict of counts/metrics, or None if unavailable.

def dashboard_stats() -> dict | None:
    # Suggested keys (match what the frontend expects):
    #   open_sales_orders, total_customers, total_products,
    #   open_purchase_orders, unpaid_invoices
    try:
        raise NotImplementedError
    except Exception:
        return None


if __name__ == "__main__":
    mcp.run(transport="stdio")
