# Project: Nanobot ERP Agent

## Stack
- Agent framework: nanobot (pip package)
- Backend: Django + DRF
- Frontend: Next.js
- MCP: FastMCP (stdio transport), server at `MCP/servers/odoo.py`
- LLM: OpenAI GPT-4o via LiteLLM
- ERP: Odoo 18 at localhost:8069, DB=odoo_dev_18, user=admin

## Architecture
- `agent/framework/nanobot.py` — AgentLoop singleton (`get_agent_loop()`), DispatchTool registered here
- `agent/framework/agents.py` — pure data templates (name, system_prompt, allowed_tools) for mini-agents
- `MCP/servers/odoo.py` — FastMCP server with 10 tools; tool names prefixed `mcp_odoo_*` when registered
- `MCP/config.py` — SERVERS dict pointing to odoo.py via stdio
- `~/.nanobot/workspace/AGENTS.md` — supervisor instructions (routes all ERP requests via `dispatch`)
- `~/.nanobot/workspace/` — nanobot workspace: memory/, sessions/, skills/, bootstrap .md files

## Supervisor / Mini-Agent Pattern
- Main AgentLoop = supervisor; does NOT call MCP tools directly
- `DispatchTool` in nanobot.py: supervisor calls `dispatch(agent_name, task)`
  - Looks up template from agents.py
  - Filters main ToolRegistry to allowed_tools set
  - Runs isolated provider.chat loop with filtered tools, returns result synchronously
- 5 agents: purchase_agent, sales_agent, invoice_agent, inventory_agent, analytics_agent

## MCP Tools (mcp_odoo_*)
GET: get_sales_orders, get_customers, get_vendors, get_products, get_purchase_orders, get_invoices, get_vendor_bills
CREATE: create_sales_order, create_purchase_order, create_customer_invoice
All GET tools support `limit` and `search` params.

## Data Generator
- `generator/odoo/main.py` — argparse CLI: --sales, --vendors, --purchase, --invoices, --inventory, --hr
- Utils: sales.py, vendors.py, purchase.py, invoices.py, inventory.py, hr.py

## Key Notes
- `customer_rank` not auto-set via XML-RPC; get_customers uses `is_company=True` domain
- Inventory uses `stock.quant` + `action_apply_inventory` (Odoo 16+)
- nanobot's built-in SubagentManager is fire-and-forget via bus — not used for ERP sub-agents
- DispatchTool holds live reference to main ToolRegistry so MCP tools visible after lazy connect
