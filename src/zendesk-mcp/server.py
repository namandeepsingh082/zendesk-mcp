"""
Zendesk MCP Server - Full Power Edition
Supports every Zendesk API endpoint + dynamic custom fields
Auth: API Token + Email
Transport: stdio — connect via npx mcp-remote for Claude.ai
"""

import asyncio
import json
import os
import base64
from typing import Any
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from dotenv import load_dotenv
from mcp import types

# Load .env if present
load_dotenv()

# ── Auth & base URL ──────────────────────────────────────────────────────────
ZENDESK_SUBDOMAIN = os.environ["ZENDESK_SUBDOMAIN"]   # e.g. "yourcompany"
ZENDESK_EMAIL     = os.environ["ZENDESK_EMAIL"]        # e.g. "you@company.com"
ZENDESK_API_TOKEN = os.environ["ZENDESK_API_TOKEN"]    # from Admin > API

BASE_URL = f"https://{ZENDESK_SUBDOMAIN}.zendesk.com/api/v2"

def _auth_header() -> dict:
    token = base64.b64encode(
        f"{ZENDESK_EMAIL}/token:{ZENDESK_API_TOKEN}".encode()
    ).decode()
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
    }

async def zd(
    method: str,
    path: str,
    params: dict | None = None,
    body: dict | None = None,
) -> Any:
    """Core Zendesk HTTP client — every tool routes through here."""
    url = BASE_URL + path if path.startswith("/") else path
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.request(
            method.upper(),
            url,
            headers=_auth_header(),
            params=params,
            json=body,
        )
        r.raise_for_status()
        return r.json() if r.content else {"status": "ok", "code": r.status_code}

def ok(data: Any) -> list[types.TextContent]:
    return [types.TextContent(type="text", text=json.dumps(data, indent=2))]

# ── Server init ──────────────────────────────────────────────────────────────
app = Server("zendesk-mcp")

