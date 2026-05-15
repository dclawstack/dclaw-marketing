"""Overview tools — dashboard summary, KPI snapshot."""

from __future__ import annotations

from sqlalchemy import func, select

from app.agents.tools.registry import ToolContext, tool
from app.models.analytics_event import AnalyticsEvent
from app.models.approval_request import ApprovalRequest, ApprovalStatus
from app.models.asset import Asset
from app.models.scheduled_post import ScheduledPost, ScheduledPostStatus


@tool(
    name="get_dashboard_summary",
    description=(
        "Return a high-level KPI snapshot for the current organization "
        "(asset count, queued posts, pending approvals, recent analytics "
        "events). Use when the user asks how things are going / for a "
        "status summary / for what's pending."
    ),
    input_schema={"type": "object", "properties": {}},
    category="overview",
)
async def get_dashboard_summary(ctx: ToolContext) -> dict:
    s = ctx.session
    asset_count = (
        await s.execute(
            select(func.count(Asset.id)).where(Asset.organization_id == ctx.org_id)
        )
    ).scalar_one()
    queued_posts = (
        await s.execute(
            select(func.count(ScheduledPost.id)).where(
                ScheduledPost.organization_id == ctx.org_id,
                ScheduledPost.status == ScheduledPostStatus.queued,
            )
        )
    ).scalar_one()
    pending_approvals = (
        await s.execute(
            select(func.count(ApprovalRequest.id)).where(
                ApprovalRequest.organization_id == ctx.org_id,
                ApprovalRequest.status == ApprovalStatus.pending,
            )
        )
    ).scalar_one()
    recent_events = (
        await s.execute(
            select(func.count(AnalyticsEvent.id)).where(
                AnalyticsEvent.organization_id == ctx.org_id,
            )
        )
    ).scalar_one()
    return {
        "ok": True,
        "org_id": str(ctx.org_id),
        "kpis": {
            "assets": int(asset_count),
            "scheduled_posts_queued": int(queued_posts),
            "pending_approvals": int(pending_approvals),
            "analytics_events_total": int(recent_events),
        },
    }


@tool(
    name="list_kpis",
    description="Alias for get_dashboard_summary. Same KPI snapshot.",
    input_schema={"type": "object", "properties": {}},
    category="overview",
)
async def list_kpis(ctx: ToolContext) -> dict:
    return await get_dashboard_summary(ctx)
