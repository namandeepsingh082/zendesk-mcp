# 🎫 Zendesk MCP Server

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-compatible-green.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A **complete** [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server for Zendesk with **60+ tools**.

Connect Claude Desktop directly to your Zendesk instance and control everything — tickets, users, custom fields, macros, triggers, SLAs, Help Center, reporting, and more — just by talking to Claude.

---

## ✨ What You Can Do

Once connected, ask Claude things like:

> *"Show me all open tickets assigned to me"*
> *"Get ticket #8821 and show me all its custom fields with readable labels"*
> *"Search for billing tickets created in the last 7 days"*
> *"Create a ticket for John, set priority to urgent, Account Tier to Enterprise"*
> *"Apply the 'Escalate to L2' macro to ticket #4400"*
> *"Show me satisfaction ratings for this month broken down by score"*
> *"What triggers do we have that auto-assign tickets? Show me the conditions"*
> *"List all users in the Support group and their assigned tickets"*

No dashboards. No clicking. Just Claude.

---

## ⚡ Quickstart

### Option A — Using `uvx` (Recommended, no install needed)

```bash
uvx zendesk-mcp
```

### Option B — Using `pip`

```bash
pip install zendesk-mcp
zendesk-mcp
```

### Option C — Run from source

```bash
git clone https://github.com/Sajiiidddd/zendesk-mcp
cd zendesk-mcp
python3 -m venv .venv
.venv/bin/pip install -e .
.venv/bin/python -m zendesk_mcp.server
```

---

## 🔧 Claude Desktop Setup

Add this to your `claude_desktop_config.json`:

**Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "zendesk": {
      "command": "uvx",
      "args": ["zendesk-mcp"],
      "env": {
        "ZENDESK_SUBDOMAIN": "yourcompany",
        "ZENDESK_EMAIL": "you@yourcompany.com",
        "ZENDESK_API_TOKEN": "your_api_token_here",
        "TRANSPORT": "stdio"
      }
    }
  }
}
```

> Replace `yourcompany`, `you@yourcompany.com`, and `your_api_token_here` with your real values.

Then **fully quit and reopen Claude Desktop** (`Cmd+Q` on Mac).

> ✅ **This is a one-time setup.** Your credentials are saved in the config file — Claude Desktop loads them automatically on every launch. You never need to repeat these steps.

---

## 🔑 Getting Your Zendesk API Token

1. Log into Zendesk as **Admin**
2. Go to **Admin Center → Apps & Integrations → APIs → Zendesk API**
3. Click the **Settings** tab → enable **Token Access**
4. Click **Add API token** → give it a label → **copy the token** *(shown only once!)*

---

## 🗂 Project Structure

```
zendesk-mcp/
├── src/
│   └── zendesk_mcp/
│       ├── __init__.py
│       └── server.py       # All 60+ tools live here
├── .env.example            # Credentials template
├── pyproject.toml          # Package config + dependencies
├── LICENSE
└── README.md
```

---

## 🛠 Tools Reference

### 🎫 Tickets (11 tools)
| Tool | Description |
|---|---|
| `list_tickets` | List with pagination, filters, sorting |
| `get_ticket` | Single ticket by ID |
| `get_ticket_custom_fields` | Ticket + all custom fields with human-readable labels |
| `create_ticket` | New ticket with any fields including custom fields |
| `update_ticket` | Update any field, add public/private comments |
| `delete_ticket` | Trash a ticket |
| `bulk_update_tickets` | Update up to 100 tickets at once |
| `merge_tickets` | Merge tickets into one |
| `search_tickets` | Full Zendesk query syntax |
| `list_ticket_comments` | All comments on a ticket |
| `add_ticket_comment` | Add public or private comment |

### 🏷️ Custom Fields (6 tools)
| Tool | Description |
|---|---|
| `list_ticket_fields` | All fields with IDs, types, labels, dropdown options |
| `get_ticket_field` | Single field details |
| `create_ticket_field` | Create a new custom field |
| `update_ticket_field` | Edit field options and labels |
| `list_user_fields` | All custom user fields |
| `list_organization_fields` | All custom org fields |

### 👤 Users (7 tools)
| Tool | Description |
|---|---|
| `list_users` | List all users, filter by role |
| `get_user` | User by ID including custom fields |
| `search_users` | By name, email, or external ID |
| `create_user` | Create end-user, agent, or admin |
| `update_user` | Update details and custom fields |
| `delete_user` | Delete a user |
| `get_user_tickets` | Requested / assigned / CC'd tickets |

### 🏢 Organizations (6 tools)
| Tool | Description |
|---|---|
| `list_organizations` | List all orgs |
| `get_organization` | Org by ID |
| `create_organization` | Create a new org |
| `update_organization` | Update org + custom fields |
| `get_organization_tickets` | All tickets for an org |
| `list_organization_fields` | All custom org fields |

### 👥 Groups (4 tools)
`list_groups` · `get_group` · `create_group` · `list_group_memberships`

### ⚡ Macros, Triggers & Automations (10 tools)
`list_macros` · `get_macro` · `apply_macro` · `create_macro` · `list_triggers` · `get_trigger` · `create_trigger` · `update_trigger` · `list_automations` · `get_automation`

### 👁️ Views & SLAs (5 tools)
`list_views` · `get_view` · `execute_view` · `list_sla_policies` · `get_sla_policy`

### 📊 Metrics & Satisfaction (4 tools)
`get_ticket_metrics` · `list_ticket_metrics` · `list_satisfaction_ratings` · `get_satisfaction_rating`

### 🏷 Tags (4 tools)
`list_tags` · `get_ticket_tags` · `set_ticket_tags` · `add_ticket_tags`

### 📎 Attachments (1 tool)
`list_ticket_attachments`

### 📚 Help Center (6 tools)
`list_articles` · `get_article` · `create_article` · `search_help_center` · `list_sections` · `list_categories`

### 🔗 Webhooks & Account (5 tools)
`list_webhooks` · `create_webhook` · `get_account_settings` · `list_locales` · `list_schedules`

### 🔍 Universal Search (1 tool)
`search` — search across all Zendesk objects

### ⚡ Power / Escape Hatch (1 tool)
| Tool | Description |
|---|---|
| `raw_api_call` | **Call ANY Zendesk API endpoint directly** — nothing is off limits |

---

## 💡 How Custom Field Decoding Works

Zendesk stores custom field values as raw machine values like `"account_tier__enterprise"`.

The `get_ticket_custom_fields` tool automatically fetches your field schema and joins it with the ticket data to produce clean, human-readable output:

```json
{
  "field_label": "Account Tier",
  "field_type": "tagger",
  "value": "account_tier__enterprise",
  "value_label": "Enterprise"
}
```

You never need to look up field IDs manually.

---

## 🔧 Troubleshooting

| Problem | Fix |
|---|---|
| `Missing required environment variables` | Add `ZENDESK_SUBDOMAIN`, `ZENDESK_EMAIL`, `ZENDESK_API_TOKEN` to the `env` block in your config |
| `401 Unauthorized` | Wrong API token or email — double-check credentials |
| `Server disconnected` in Claude Desktop | Fully quit Claude (`Cmd+Q`) and reopen — closing the window isn't enough |
| `ModuleNotFoundError` | Run `pip install zendesk-mcp` or use `uvx zendesk-mcp` |
| Tools not appearing | Check logs: **Settings → Developer → Open MCP Log File** |

### Viewing Logs (Mac)
```bash
tail -f ~/Library/Logs/Claude/mcp-server-zendesk.log
```

---

## 🧩 Adding New Tools

1. Add a `types.Tool(...)` entry to the `TOOLS` list in `server.py`
2. Add a handler in the `call_tool()` function
3. Restart Claude Desktop

For one-off calls, use `raw_api_call` with any path from the [Zendesk API docs](https://developer.zendesk.com/api-reference/).

---

## 🔒 Security

- **Never commit your `.env` file** or API token to Git
- The `.env.example` file is safe to commit (no real values)
- Your API token has full admin-level Zendesk access — treat it like a password
- Consider creating a dedicated **"MCP Bot" agent** in Zendesk for a clean audit trail

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `mcp[cli]` | MCP protocol SDK |
| `httpx` | Async HTTP client for Zendesk API calls |
| `python-dotenv` | Load credentials from `.env` |
| `starlette` | ASGI framework (SSE transport) |
| `uvicorn` | ASGI server (SSE transport) |

---

## 🤝 Contributing

PRs welcome! If you add new tools or fix bugs, please open a pull request.
If you find this repo helpful, drop a ⭐

---

## 📄 License

MIT — see [LICENSE](LICENSE)
