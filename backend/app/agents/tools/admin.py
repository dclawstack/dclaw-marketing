"""Admin tools — integrations, orgs, users, models."""

from __future__ import annotations

from sqlalchemy import select

from app.agents.tools.registry import ToolContext, tool
from app.models.connection import Connection
from app.models.model_registry import ModelEntry, ModelProvider
from app.models.organization import (
    Organization,
    OrganizationMembership,
    OrganizationRole,
)
from app.models.user import User


# ---------------- Integrations ----------------------------------------

@tool(
    name="list_integrations",
    description="List MCP / integration connections for this org.",
    input_schema={"type": "object", "properties": {}},
    category="admin",
)
async def list_integrations(ctx: ToolContext) -> dict:
    rows = (
        await ctx.session.execute(
            select(Connection).where(Connection.organization_id == ctx.org_id)
        )
    ).scalars().all()
    return {
        "ok": True,
        "count": len(rows),
        "items": [
            {
                "id": str(r.id),
                "name": r.name,
                "server_id": getattr(r, "server_id", None),
                "status": getattr(r.status, "value", None) if getattr(r, "status", None) else None,
            }
            for r in rows
        ],
    }


@tool(
    name="connect_integration",
    description="Walks the user to /integrations to connect a new MCP/integration.",
    input_schema={
        "type": "object",
        "properties": {"name": {"type": "string"}},
        "required": ["name"],
    },
    category="admin",
)
async def connect_integration(ctx: ToolContext, *, name: str) -> dict:
    return {
        "ok": True,
        "next_step": "open_integrations_page",
        "name": name,
        "route": "/integrations",
        "message": f"Open /integrations to connect {name}.",
    }


# ---------------- Orgs ------------------------------------------------

@tool(
    name="list_orgs",
    description=(
        "List orgs the current user has access to. Useful for cross-org "
        "navigation hints."
    ),
    input_schema={"type": "object", "properties": {}},
    category="admin",
)
async def list_orgs(ctx: ToolContext) -> dict:
    rows = (
        await ctx.session.execute(
            select(Organization, OrganizationMembership)
            .join(
                OrganizationMembership,
                OrganizationMembership.organization_id == Organization.id,
            )
            .where(OrganizationMembership.user_id == ctx.user_id)
        )
    ).all()
    return {
        "ok": True,
        "count": len(rows),
        "items": [
            {
                "id": str(org.id),
                "slug": org.slug,
                "name": org.name,
                "role": mem.role.value,
            }
            for org, mem in rows
        ],
    }


@tool(
    name="create_org",
    description=(
        "Create a new organization. Restricted to superadmins. Returns "
        "either {ok: true, org_id} or {ok: false, error}."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "slug": {"type": "string", "pattern": "^[a-z0-9-]+$"},
            "name": {"type": "string"},
        },
        "required": ["slug", "name"],
    },
    requires_approval=True,
    category="admin",
)
async def create_org(ctx: ToolContext, *, slug: str, name: str) -> dict:
    # Superadmin gate
    requester = (
        await ctx.session.execute(select(User).where(User.id == ctx.user_id))
    ).scalar_one_or_none()
    if requester is None or not requester.is_superuser:
        return {"ok": False, "error": "create_org requires superadmin"}
    exists = (
        await ctx.session.execute(select(Organization).where(Organization.slug == slug))
    ).scalar_one_or_none()
    if exists is not None:
        return {"ok": False, "error": f"slug '{slug}' already taken"}
    org = Organization(slug=slug, name=name)
    ctx.session.add(org)
    await ctx.session.commit()
    await ctx.session.refresh(org)
    return {"ok": True, "org_id": str(org.id), "slug": org.slug, "name": org.name}


# ---------------- Users -----------------------------------------------

@tool(
    name="list_users",
    description="List members of the current org with their roles.",
    input_schema={"type": "object", "properties": {}},
    category="admin",
)
async def list_users(ctx: ToolContext) -> dict:
    rows = (
        await ctx.session.execute(
            select(User, OrganizationMembership)
            .join(OrganizationMembership, OrganizationMembership.user_id == User.id)
            .where(OrganizationMembership.organization_id == ctx.org_id)
        )
    ).all()
    return {
        "ok": True,
        "count": len(rows),
        "items": [
            {
                "id": str(u.id),
                "email": u.email,
                "full_name": u.full_name,
                "role": m.role.value,
            }
            for u, m in rows
        ],
    }


@tool(
    name="invite_user",
    description=(
        "Invite a user to the current org with a given role. Stubbed "
        "receipt — the real invitation flow lives on /admin/users."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "email": {"type": "string", "format": "email"},
            "role": {
                "type": "string",
                "enum": [r.value for r in OrganizationRole],
            },
        },
        "required": ["email", "role"],
    },
    requires_approval=True,
    category="admin",
)
async def invite_user(ctx: ToolContext, *, email: str, role: str) -> dict:
    return {
        "ok": True,
        "queued": True,
        "email": email,
        "role": role,
        "route": "/admin/users",
        "message": f"Routed an invitation receipt for {email} as {role}.",
    }


# ---------------- Models ----------------------------------------------

@tool(
    name="list_models",
    description="List ModelEntry rows from the Model Registry (~all providers/models).",
    input_schema={
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 50},
        },
    },
    category="admin",
)
async def list_models(ctx: ToolContext, *, limit: int = 50) -> dict:
    rows = (
        await ctx.session.execute(
            select(ModelEntry, ModelProvider)
            .join(ModelProvider, ModelEntry.provider_id == ModelProvider.id)
            .limit(limit)
        )
    ).all()
    return {
        "ok": True,
        "count": len(rows),
        "items": [
            {
                "id": str(m.id),
                "name": getattr(m, "model_name", getattr(m, "name", None)),
                "provider": getattr(p, "name", None),
                "capabilities": getattr(m, "capabilities", None),
            }
            for m, p in rows
        ],
    }


@tool(
    name="set_model_pref",
    description=(
        "Set the user's preferred model entry for a capability. Stubbed "
        "receipt; the real wiring lives on /admin/models."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "model_entry_id": {"type": "string"},
            "capability": {"type": "string"},
        },
        "required": ["model_entry_id", "capability"],
    },
    category="admin",
)
async def set_model_pref(
    ctx: ToolContext,
    *,
    model_entry_id: str,
    capability: str,
) -> dict:
    return {
        "ok": True,
        "queued": True,
        "model_entry_id": model_entry_id,
        "capability": capability,
        "route": "/admin/models",
    }
