# ERP Agent (Odoo addon)

An AI-powered conversational interface embedded inside Odoo. Chat with your Odoo data via natural language: read customers, products, invoices; create sales orders, purchase orders, payments. Backed by an in-process [nanobot](https://github.com/HKUDS/nanobot) daemon spawned at addon load.

## Prerequisites

- Odoo 18
- Python 3.10+
- Odoo modules: **Sales** (`sale_management`), **Purchase** (`purchase`), **Invoicing** (`account`). These pull in `product`, `sales_team`, `stock` as deps.

Python packages (see `requirements.txt`): `django`, `uvicorn`, `nanobot`, `litellm`, `loguru`, `dotenv`, `pyyaml`, `aiohttp`, `json_repair`, `corsheaders`.

## Install

1. Drop this folder into your Odoo addons path.
2. Install the Python packages into the Python that runs your Odoo service:
   ```bash
   /path/to/odoo/python.exe -m pip install -r requirements.txt
   ```
   (Windows service installs typically ship their own bundled Python — use that, not the system Python, or Odoo will start but the daemon will fail to import.)
3. Install the three prerequisite modules from Odoo → **Apps**.
4. Install **ERP Agent** from Odoo → **Apps** (search `erp_agent`).

On install:
- New models are created (`erp_agent.conversation`, `erp_agent.message`, `erp_agent.agent`, `erp_agent.profile`, `erp_agent.pending_action`).
- Per-user record rules are registered — each user only sees their own conversations, profiles, and pending actions. Admin (`base.group_system`) sees everything.
- A Django daemon boots inside the Odoo process on port `8001`. MCP subprocesses spawn on first request.

---

## Configure

### Per-user LLM profile

Every user creates their own profile in the chat's **Settings** tab. A profile stores:

| Field | Notes |
|---|---|
| `name` | Display name for the profile |
| `model` | LiteLLM-style model id (`openai/gpt-4o-mini`, `anthropic/claude-3-5-sonnet-20241022`, `groq/…`, `deepseek/…`) |
| `api_key` | Provider API key — masked in the UI, stored in DB (per-user record rule scopes it) |

Active profile is remembered per browser via `localStorage`.

### Custom agents

Admins can define custom sub-agents from **Dashboard → Agents**:

- Name, description, system prompt
- Tool allowlist (subset of the registered MCP tools)

Defaults ship in `backend/agents/templates.yaml` — override by creating a custom agent with the same name.

### MCP servers on/off

Admin toggles in **Dashboard → Health**. Disabling a server hides its tools from the agent registry (and any agent that depended on those tools is filtered out until re-enabled).

---

## Roles

| Action | Non-admin user | Admin |
|---|---|---|
| Chat | ✓ | ✓ |
| Create own profile / agents | ✓ | ✓ |
| Read tools (list customers, products, orders) | ✓ | ✓ |
| Write tools (create sales order, register payment, etc.) | Queued for admin approval | Executed directly |
| See dashboard **Usage** tab | — | ✓ |
| See dashboard **Pending** tab | — | ✓ |
| Rebuild MCP subprocesses | — | ✓ |

---

## Data sources

### Odoo (real ERP)

Tools call back into Odoo via an internal HTTP endpoint (`/erp_agent/internal/execute`), gated by:

1. A short-lived HMAC token signed by the daemon (`backend/gateway.py`) — proves the request came from the addon's own daemon.
2. A per-tool `(model, method)` operation allowlist, auto-derived at startup from each tool's `@needs(...)` decorator declaration.

Every tool call runs as the requesting Odoo user, so Odoo's own ACLs and record rules still apply.

### SQLite (bundled demo)

A demo database ships under `backend/mcp_servers/sqlite.py` — same tool shape as the Odoo backend, no auth, single tenant. Used as a fallback / for demoing without an Odoo install.

---

## MCP tools

| Tool | Kind | Write? |
|---|---|---|
| `get_sales_orders` | read | |
| `get_purchase_orders` | read | |
| `get_invoices` | read | |
| `get_vendor_bills` | read | |
| `get_customers` | read | |
| `get_vendors` | read | |
| `get_products` | read | |
| `dashboard_stats` | read | |
| `create_sales_order` | write | ✓ |
| `create_purchase_order` | write | ✓ |
| `create_customer_invoice` | write | ✓ |
| `create_vendor_bill` | write | ✓ |
| `confirm_sales_order` | write | ✓ |
| `register_payment` | write | ✓ |
| `update_sales_order` | write | ✓ |
| `update_purchase_order` | write | ✓ |
| `update_invoice` | write | ✓ |

Every tool exists in both `odoo` and `sqlite` MCP servers with matching signatures. Write tools return `{id, kind, ...}` uniformly across both backends.

---

## Agents

The top-level LLM sees a single `dispatch(agent_name, task)` tool. Available agents:

| Agent | Description |
|---|---|
| `odoo_agent` | Reads and writes Odoo records via the odoo MCP server. |
| `demo_agent` | Reads and writes the bundled SQLite demo ERP (fallback when Odoo is unavailable). |

Any custom agents you create in the Dashboard appear here too, filtered to whichever MCP servers are healthy.

---

## Approval flow (non-admin write actions)

When a non-admin user's chat triggers a write tool:

1. The daemon intercepts the tool call **before** execution.
2. A row is created in `erp_agent.pending_action` with the tool name + payload.
3. The chat gets a "Waiting for admin approval…" bubble showing the payload.
4. An admin reviews from **Dashboard → Pending** and clicks **Approve** or **Reject**.
5. On approve, the controller re-signs a gateway token as the requesting user and executes the tool. On reject, the row is marked and a message posts back into the conversation.

Admins bypass this entirely — their write tool calls execute inline.

---

## Chat features

- **Conversation search** — ilike over message content, scoped per-user
- **Export as markdown** — download button on each conversation
- **Per-conversation system prompt override** — pin a thread to a specialized instruction ("this thread is for accounting only")
- **Async streaming** — closing the chat mid-response no longer loses data; the daemon task keeps running and the assistant reply persists via the SSE service, visible on next open
- **Live agent thinking** — every dispatch + tool call + result streams to the chat as it happens, collapsible after completion

---

## Dashboard tabs

| Tab | Who | Shows |
|---|---|---|
| **Activity** | Everyone (own data, admin sees all) | Calls per day, top tools, per-agent breakdown, per-call detail with steps + result preview |
| **Health** | Everyone | Daemon uptime, MCP server states (Healthy / DB down / Dead) with real DB probe, uptime chart |
| **Agents** | Everyone (own custom agents, defaults read-only) | List of default + custom agents, tool allowlist editor |
| **Tools** | Everyone | Every registered MCP tool with its schema, param list, call history, last args + result preview |
| **Usage** | Admin | Total cost / tokens / messages over N days, per-user + per-model leaderboards, cost-over-time chart |
| **Pending** | Admin | All pending write actions across all users, with Approve / Reject buttons |

---

## Architecture

```
browser
  │ POST /erp_agent/chat  (Odoo session cookie)
  ▼
controllers/chat.py — assembles bundle {agents, profile, enabled_mcps, uid, is_admin, system_prompt_override}
  │ POST → daemon :8001 (X-API-Key)
  ▼
backend/chat/views.py — set_context() puts bundle on AgentContext ContextVar
  │ acquire top_level_lock → sync_provider(loop) → process_direct()
  ▼
nanobot AgentLoop top-level LLM call (sees only `dispatch`)
  ▼
backend/agents/dispatch.py — DispatchTool / SubAgentRunner
  │ sub-agent LLM uses ctx.profile model + api_key per call
  │ write-tool interception: if not ctx.is_admin, emit pending_action SSE
  ▼
backend/agent_loop.py:wrap_mcp_tools — injects auth_token from ctx.user_id
  │ token = HMAC sign({uid, op, exp}) via backend/gateway.py
  ▼
backend/mcp_servers/odoo.py — stateless; @needs([(model, method), …]) declares ops
  │ tool body calls _exec("model", "method", args, kwargs)
  │ POST → http://localhost:8069/erp_agent/internal/execute
  ▼
controllers/internal.py — verifies token, checks op allowlist
  │ env = request.env(user=uid)   ← Odoo identity switch
  │ if first arg is a list of ids → env[model].browse(ids).method(*rest, **kw)
  │ else → env[model].method(*args, **kw)
  │ recordset results normalized to id/ids before serialization
```

### Trust boundaries

- **browser ↔ Odoo:** session cookie (Odoo's normal auth)
- **Odoo controller ↔ daemon:** in-process shared `API_KEY` (env-set or auto-generated at startup)
- **daemon ↔ MCP ↔ `/internal/execute`:** HMAC gateway token + per-tool `(model, method)` allowlist

---

## Health probe

`curl http://localhost:8069/erp_agent/internal/health` returns `{"status": "UP", "reason": "ok"}` when Odoo + DB are reachable.