# ═══════════════════════════════════════════════════════════════════════════
#  TOOL REGISTRY
# ═══════════════════════════════════════════════════════════════════════════
TOOLS: list[types.Tool] = [

    # ── TICKETS ─────────────────────────────────────────────────────────────
    types.Tool(
        name="list_tickets",
        description="List tickets. Supports pagination, sorting and filtering by status/assignee/requester.",
        inputSchema={
            "type": "object",
            "properties": {
                "page":       {"type": "integer", "description": "Page number"},
                "per_page":   {"type": "integer", "description": "Results per page (max 100)"},
                "sort_by":    {"type": "string",  "description": "Field to sort by"},
                "sort_order": {"type": "string",  "enum": ["asc", "desc"]},
                "status":     {"type": "string",  "description": "Filter by status"},
            },
        },
    ),
    types.Tool(
        name="get_ticket",
        description="Get a single ticket by ID, including all custom fields.",
        inputSchema={
            "type": "object",
            "required": ["ticket_id"],
            "properties": {
                "ticket_id": {"type": "integer", "description": "Zendesk ticket ID"},
            },
        },
    ),
    types.Tool(
        name="get_ticket_custom_fields",
        description="Get a ticket and decode its custom fields with human-readable labels by joining with your field schema.",
        inputSchema={
            "type": "object",
            "required": ["ticket_id"],
            "properties": {
                "ticket_id": {"type": "integer"},
            },
        },
    ),
    types.Tool(
        name="create_ticket",
        description="Create a new ticket with any fields including custom fields.",
        inputSchema={
            "type": "object",
            "required": ["subject"],
            "properties": {
                "subject":       {"type": "string"},
                "comment_body":  {"type": "string"},
                "requester_id":  {"type": "integer"},
                "assignee_id":   {"type": "integer"},
                "group_id":      {"type": "integer"},
                "priority":      {"type": "string", "enum": ["urgent","high","normal","low"]},
                "status":        {"type": "string", "enum": ["new","open","pending","hold","solved","closed"]},
                "tags":          {"type": "array", "items": {"type": "string"}},
                "custom_fields": {
                    "type": "array",
                    "description": "Array of {id, value} objects for custom fields",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id":    {"type": "integer"},
                            "value": {},
                        },
                    },
                },
                "type":          {"type": "string", "enum": ["problem","incident","question","task"]},
            },
        },
    ),
    types.Tool(
        name="update_ticket",
        description="Update any field on an existing ticket including custom fields.",
        inputSchema={
            "type": "object",
            "required": ["ticket_id"],
            "properties": {
                "ticket_id":     {"type": "integer"},
                "subject":       {"type": "string"},
                "status":        {"type": "string", "enum": ["new","open","pending","hold","solved","closed"]},
                "priority":      {"type": "string", "enum": ["urgent","high","normal","low"]},
                "assignee_id":   {"type": "integer"},
                "group_id":      {"type": "integer"},
                "tags":          {"type": "array", "items": {"type": "string"}},
                "comment_body":  {"type": "string", "description": "Add a comment"},
                "comment_public":{"type": "boolean", "default": True},
                "custom_fields": {
                    "type": "array",
                    "items": {"type": "object", "properties": {"id": {"type": "integer"}, "value": {}}},
                },
            },
        },
    ),
    types.Tool(
        name="delete_ticket",
        description="Delete (trash) a ticket by ID.",
        inputSchema={
            "type": "object",
            "required": ["ticket_id"],
            "properties": {
                "ticket_id": {"type": "integer"},
            },
        },
    ),
    types.Tool(
        name="bulk_update_tickets",
        description="Update multiple tickets at once (up to 100).",
        inputSchema={
            "type": "object",
            "required": ["ticket_ids", "update"],
            "properties": {
                "ticket_ids": {"type": "array", "items": {"type": "integer"}},
                "update": {"type": "object", "description": "Fields to update on all tickets"},
            },
        },
    ),
    types.Tool(
        name="merge_tickets",
        description="Merge one or more tickets into a target ticket.",
        inputSchema={
            "type": "object",
            "required": ["target_ticket_id", "source_ticket_ids"],
            "properties": {
                "target_ticket_id":  {"type": "integer"},
                "source_ticket_ids": {"type": "array", "items": {"type": "integer"}},
                "target_comment":    {"type": "string"},
                "source_comment":    {"type": "string"},
            },
        },
    ),
    types.Tool(
        name="search_tickets",
        description="Search tickets using Zendesk query syntax e.g. 'status:open type:ticket assignee:me'",
        inputSchema={
            "type": "object",
            "required": ["query"],
            "properties": {
                "query":    {"type": "string"},
                "page":     {"type": "integer"},
                "per_page": {"type": "integer"},
                "sort_by":  {"type": "string"},
                "sort_order": {"type": "string", "enum": ["asc","desc"]},
            },
        },
    ),
    types.Tool(
        name="list_ticket_comments",
        description="List all comments on a ticket.",
        inputSchema={
            "type": "object",
            "required": ["ticket_id"],
            "properties": {
                "ticket_id": {"type": "integer"},
            },
        },
    ),
    types.Tool(
        name="add_ticket_comment",
        description="Add a public or private comment to a ticket.",
        inputSchema={
            "type": "object",
            "required": ["ticket_id", "body"],
            "properties": {
                "ticket_id": {"type": "integer"},
                "body":      {"type": "string"},
                "public":    {"type": "boolean", "default": True},
                "author_id": {"type": "integer"},
            },
        },
    ),

    # ── TICKET FIELDS / CUSTOM FIELDS ────────────────────────────────────────
    types.Tool(
        name="list_ticket_fields",
        description="List ALL ticket fields including every custom field with its ID, type, label and options.",
        inputSchema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="get_ticket_field",
        description="Get details of a specific ticket field by ID.",
        inputSchema={
            "type": "object",
            "required": ["field_id"],
            "properties": {"field_id": {"type": "integer"}},
        },
    ),
    types.Tool(
        name="create_ticket_field",
        description="Create a new custom ticket field.",
        inputSchema={
            "type": "object",
            "required": ["type", "title"],
            "properties": {
                "type":  {"type": "string", "enum": ["text","textarea","checkbox","date","integer","decimal","regexp","partialcreditcard","multiselect","tagger","lookup"]},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "required_in_portal": {"type": "boolean"},
                "custom_field_options": {
                    "type": "array",
                    "items": {"type": "object", "properties": {"name": {"type": "string"}, "value": {"type": "string"}}},
                },
            },
        },
    ),
    types.Tool(
        name="update_ticket_field",
        description="Update a ticket field by ID.",
        inputSchema={
            "type": "object",
            "required": ["field_id"],
            "properties": {
                "field_id": {"type": "integer"},
                "title":    {"type": "string"},
                "description": {"type": "string"},
                "custom_field_options": {"type": "array"},
            },
        },
    ),

    # ── USERS ────────────────────────────────────────────────────────────────
    types.Tool(
        name="list_users",
        description="List all users with optional role filter.",
        inputSchema={
            "type": "object",
            "properties": {
                "role":     {"type": "string", "enum": ["end-user","agent","admin"]},
                "page":     {"type": "integer"},
                "per_page": {"type": "integer"},
            },
        },
    ),
    types.Tool(
        name="get_user",
        description="Get a user by ID including custom user fields.",
        inputSchema={
            "type": "object",
            "required": ["user_id"],
            "properties": {"user_id": {"type": "integer"}},
        },
    ),
    types.Tool(
        name="search_users",
        description="Search users by name, email or external_id.",
        inputSchema={
            "type": "object",
            "required": ["query"],
            "properties": {"query": {"type": "string"}},
        },
    ),
    types.Tool(
        name="create_user",
        description="Create a new user (end-user, agent or admin).",
        inputSchema={
            "type": "object",
            "required": ["name", "email"],
            "properties": {
                "name":        {"type": "string"},
                "email":       {"type": "string"},
                "role":        {"type": "string", "enum": ["end-user","agent","admin"]},
                "phone":       {"type": "string"},
                "organization_id": {"type": "integer"},
                "user_fields": {"type": "object", "description": "Custom user fields as key-value pairs"},
            },
        },
    ),
    types.Tool(
        name="update_user",
        description="Update a user by ID.",
        inputSchema={
            "type": "object",
            "required": ["user_id"],
            "properties": {
                "user_id":     {"type": "integer"},
                "name":        {"type": "string"},
                "email":       {"type": "string"},
                "role":        {"type": "string"},
                "phone":       {"type": "string"},
                "user_fields": {"type": "object"},
            },
        },
    ),
    types.Tool(
        name="delete_user",
        description="Delete a user by ID.",
        inputSchema={
            "type": "object",
            "required": ["user_id"],
            "properties": {"user_id": {"type": "integer"}},
        },
    ),
    types.Tool(
        name="get_user_tickets",
        description="Get tickets requested by or assigned to a user.",
        inputSchema={
            "type": "object",
            "required": ["user_id", "type"],
            "properties": {
                "user_id": {"type": "integer"},
                "type":    {"type": "string", "enum": ["requested","ccd","assigned"]},
            },
        },
    ),

    # ── USER FIELDS ──────────────────────────────────────────────────────────
    types.Tool(
        name="list_user_fields",
        description="List all custom user fields.",
        inputSchema={"type": "object", "properties": {}},
    ),

    # ── ORGANIZATIONS ────────────────────────────────────────────────────────
    types.Tool(
        name="list_organizations",
        description="List all organizations.",
        inputSchema={
            "type": "object",
            "properties": {
                "page":     {"type": "integer"},
                "per_page": {"type": "integer"},
            },
        },
    ),
    types.Tool(
        name="get_organization",
        description="Get an organization by ID.",
        inputSchema={
            "type": "object",
            "required": ["org_id"],
            "properties": {"org_id": {"type": "integer"}},
        },
    ),
    types.Tool(
        name="create_organization",
        description="Create a new organization.",
        inputSchema={
            "type": "object",
            "required": ["name"],
            "properties": {
                "name":              {"type": "string"},
                "domain_names":      {"type": "array", "items": {"type": "string"}},
                "organization_fields": {"type": "object"},
            },
        },
    ),
    types.Tool(
        name="update_organization",
        description="Update an organization.",
        inputSchema={
            "type": "object",
            "required": ["org_id"],
            "properties": {
                "org_id": {"type": "integer"},
                "name":   {"type": "string"},
                "organization_fields": {"type": "object"},
            },
        },
    ),
    types.Tool(
        name="get_organization_tickets",
        description="List all tickets belonging to an organization.",
        inputSchema={
            "type": "object",
            "required": ["org_id"],
            "properties": {"org_id": {"type": "integer"}},
        },
    ),
    types.Tool(
        name="list_organization_fields",
        description="List all custom organization fields.",
        inputSchema={"type": "object", "properties": {}},
    ),

    # ── GROUPS ───────────────────────────────────────────────────────────────
    types.Tool(
        name="list_groups",
        description="List all agent groups.",
        inputSchema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="get_group",
        description="Get a group by ID.",
        inputSchema={
            "type": "object",
            "required": ["group_id"],
            "properties": {"group_id": {"type": "integer"}},
        },
    ),
    types.Tool(
        name="create_group",
        description="Create a new group.",
        inputSchema={
            "type": "object",
            "required": ["name"],
            "properties": {"name": {"type": "string"}, "description": {"type": "string"}},
        },
    ),
    types.Tool(
        name="list_group_memberships",
        description="List all agent memberships in a group.",
        inputSchema={
            "type": "object",
            "required": ["group_id"],
            "properties": {"group_id": {"type": "integer"}},
        },
    ),

    # ── MACROS ───────────────────────────────────────────────────────────────
    types.Tool(
        name="list_macros",
        description="List all macros.",
        inputSchema={
            "type": "object",
            "properties": {
                "active": {"type": "boolean"},
                "page":   {"type": "integer"},
            },
        },
    ),
    types.Tool(
        name="get_macro",
        description="Get a macro by ID.",
        inputSchema={
            "type": "object",
            "required": ["macro_id"],
            "properties": {"macro_id": {"type": "integer"}},
        },
    ),
    types.Tool(
        name="apply_macro",
        description="Apply a macro to a ticket.",
        inputSchema={
            "type": "object",
            "required": ["ticket_id", "macro_id"],
            "properties": {
                "ticket_id": {"type": "integer"},
                "macro_id":  {"type": "integer"},
            },
        },
    ),
    types.Tool(
        name="create_macro",
        description="Create a new macro.",
        inputSchema={
            "type": "object",
            "required": ["title", "actions"],
            "properties": {
                "title":   {"type": "string"},
                "active":  {"type": "boolean"},
                "actions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "field": {"type": "string"},
                            "value": {},
                        },
                    },
                },
            },
        },
    ),

    # ── TRIGGERS ─────────────────────────────────────────────────────────────
    types.Tool(
        name="list_triggers",
        description="List all triggers.",
        inputSchema={"type": "object", "properties": {"active": {"type": "boolean"}}},
    ),
    types.Tool(
        name="get_trigger",
        description="Get a trigger by ID.",
        inputSchema={
            "type": "object",
            "required": ["trigger_id"],
            "properties": {"trigger_id": {"type": "integer"}},
        },
    ),
    types.Tool(
        name="create_trigger",
        description="Create a new trigger.",
        inputSchema={
            "type": "object",
            "required": ["title", "conditions", "actions"],
            "properties": {
                "title":      {"type": "string"},
                "conditions": {"type": "object"},
                "actions":    {"type": "array"},
                "active":     {"type": "boolean"},
            },
        },
    ),
    types.Tool(
        name="update_trigger",
        description="Update a trigger by ID.",
        inputSchema={
            "type": "object",
            "required": ["trigger_id"],
            "properties": {
                "trigger_id": {"type": "integer"},
                "title":      {"type": "string"},
                "conditions": {"type": "object"},
                "actions":    {"type": "array"},
                "active":     {"type": "boolean"},
            },
        },
    ),

    # ── AUTOMATIONS ──────────────────────────────────────────────────────────
    types.Tool(
        name="list_automations",
        description="List all automations.",
        inputSchema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="get_automation",
        description="Get an automation by ID.",
        inputSchema={
            "type": "object",
            "required": ["automation_id"],
            "properties": {"automation_id": {"type": "integer"}},
        },
    ),

    # ── VIEWS ────────────────────────────────────────────────────────────────
    types.Tool(
        name="list_views",
        description="List all views.",
        inputSchema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="get_view",
        description="Get a view by ID.",
        inputSchema={
            "type": "object",
            "required": ["view_id"],
            "properties": {"view_id": {"type": "integer"}},
        },
    ),
    types.Tool(
        name="execute_view",
        description="Execute a view and return its matching tickets.",
        inputSchema={
            "type": "object",
            "required": ["view_id"],
            "properties": {
                "view_id":  {"type": "integer"},
                "page":     {"type": "integer"},
                "per_page": {"type": "integer"},
            },
        },
    ),

    # ── SLAs ─────────────────────────────────────────────────────────────────
    types.Tool(
        name="list_sla_policies",
        description="List all SLA policies.",
        inputSchema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="get_sla_policy",
        description="Get an SLA policy by ID.",
        inputSchema={
            "type": "object",
            "required": ["sla_id"],
            "properties": {"sla_id": {"type": "integer"}},
        },
    ),

    # ── TICKET METRICS ───────────────────────────────────────────────────────
    types.Tool(
        name="get_ticket_metrics",
        description="Get full SLA and timing metrics for a specific ticket.",
        inputSchema={
            "type": "object",
            "required": ["ticket_id"],
            "properties": {"ticket_id": {"type": "integer"}},
        },
    ),
    types.Tool(
        name="list_ticket_metrics",
        description="List metrics for all tickets.",
        inputSchema={
            "type": "object",
            "properties": {
                "page":     {"type": "integer"},
                "per_page": {"type": "integer"},
            },
        },
    ),

    # ── SATISFACTION RATINGS ─────────────────────────────────────────────────
    types.Tool(
        name="list_satisfaction_ratings",
        description="List satisfaction ratings with optional score filter.",
        inputSchema={
            "type": "object",
            "properties": {
                "score":     {"type": "string", "enum": ["offered","unoffered","received","received_with_comment","received_without_comment","good","bad","good_with_comment","bad_with_comment"]},
                "start_time": {"type": "string", "description": "ISO 8601"},
                "end_time":   {"type": "string"},
            },
        },
    ),
    types.Tool(
        name="get_satisfaction_rating",
        description="Get a single satisfaction rating by ID.",
        inputSchema={
            "type": "object",
            "required": ["rating_id"],
            "properties": {"rating_id": {"type": "integer"}},
        },
    ),

    # ── TAGS ─────────────────────────────────────────────────────────────────
    types.Tool(
        name="list_tags",
        description="List the most popular tags.",
        inputSchema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="get_ticket_tags",
        description="Get all tags on a ticket.",
        inputSchema={
            "type": "object",
            "required": ["ticket_id"],
            "properties": {"ticket_id": {"type": "integer"}},
        },
    ),
    types.Tool(
        name="set_ticket_tags",
        description="Replace all tags on a ticket.",
        inputSchema={
            "type": "object",
            "required": ["ticket_id", "tags"],
            "properties": {
                "ticket_id": {"type": "integer"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
        },
    ),
    types.Tool(
        name="add_ticket_tags",
        description="Add tags to a ticket without replacing existing ones.",
        inputSchema={
            "type": "object",
            "required": ["ticket_id", "tags"],
            "properties": {
                "ticket_id": {"type": "integer"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
        },
    ),

    # ── ATTACHMENTS ──────────────────────────────────────────────────────────
    types.Tool(
        name="list_ticket_attachments",
        description="List all attachments from all comments on a ticket.",
        inputSchema={
            "type": "object",
            "required": ["ticket_id"],
            "properties": {"ticket_id": {"type": "integer"}},
        },
    ),

    # ── HELP CENTER / ARTICLES ───────────────────────────────────────────────
    types.Tool(
        name="list_articles",
        description="List Help Center articles.",
        inputSchema={
            "type": "object",
            "properties": {
                "locale":   {"type": "string", "description": "e.g. 'en-us'"},
                "page":     {"type": "integer"},
                "per_page": {"type": "integer"},
            },
        },
    ),
    types.Tool(
        name="get_article",
        description="Get a Help Center article by ID.",
        inputSchema={
            "type": "object",
            "required": ["article_id"],
            "properties": {"article_id": {"type": "integer"}},
        },
    ),
    types.Tool(
        name="search_help_center",
        description="Search Help Center articles.",
        inputSchema={
            "type": "object",
            "required": ["query"],
            "properties": {"query": {"type": "string"}, "locale": {"type": "string"}},
        },
    ),
    types.Tool(
        name="create_article",
        description="Create a new Help Center article.",
        inputSchema={
            "type": "object",
            "required": ["title", "body", "section_id"],
            "properties": {
                "title":      {"type": "string"},
                "body":       {"type": "string"},
                "section_id": {"type": "integer"},
                "locale":     {"type": "string", "default": "en-us"},
                "draft":      {"type": "boolean"},
            },
        },
    ),
    types.Tool(
        name="list_sections",
        description="List all Help Center sections.",
        inputSchema={"type": "object", "properties": {"locale": {"type": "string"}}},
    ),
    types.Tool(
        name="list_categories",
        description="List all Help Center categories.",
        inputSchema={"type": "object", "properties": {"locale": {"type": "string"}}},
    ),

    # ── SEARCH ───────────────────────────────────────────────────────────────
    types.Tool(
        name="search",
        description="Universal Zendesk search across all object types. Use type:ticket, type:user, type:organization etc.",
        inputSchema={
            "type": "object",
            "required": ["query"],
            "properties": {
                "query":      {"type": "string"},
                "page":       {"type": "integer"},
                "per_page":   {"type": "integer"},
                "sort_by":    {"type": "string"},
                "sort_order": {"type": "string"},
            },
        },
    ),

    # ── WEBHOOKS ─────────────────────────────────────────────────────────────
    types.Tool(
        name="list_webhooks",
        description="List all webhooks.",
        inputSchema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="create_webhook",
        description="Create a new webhook.",
        inputSchema={
            "type": "object",
            "required": ["name", "endpoint", "http_method", "request_format", "subscriptions"],
            "properties": {
                "name":           {"type": "string"},
                "endpoint":       {"type": "string"},
                "http_method":    {"type": "string", "enum": ["GET","POST","PUT","PATCH","DELETE"]},
                "request_format": {"type": "string", "enum": ["json","xml","form_encoded"]},
                "subscriptions":  {"type": "array", "items": {"type": "string"}},
                "status":         {"type": "string", "enum": ["active","inactive"]},
            },
        },
    ),

    # ── ACCOUNT / SETTINGS ───────────────────────────────────────────────────
    types.Tool(
        name="get_account_settings",
        description="Get the Zendesk account settings.",
        inputSchema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="list_locales",
        description="List all supported locales in the account.",
        inputSchema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="list_schedules",
        description="List all business hour schedules.",
        inputSchema={"type": "object", "properties": {}},
    ),

    # ── ⚡ UNIVERSAL ESCAPE HATCH ────────────────────────────────────────────
    types.Tool(
        name="raw_api_call",
        description=(
            "POWER TOOL: Make a raw HTTP call to ANY Zendesk API endpoint. "
            "Use this for any endpoint not covered by the other tools, or for "
            "advanced use cases. Path is relative to /api/v2 e.g. '/tickets/123/audits'."
        ),
        inputSchema={
            "type": "object",
            "required": ["method", "path"],
            "properties": {
                "method": {"type": "string", "enum": ["GET","POST","PUT","PATCH","DELETE"]},
                "path":   {"type": "string", "description": "API path e.g. /tickets/123/audits"},
                "params": {"type": "object", "description": "Query string parameters"},
                "body":   {"type": "object", "description": "Request body for POST/PUT/PATCH"},
            },
        },
    ),
]

# ═══════════════════════════════════════════════════════════════════════════
#  LIST TOOLS HANDLER
# ═══════════════════════════════════════════════════════════════════════════
@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return TOOLS

# ═══════════════════════════════════════════════════════════════════════════
#  CALL TOOL HANDLER
# ═══════════════════════════════════════════════════════════════════════════
@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:

    # ── TICKETS ──────────────────────────────────────────────────────────────
    if name == "list_tickets":
        return ok(await zd("GET", "/tickets.json", params=arguments or None))

    if name == "get_ticket":
        return ok(await zd("GET", f"/tickets/{arguments['ticket_id']}.json"))

    if name == "get_ticket_custom_fields":
        tid = arguments["ticket_id"]
        ticket_data, fields_data = await asyncio.gather(
            zd("GET", f"/tickets/{tid}.json"),
            zd("GET", "/ticket_fields.json"),
        )
        ticket = ticket_data["ticket"]
        field_map = {f["id"]: f for f in fields_data["ticket_fields"]}
        decoded = []
        for cf in ticket.get("custom_fields", []):
            fid = cf["id"]
            meta = field_map.get(fid, {})
            entry = {
                "field_id":    fid,
                "field_label": meta.get("title", f"field_{fid}"),
                "field_type":  meta.get("type"),
                "value":       cf["value"],
            }
            # Decode dropdown/tagger options to human labels
            if cf["value"] and meta.get("custom_field_options"):
                for opt in meta["custom_field_options"]:
                    if opt.get("value") == cf["value"]:
                        entry["value_label"] = opt["name"]
                        break
            decoded.append(entry)
        return ok({"ticket_id": tid, "subject": ticket.get("subject"), "custom_fields": decoded})

    if name == "create_ticket":
        body: dict[str, Any] = {k: v for k, v in arguments.items() if k != "comment_body"}
        if "comment_body" in arguments:
            body["comment"] = {"body": arguments["comment_body"]}
        return ok(await zd("POST", "/tickets.json", body={"ticket": body}))

    if name == "update_ticket":
        tid = arguments.pop("ticket_id")
        body = dict(arguments)
        if "comment_body" in body:
            body["comment"] = {
                "body":   body.pop("comment_body"),
                "public": body.pop("comment_public", True),
            }
        return ok(await zd("PUT", f"/tickets/{tid}.json", body={"ticket": body}))

    if name == "delete_ticket":
        return ok(await zd("DELETE", f"/tickets/{arguments['ticket_id']}.json"))

    if name == "bulk_update_tickets":
        ids_param = ",".join(str(i) for i in arguments["ticket_ids"])
        return ok(await zd("PUT", "/tickets/update_many.json",
                           params={"ids": ids_param},
                           body={"ticket": arguments["update"]}))

    if name == "merge_tickets":
        tid = arguments["target_ticket_id"]
        body: dict[str, Any] = {"ids": arguments["source_ticket_ids"]}
        if "target_comment" in arguments:
            body["target_comment"] = arguments["target_comment"]
        if "source_comment" in arguments:
            body["source_comment"] = arguments["source_comment"]
        return ok(await zd("POST", f"/tickets/{tid}/merge.json", body=body))

    if name == "search_tickets":
        q = arguments.pop("query")
        arguments["query"] = f"type:ticket {q}"
        return ok(await zd("GET", "/search.json", params=arguments))

    if name == "list_ticket_comments":
        return ok(await zd("GET", f"/tickets/{arguments['ticket_id']}/comments.json"))

    if name == "add_ticket_comment":
        tid = arguments["ticket_id"]
        return ok(await zd("PUT", f"/tickets/{tid}.json", body={
            "ticket": {
                "comment": {
                    "body":      arguments["body"],
                    "public":    arguments.get("public", True),
                    "author_id": arguments.get("author_id"),
                }
            }
        }))

    # ── TICKET FIELDS ────────────────────────────────────────────────────────
    if name == "list_ticket_fields":
        return ok(await zd("GET", "/ticket_fields.json"))

    if name == "get_ticket_field":
        return ok(await zd("GET", f"/ticket_fields/{arguments['field_id']}.json"))

    if name == "create_ticket_field":
        return ok(await zd("POST", "/ticket_fields.json", body={"ticket_field": arguments}))

    if name == "update_ticket_field":
        fid = arguments.pop("field_id")
        return ok(await zd("PUT", f"/ticket_fields/{fid}.json", body={"ticket_field": arguments}))

    # ── USERS ────────────────────────────────────────────────────────────────
    if name == "list_users":
        return ok(await zd("GET", "/users.json", params=arguments or None))

    if name == "get_user":
        return ok(await zd("GET", f"/users/{arguments['user_id']}.json"))

    if name == "search_users":
        return ok(await zd("GET", "/users/search.json", params={"query": arguments["query"]}))

    if name == "create_user":
        return ok(await zd("POST", "/users.json", body={"user": arguments}))

    if name == "update_user":
        uid = arguments.pop("user_id")
        return ok(await zd("PUT", f"/users/{uid}.json", body={"user": arguments}))

    if name == "delete_user":
        return ok(await zd("DELETE", f"/users/{arguments['user_id']}.json"))

    if name == "get_user_tickets":
        uid = arguments["user_id"]
        t   = arguments["type"]
        endpoint = {"requested": "requested_tickets", "ccd": "ccd_tickets", "assigned": "assigned_tickets"}[t]
        return ok(await zd("GET", f"/users/{uid}/{endpoint}.json"))

    if name == "list_user_fields":
        return ok(await zd("GET", "/user_fields.json"))

    # ── ORGANIZATIONS ────────────────────────────────────────────────────────
    if name == "list_organizations":
        return ok(await zd("GET", "/organizations.json", params=arguments or None))

    if name == "get_organization":
        return ok(await zd("GET", f"/organizations/{arguments['org_id']}.json"))

    if name == "create_organization":
        return ok(await zd("POST", "/organizations.json", body={"organization": arguments}))

    if name == "update_organization":
        oid = arguments.pop("org_id")
        return ok(await zd("PUT", f"/organizations/{oid}.json", body={"organization": arguments}))

    if name == "get_organization_tickets":
        return ok(await zd("GET", f"/organizations/{arguments['org_id']}/tickets.json"))

    if name == "list_organization_fields":
        return ok(await zd("GET", "/organization_fields.json"))

    # ── GROUPS ───────────────────────────────────────────────────────────────
    if name == "list_groups":
        return ok(await zd("GET", "/groups.json"))

    if name == "get_group":
        return ok(await zd("GET", f"/groups/{arguments['group_id']}.json"))

    if name == "create_group":
        return ok(await zd("POST", "/groups.json", body={"group": arguments}))

    if name == "list_group_memberships":
        return ok(await zd("GET", f"/groups/{arguments['group_id']}/memberships.json"))

    # ── MACROS ───────────────────────────────────────────────────────────────
    if name == "list_macros":
        return ok(await zd("GET", "/macros.json", params=arguments or None))

    if name == "get_macro":
        return ok(await zd("GET", f"/macros/{arguments['macro_id']}.json"))

    if name == "apply_macro":
        return ok(await zd("GET",
                           f"/tickets/{arguments['ticket_id']}/macros/{arguments['macro_id']}/apply.json"))

    if name == "create_macro":
        return ok(await zd("POST", "/macros.json", body={"macro": arguments}))

    # ── TRIGGERS ─────────────────────────────────────────────────────────────
    if name == "list_triggers":
        return ok(await zd("GET", "/triggers.json", params=arguments or None))

    if name == "get_trigger":
        return ok(await zd("GET", f"/triggers/{arguments['trigger_id']}.json"))

    if name == "create_trigger":
        return ok(await zd("POST", "/triggers.json", body={"trigger": arguments}))

    if name == "update_trigger":
        tid = arguments.pop("trigger_id")
        return ok(await zd("PUT", f"/triggers/{tid}.json", body={"trigger": arguments}))

    # ── AUTOMATIONS ──────────────────────────────────────────────────────────
    if name == "list_automations":
        return ok(await zd("GET", "/automations.json"))

    if name == "get_automation":
        return ok(await zd("GET", f"/automations/{arguments['automation_id']}.json"))

    # ── VIEWS ────────────────────────────────────────────────────────────────
    if name == "list_views":
        return ok(await zd("GET", "/views.json"))

    if name == "get_view":
        return ok(await zd("GET", f"/views/{arguments['view_id']}.json"))

    if name == "execute_view":
        vid = arguments.pop("view_id")
        return ok(await zd("GET", f"/views/{vid}/execute.json", params=arguments or None))

    # ── SLAs ─────────────────────────────────────────────────────────────────
    if name == "list_sla_policies":
        return ok(await zd("GET", "/slas/policies.json"))

    if name == "get_sla_policy":
        return ok(await zd("GET", f"/slas/policies/{arguments['sla_id']}.json"))

    # ── TICKET METRICS ───────────────────────────────────────────────────────
    if name == "get_ticket_metrics":
        return ok(await zd("GET", f"/tickets/{arguments['ticket_id']}/metrics.json"))

    if name == "list_ticket_metrics":
        return ok(await zd("GET", "/ticket_metrics.json", params=arguments or None))

    # ── SATISFACTION RATINGS ─────────────────────────────────────────────────
    if name == "list_satisfaction_ratings":
        return ok(await zd("GET", "/satisfaction_ratings.json", params=arguments or None))

    if name == "get_satisfaction_rating":
        return ok(await zd("GET", f"/satisfaction_ratings/{arguments['rating_id']}.json"))

    # ── TAGS ─────────────────────────────────────────────────────────────────
    if name == "list_tags":
        return ok(await zd("GET", "/tags.json"))

    if name == "get_ticket_tags":
        return ok(await zd("GET", f"/tickets/{arguments['ticket_id']}/tags.json"))

    if name == "set_ticket_tags":
        tid = arguments["ticket_id"]
        return ok(await zd("POST", f"/tickets/{tid}/tags.json", body={"tags": arguments["tags"]}))

    if name == "add_ticket_tags":
        tid = arguments["ticket_id"]
        return ok(await zd("PUT", f"/tickets/{tid}/tags.json", body={"tags": arguments["tags"]}))

    # ── ATTACHMENTS ──────────────────────────────────────────────────────────
    if name == "list_ticket_attachments":
        comments = await zd("GET", f"/tickets/{arguments['ticket_id']}/comments.json")
        attachments = []
        for c in comments.get("comments", []):
            for a in c.get("attachments", []):
                attachments.append({
                    "comment_id":   c["id"],
                    "attachment_id": a["id"],
                    "file_name":    a["file_name"],
                    "content_type": a["content_type"],
                    "size":         a["size"],
                    "content_url":  a["content_url"],
                })
        return ok({"ticket_id": arguments["ticket_id"], "attachments": attachments})

    # ── HELP CENTER ──────────────────────────────────────────────────────────
    if name == "list_articles":
        locale = arguments.pop("locale", "en-us")
        return ok(await zd("GET", f"/help_center/{locale}/articles.json", params=arguments or None))

    if name == "get_article":
        return ok(await zd("GET", f"/help_center/articles/{arguments['article_id']}.json"))

    if name == "search_help_center":
        return ok(await zd("GET", "/help_center/articles/search.json",
                           params={"query": arguments["query"], "locale": arguments.get("locale","en-us")}))

    if name == "create_article":
        sid    = arguments.pop("section_id")
        locale = arguments.pop("locale", "en-us")
        return ok(await zd("POST", f"/help_center/{locale}/sections/{sid}/articles.json",
                           body={"article": arguments}))

    if name == "list_sections":
        locale = arguments.get("locale", "en-us")
        return ok(await zd("GET", f"/help_center/{locale}/sections.json"))

    if name == "list_categories":
        locale = arguments.get("locale", "en-us")
        return ok(await zd("GET", f"/help_center/{locale}/categories.json"))

    # ── SEARCH ───────────────────────────────────────────────────────────────
    if name == "search":
        return ok(await zd("GET", "/search.json", params=arguments))

    # ── WEBHOOKS ─────────────────────────────────────────────────────────────
    if name == "list_webhooks":
        return ok(await zd("GET", "/webhooks"))

    if name == "create_webhook":
        return ok(await zd("POST", "/webhooks", body={"webhook": arguments}))

    # ── ACCOUNT ──────────────────────────────────────────────────────────────
    if name == "get_account_settings":
        return ok(await zd("GET", "/account/settings.json"))

    if name == "list_locales":
        return ok(await zd("GET", "/locales.json"))

    if name == "list_schedules":
        return ok(await zd("GET", "/business_hours/schedules.json"))

    # ── ⚡ UNIVERSAL ESCAPE HATCH ────────────────────────────────────────────
    if name == "raw_api_call":
        return ok(await zd(
            arguments["method"],
            arguments["path"],
            params=arguments.get("params"),
            body=arguments.get("body"),
        ))

    return ok({"error": f"Unknown tool: {name}"})

# ═══════════════════════════════════════════════════════════════════════════
#  SSE / HTTP SERVER  (Claude.ai connects to this directly)
# ═══════════════════════════════════════════════════════════════════════════
def run_sse():
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.routing import Mount, Route
    import uvicorn

    sse = SseServerTransport("/messages/")

    async def handle_sse(request):
        async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
            await app.run(streams[0], streams[1], app.create_initialization_options())

    starlette_app = Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Mount("/messages/", app=sse.handle_post_message),
        ]
    )

    port = int(os.environ.get("PORT", 8080))
    print(f"\n🚀  Zendesk MCP Server → http://localhost:{port}/sse")
    print(f"    Add this to Claude.ai: Settings → Integrations → Add MCP Server\n")
    uvicorn.run(starlette_app, host="0.0.0.0", port=port)


# ═══════════════════════════════════════════════════════════════════════════
#  ENTRY POINT  — defaults to SSE; set TRANSPORT=stdio to use stdio
# ═══════════════════════════════════════════════════════════════════════════
async def main_stdio():
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())

if __name__ == "__main__":
    transport = os.environ.get("TRANSPORT", "sse").lower()
    if transport == "stdio":
        asyncio.run(main_stdio())
    else:
        run_sse()



def cli_entry():
    """Entry point for `uvx zendesk-mcp` and `pip install zendesk-mcp`."""
    missing = [v for v in ["ZENDESK_SUBDOMAIN", "ZENDESK_EMAIL", "ZENDESK_API_TOKEN"] if not os.environ.get(v)]
    if missing:
        print("❌  Missing required environment variables:")
        for v in missing:
            print(f"    {v}")
        print("\nSet them in your Claude Desktop config under the 'env' block.")
        print("See README for setup instructions.")
        raise SystemExit(1)
    transport = os.environ.get("TRANSPORT", "stdio").lower()
    if transport == "stdio":
        asyncio.run(main_stdio())
    else:
        run_sse()
