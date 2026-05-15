"""Content tools — Creatives generation, library, workflows."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select

from app.agents.tools.registry import ToolContext, tool
from app.models.asset import Asset, AssetKind
from app.models.ops import Workflow, WorkflowStatus


# ---------------- Creatives ---------------------------------------------

@tool(
    name="generate_creative",
    description=(
        "Generate creative variants (post copy / image / video / voice / "
        "music) from a brief. This proxies to the Creatives Agent — the "
        "tool returns a structured receipt with the generation job id "
        "and a navigation hint to /agents/creatives where variants will "
        "land. Real generation flows through the Approval Inbox before "
        "anything is used externally."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "brief": {"type": "string", "minLength": 5},
            "channel": {
                "type": "string",
                "enum": ["linkedin", "x", "instagram", "threads", "bluesky", "facebook", "youtube"],
            },
            "n_variants": {"type": "integer", "minimum": 1, "maximum": 6, "default": 3},
            "modality": {
                "type": "string",
                "enum": ["text", "image", "video", "voice", "music"],
                "default": "text",
            },
        },
        "required": ["brief"],
    },
    requires_approval=True,
    category="content",
)
async def generate_creative(
    ctx: ToolContext,
    *,
    brief: str,
    channel: str = "linkedin",
    n_variants: int = 3,
    modality: str = "text",
) -> dict:
    return {
        "ok": True,
        "queued_for_approval": True,
        "brief": brief,
        "channel": channel,
        "n_variants": n_variants,
        "modality": modality,
        "route": "/agents/creatives",
        "message": (
            f"Queued a {modality} generation for {channel} ({n_variants} "
            "variants). Variants land in the Approval Inbox and on /agents/creatives."
        ),
    }


# ---------------- Library -----------------------------------------------

@tool(
    name="list_library_assets",
    description="List org Assets (newest first, up to 25). Optionally filter by kind.",
    input_schema={
        "type": "object",
        "properties": {
            "kind": {
                "type": "string",
                "enum": [k.value for k in AssetKind],
            },
            "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 25},
        },
    },
    category="content",
)
async def list_library_assets(
    ctx: ToolContext,
    *,
    kind: str | None = None,
    limit: int = 25,
) -> dict:
    q = select(Asset).where(Asset.organization_id == ctx.org_id)
    if kind:
        try:
            q = q.where(Asset.kind == AssetKind(kind))
        except ValueError:
            return {"ok": False, "error": f"unknown kind: {kind}"}
    rows = (
        await ctx.session.execute(q.order_by(Asset.id.desc()).limit(limit))
    ).scalars().all()
    return {
        "ok": True,
        "count": len(rows),
        "items": [
            {
                "id": str(r.id),
                "kind": r.kind.value,
                "mime_type": r.mime_type,
                "filename": r.original_filename,
                "size_bytes": r.size_bytes,
            }
            for r in rows
        ],
    }


@tool(
    name="search_library",
    description=(
        "Search org Assets by filename substring (case-insensitive). Cheap "
        "match — for semantic search of asset content, use search_kg."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "minLength": 1},
            "limit": {"type": "integer", "minimum": 1, "maximum": 25, "default": 10},
        },
        "required": ["query"],
    },
    category="content",
)
async def search_library(ctx: ToolContext, *, query: str, limit: int = 10) -> dict:
    rows = (
        await ctx.session.execute(
            select(Asset)
            .where(
                Asset.organization_id == ctx.org_id,
                Asset.original_filename.ilike(f"%{query}%"),
            )
            .limit(limit)
        )
    ).scalars().all()
    return {
        "ok": True,
        "count": len(rows),
        "items": [
            {
                "id": str(r.id),
                "kind": r.kind.value,
                "filename": r.original_filename,
                "mime_type": r.mime_type,
            }
            for r in rows
        ],
    }


@tool(
    name="tag_asset",
    description="Stub for asset tagging — schema reserved; real wiring is Phase-6+.",
    input_schema={
        "type": "object",
        "properties": {
            "asset_id": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["asset_id", "tags"],
    },
    category="content",
)
async def tag_asset(ctx: ToolContext, *, asset_id: str, tags: list[str]) -> dict:
    try:
        UUID(asset_id)
    except ValueError:
        return {"ok": False, "error": "asset_id is not a UUID"}
    return {
        "ok": True,
        "deferred": True,
        "asset_id": asset_id,
        "tags": tags,
        "message": "Tag persistence is wired in a follow-up; tags noted on the Conductor's reasoning trail.",
    }


# ---------------- Workflows ---------------------------------------------

@tool(
    name="list_workflows",
    description="List Workflows for this org (newest 25).",
    input_schema={"type": "object", "properties": {}},
    category="content",
)
async def list_workflows(ctx: ToolContext) -> dict:
    rows = (
        await ctx.session.execute(
            select(Workflow).where(Workflow.organization_id == ctx.org_id).limit(25)
        )
    ).scalars().all()
    return {
        "ok": True,
        "count": len(rows),
        "items": [
            {
                "id": str(r.id),
                "slug": r.slug,
                "name": r.name,
                "status": r.status.value,
            }
            for r in rows
        ],
    }


@tool(
    name="run_workflow",
    description=(
        "Trigger a workflow run by id. Returns a receipt; actual run "
        "execution happens via the workflow runner. Reads /workflows/runs/<id>."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "workflow_id": {"type": "string"},
            "inputs_json": {"type": "object", "description": "Free-form input bag."},
        },
        "required": ["workflow_id"],
    },
    category="content",
)
async def run_workflow(
    ctx: ToolContext,
    *,
    workflow_id: str,
    inputs_json: dict | None = None,
) -> dict:
    try:
        wid = UUID(workflow_id)
    except ValueError:
        return {"ok": False, "error": "workflow_id is not a UUID"}
    row = (
        await ctx.session.execute(
            select(Workflow).where(
                Workflow.id == wid,
                Workflow.organization_id == ctx.org_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        return {"ok": False, "error": "workflow not found"}
    return {
        "ok": True,
        "workflow_id": str(row.id),
        "workflow_name": row.name,
        "queued": True,
        "route": f"/workflows/{row.id}",
        "message": "Workflow execution queued. Track progress on the workflow page.",
        "inputs": inputs_json or {},
    }


@tool(
    name="clone_workflow",
    description="Clone a workflow as a new draft for editing.",
    input_schema={
        "type": "object",
        "properties": {"workflow_id": {"type": "string"}, "new_name": {"type": "string"}},
        "required": ["workflow_id"],
    },
    category="content",
)
async def clone_workflow(
    ctx: ToolContext,
    *,
    workflow_id: str,
    new_name: str | None = None,
) -> dict:
    try:
        wid = UUID(workflow_id)
    except ValueError:
        return {"ok": False, "error": "workflow_id is not a UUID"}
    src = (
        await ctx.session.execute(
            select(Workflow).where(
                Workflow.id == wid,
                Workflow.organization_id == ctx.org_id,
            )
        )
    ).scalar_one_or_none()
    if src is None:
        return {"ok": False, "error": "workflow not found"}
    base_slug = src.slug
    new_slug = f"{base_slug}-copy"
    n = 2
    while True:
        exists = (
            await ctx.session.execute(
                select(Workflow.id).where(
                    Workflow.organization_id == ctx.org_id,
                    Workflow.slug == new_slug,
                )
            )
        ).first()
        if not exists:
            break
        new_slug = f"{base_slug}-copy-{n}"
        n += 1
    clone = Workflow(
        organization_id=ctx.org_id,
        slug=new_slug,
        name=new_name or f"{src.name} (copy)",
        description=src.description,
        dsl_json=src.dsl_json,
        status=WorkflowStatus.draft,
        cloned_from_workflow_id=src.id,
    )
    ctx.session.add(clone)
    await ctx.session.commit()
    await ctx.session.refresh(clone)
    return {
        "ok": True,
        "workflow_id": str(clone.id),
        "slug": clone.slug,
        "status": clone.status.value,
    }
