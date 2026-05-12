from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.analytics_event import AnalyticsEvent, EventType
from app.models.attribution import AnalyticsRollup
from app.models.organization import OrganizationMembership
from app.models.user import User
from app.schemas.analytics_event import AnalyticsEventCreate, AnalyticsEventRead
from app.repositories.analytics_event_repo import AnalyticsEventRepository

router = APIRouter()


@router.post("/", response_model=AnalyticsEventRead, status_code=201)
async def create_analytics_event(data: AnalyticsEventCreate, db: AsyncSession = Depends(get_db)):
    repo = AnalyticsEventRepository(db)
    event = AnalyticsEvent(**data.model_dump())
    return await repo.create(event)


@router.get("/campaign/{campaign_id}", response_model=dict)
async def list_analytics_by_campaign(
    campaign_id: UUID,
    event_type: Optional[EventType] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    repo = AnalyticsEventRepository(db)
    items, total = await repo.list_by_campaign(
        campaign_id=campaign_id, event_type=event_type, limit=limit, offset=offset
    )
    return {"items": [AnalyticsEventRead.model_validate(item) for item in items], "total": total}


@router.get("/campaign/{campaign_id}/summary")
async def get_campaign_summary(campaign_id: UUID, db: AsyncSession = Depends(get_db)):
    repo = AnalyticsEventRepository(db)
    summary = await repo.get_summary_by_campaign(campaign_id)
    return summary


# ---------- Phase 8.1 — daily rollups ---------------------------------


async def _require_member(
    session: AsyncSession, user: User, org_id: UUID
) -> None:
    if user.is_superuser:
        return
    result = await session.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == org_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not a member."
        )


@router.get("/rollups")
async def list_rollups(
    organization_id: UUID,
    scope: Optional[str] = Query(None, regex="^(org|channel|project|campaign)$"),
    days: int = Query(7, ge=1, le=90),
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Returns the last ``days`` of AnalyticsRollup rows for the org.

    Used by the Analyst Agent + the /analytics dashboard. Filter by
    scope (``org`` for the summary timeline, ``channel`` for the
    stacked chart).
    """
    await _require_member(db, user, organization_id)

    since = datetime.now(tz=timezone.utc) - timedelta(days=days)
    stmt = (
        select(AnalyticsRollup)
        .where(
            AnalyticsRollup.organization_id == organization_id,
            AnalyticsRollup.day >= since,
        )
        .order_by(AnalyticsRollup.day.asc())
    )
    if scope:
        stmt = stmt.where(AnalyticsRollup.scope == scope)
    rows = (await db.execute(stmt)).scalars().all()

    return {
        "organization_id": str(organization_id),
        "days": days,
        "scope": scope,
        "rollups": [
            {
                "scope": r.scope,
                "scope_key": r.scope_key,
                "day": r.day.isoformat(),
                "metric_json": r.metric_json,
                "computed_at": r.computed_at.isoformat(),
            }
            for r in rows
        ],
    }
