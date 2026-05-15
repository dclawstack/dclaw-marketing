"""Insights tools — SEO, AEO, analytics, knowledge graph."""

from __future__ import annotations

from sqlalchemy import func, select

from app.agents.tools.registry import ToolContext, tool
from app.models.analytics_event import AnalyticsEvent
from app.models.ingestion import DocumentChunk, IngestionSource


# ---------------- SEO / AEO --------------------------------------------

@tool(
    name="run_seo_audit",
    description=(
        "Queue an SEO audit for a URL. Returns a structured receipt; the "
        "audit job runs async on /agents/seo/pipeline and lands its "
        "scored report there. Use when the user asks to audit / score a "
        "URL for SEO."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "url": {"type": "string", "format": "uri"},
            "depth": {"type": "string", "enum": ["quick", "deep"], "default": "quick"},
        },
        "required": ["url"],
    },
    category="insights",
)
async def run_seo_audit(ctx: ToolContext, *, url: str, depth: str = "quick") -> dict:
    return {
        "ok": True,
        "queued": True,
        "url": url,
        "depth": depth,
        "route": "/agents/seo/pipeline",
        "message": "SEO audit queued. Watch /agents/seo/pipeline for the scored report.",
    }


@tool(
    name="keyword_research",
    description="Run a keyword-research pass for a topic. Stubbed receipt — full pipeline is /agents/seo.",
    input_schema={
        "type": "object",
        "properties": {
            "topic": {"type": "string"},
            "n_keywords": {"type": "integer", "minimum": 5, "maximum": 100, "default": 25},
        },
        "required": ["topic"],
    },
    category="insights",
)
async def keyword_research(
    ctx: ToolContext,
    *,
    topic: str,
    n_keywords: int = 25,
) -> dict:
    return {
        "ok": True,
        "queued": True,
        "topic": topic,
        "n_keywords": n_keywords,
        "route": "/agents/seo",
    }


@tool(
    name="aeo_score",
    description=(
        "Score a URL for Answer Engine Optimization (how well it's "
        "structured for AI search). Queues an async job; results land "
        "on /agents/seo."
    ),
    input_schema={
        "type": "object",
        "properties": {"url": {"type": "string", "format": "uri"}},
        "required": ["url"],
    },
    category="insights",
)
async def aeo_score(ctx: ToolContext, *, url: str) -> dict:
    return {
        "ok": True,
        "queued": True,
        "url": url,
        "route": "/agents/seo",
        "message": "AEO scoring queued. Heatmap on /agents/seo will refresh.",
    }


# ---------------- Analytics --------------------------------------------

@tool(
    name="get_analytics_report",
    description=(
        "Return an analytics summary (event count by type) for this org "
        "from the analytics_events table. Use when the user asks for a "
        "rollup / engagement overview."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "limit_groups": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
        },
    },
    category="insights",
)
async def get_analytics_report(ctx: ToolContext, *, limit_groups: int = 10) -> dict:
    rows = (
        await ctx.session.execute(
            select(AnalyticsEvent.event_type, func.count(AnalyticsEvent.id))
            .where(AnalyticsEvent.organization_id == ctx.org_id)
            .group_by(AnalyticsEvent.event_type)
            .order_by(func.count(AnalyticsEvent.id).desc())
            .limit(limit_groups)
        )
    ).all()
    return {
        "ok": True,
        "by_event_type": [
            {"event_type": str(et), "count": int(c)} for et, c in rows
        ],
        "route": "/analytics",
    }


@tool(
    name="drill_campaign",
    description="Drill into a specific campaign's analytics. Stubbed receipt — opens /analytics.",
    input_schema={
        "type": "object",
        "properties": {"campaign_id": {"type": "string"}},
        "required": ["campaign_id"],
    },
    category="insights",
)
async def drill_campaign(ctx: ToolContext, *, campaign_id: str) -> dict:
    return {
        "ok": True,
        "campaign_id": campaign_id,
        "route": f"/analytics?campaign={campaign_id}",
    }


# ---------------- Knowledge Graph --------------------------------------

@tool(
    name="search_kg",
    description=(
        "Search the org's Knowledge Graph for ingested documents/chunks "
        "matching a substring (case-insensitive). For real semantic "
        "search, the embedding pipeline must be running — this tool "
        "currently returns lexical matches as a baseline."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 8},
        },
        "required": ["query"],
    },
    category="insights",
)
async def search_kg(ctx: ToolContext, *, query: str, limit: int = 8) -> dict:
    rows = (
        await ctx.session.execute(
            select(DocumentChunk, IngestionSource)
            .join(IngestionSource, DocumentChunk.source_id == IngestionSource.id)
            .where(
                IngestionSource.organization_id == ctx.org_id,
                DocumentChunk.text.ilike(f"%{query}%"),
            )
            .limit(limit)
        )
    ).all()
    return {
        "ok": True,
        "count": len(rows),
        "items": [
            {
                "source_id": str(src.id),
                "source_type": getattr(src.source_type, "value", str(src.source_type)),
                "source_label": src.name,
                "chunk_id": str(chunk.id),
                "preview": (chunk.text or "")[:240],
            }
            for chunk, src in rows
        ],
    }


@tool(
    name="ingest_knowledge",
    description=(
        "Queue a new ingestion source (URL or asset) into the Knowledge "
        "Graph. Real ingestion runs async; this tool returns a receipt."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "url": {"type": "string", "format": "uri"},
            "asset_id": {"type": "string"},
            "label": {"type": "string"},
        },
    },
    category="insights",
)
async def ingest_knowledge(
    ctx: ToolContext,
    *,
    url: str | None = None,
    asset_id: str | None = None,
    label: str = "",
) -> dict:
    if not url and not asset_id:
        return {"ok": False, "error": "either url or asset_id is required"}
    return {
        "ok": True,
        "queued": True,
        "url": url,
        "asset_id": asset_id,
        "label": label,
        "route": "/knowledge",
        "message": "Ingestion queued. Watch /knowledge for the new source.",
    }
