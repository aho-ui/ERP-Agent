# ERP Agent

An AI-powered ERP agent interface built on [nanobot](https://github.com/HKUDS/nanobot). Query and manage ERP data through natural language.

## Running

### Docker (recommended)

Fill in your `OPENAI_API_KEY` in `docker-compose.run.yml`, then:

```bash
docker compose -f docker-compose.run.yml up
```

Frontend: http://localhost:3000 — Backend: http://localhost:8000

---

### Manual

**Backend**
```bash
cp .env.example .env  # fill in your values
pip install -r requirements.txt
python manage.py migrate
uvicorn backend.asgi:application --host 0.0.0.0 --port 8000 --reload
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

---

## Data Sources

### Demo ERP (default)

A built-in SQLite ERP is available out of the box with no configuration. Sample data is populated automatically on startup.

### Odoo

Odoo is supported and provides the same agent and tool capabilities as the demo ERP. Set the Odoo connection variables in `.env`, then populate with sample data if needed:

```bash
python generator/odoo/main.py
```

If Odoo is not configured, the system falls back to the demo ERP automatically.

---

## MCP Tools

Both data sources expose the same set of tools via MCP servers (`MCP/servers/`).

| Tool | Description |
|---|---|
| `get_sales_orders` | Fetch sales orders with optional search and filters |
| `get_purchase_orders` | Fetch purchase orders |
| `get_invoices` | Fetch customer invoices |
| `get_vendor_bills` | Fetch vendor bills |
| `get_customers` | Fetch customer records |
| `get_vendors` | Fetch vendor records |
| `get_products` | Fetch product catalog |
| `create_sales_order` | Create a new sales order |
| `create_purchase_order` | Create a new purchase order |
| `create_customer_invoice` | Create a new customer invoice |

---

## Agents

The system routes your message to the appropriate sub-agent based on intent.

| Agent | Description |
|---|---|
| `sales_agent` | Query and create sales orders, look up customers |
| `purchase_agent` | Query and create purchase orders, look up vendors |
| `invoice_agent` | View customer invoices and vendor bills, create invoices |
| `inventory_agent` | Browse product catalog and inventory |
| `analytics_agent` | Cross-functional reporting and data analysis with chart support |

Write operations (create, update) require confirmation before execution.

---

## Platform Bots

The agent can be deployed as a bot on external platforms. Bots are managed from the Bots page in the UI.

### Discord

Create a bot at [discord.com/developers](https://discord.com/developers/applications).

Required bot permissions:
- `Send Messages`
- `Read Message History`
- `Attach Files`

Enable **Message Content Intent** under Bot → Privileged Gateway Intents.

Token: the bot token from the Bot page.

### Slack

Create an app at [api.slack.com/apps](https://api.slack.com/apps). Enable **Socket Mode**.

Required bot token scopes (OAuth & Permissions):
- `chat:write`
- `files:write`
- `channels:history`
- `im:history`

Required app-level token scope (Basic Information → App-Level Tokens):
- `connections:write`

Subscribe to bot events (Event Subscriptions): `message.channels`, `message.im`

Tokens: Bot Token (`xoxb-...`) and App Token (`xapp-...`).

### Telegram

Create a bot via [@BotFather](https://t.me/BotFather) on Telegram. No extra permissions needed.

Token: the token provided by BotFather.

### WhatsApp

WhatsApp is supported via [Twilio](https://www.twilio.com). Set up a Twilio account and enable the WhatsApp sandbox.

When the bot is activated, a webhook URL is generated and displayed in the UI. Paste it into the Twilio sandbox webhook configuration. Requires `NGROK_AUTHTOKEN` in `.env`.

Credentials required: Account SID, Auth Token, and the Twilio WhatsApp sender number.
