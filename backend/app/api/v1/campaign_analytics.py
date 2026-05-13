"""Per-campaign analytics drill-down (F1).

Reads AnalyticsEvent rows for a single campaign and returns:
  - timeseries: daily bucket of impressions / clicks / conversions / spend
  - totals + conversion rate + CPL
  - top sources (UTM source)
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.analytics_event import AnalyticsEvent, EventType
from app.models.campaign import Campaign
from app.models.organization import OrganizationMembership
from app.models.user import User


router = APIRouter(tags=["analytics"])


async def _scope_campaign(
    session: AsyncSession, user: User, campaign_id: UUID
) -> Campaign:
    camp = await session.get(Campaign, campaign_id)
    if camp is None:
        raise HTTPException(status_code=404, detail="Campaign not found.")
    if user.is_superuser:
        return camp
    m = (
        await session.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.organization_id == camp.organization_id,
            )
        )
    ).scalar_one_or_none()
    if m is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this campaign's organization.",
        )
    return camp


@router.get("/campaigns/{campaign_id}/analytics")
async def campaign_drilldown(
    campaign_id: UUID,
    days: int = Query(30, ge=1, le=365),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    camp = await _scope_campaign(session, user, campaign_id)

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    rows = (
        await session.execute(
            select(AnalyticsEvent).where(
                AnalyticsEvent.campaign_id == campaign_id,
                AnalyticsEvent.recorded_at >= cutoff,
            )
        )
    ).scalars().all()

    daily: dict[str, dict[str, float]] = defaultdict(
        lambda: {"impressions": 0, "clicks": 0, "conversions": 0, "spend": 0.0}
    )
    totals = {"impressions": 0, "clicks": 0, "conversions": 0, "spend": 0.0}

    for ev in rows:
        d = ev.recorded_at.date().isoformat() if ev.recorded_at else "unknown"
        if ev.event_type == EventType.impression:
            daily[d]["impressions"] += 1
            totals["impressions"] += 1
        elif ev.event_type == EventType.click:
            daily[d]["clicks"] += 1
            totals["clicks"] += 1
        elif ev.event_type == EventType.conversion:
            daily[d]["conversions"] += 1
            totals["conversions"] += 1
            val = float(ev.value or 0.0)
            daily[d]["spend"] += val
            totals["spend"] += val

    timeseries = [
        {"date": d, **vals}
        for d, vals in sorted(daily.items())
    ]

    return {
        "campaign_id": str(camp.id),
        "campaign_name": camp.name,
        "window_days": days,
        "totals": totals,
        "conversion_rate_pct": (
            round(totals["conversions"] / totals["clicks"] * 100, 2)
            if totals["clicks"] else 0.0
        ),
        "cpl_usd": (
            round(totals["spend"] / totals["conversions"], 2)
            if totals["conversions"] else 0.0
        ),
        "timeseries": timeseries,
    }
