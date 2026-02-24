# ============================================================
# ODOO MCP SERVER
# Exposes Odoo actions as tools that nanobot can call
# ============================================================

# --- IMPORTS ---
# mcp: to create the MCP server and define tools
# xmlrpc.client: built-in Python lib to talk to Odoo's XML-RPC API
# json: to format responses

# --- CREDENTIALS ---
# Load from .credentials/odoo.md
# URL, DB name, username, password

# --- CONNECTION ---
# On each tool call:
#   1. Connect to /xmlrpc/2/common → authenticate → get uid
#   2. Connect to /xmlrpc/2/object → use uid to execute model methods

# --- TOOL: get_orders ---
# Input: limit (optional, default 10)
# Action: call purchase.order → search_read
# Fields to return: name, vendor, date, total amount, status
# Output: list of orders as JSON

# --- TOOL: create_purchase_order ---
# Input: partner_id (vendor), product_id, quantity, price_unit
# Action:
#   1. call purchase.order → create → with order_line
#   2. return the new PO id
# Output: created PO id as JSON

# --- MCP SERVER ENTRY POINT ---
# Start the server using stdio (nanobot talks to it via stdin/stdout)
