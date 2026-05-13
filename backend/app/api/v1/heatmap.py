"""F2 Content Performance Heatmap (SP3-13).

Aggregates Touchpoints into a 7×24 grid (day-of-week × hour-of-day) so the
UI can render a "when does my content actually get engagement?" heatmap.

Endpoint:
  GET /api/v1/orgs/{org}/analytics/heatmap?days=90&channel=...

Returns:
  {
    "grid": [[count, ...], ...],            # 7 rows (Mon..Sun) × 24 cols
    "max": int,                              # for rendering scale
    "total": int,
    "window_days": int,
    "channel": str | null
  }
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.attribution import Touchpoint
from app.models.organization import OrganizationMembership
from app.models.user import User


router = APIRouter(tags=["analytics-heatmap"])


async def _require_member(
    session: AsyncSession, user: User, organization_id: UUID
) -> None:
    if user.is_superuser:
        return
    m = (
        await session.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.organization_id == organization_id,
            )
        )
    ).scalar_one_or_none()
    if m is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization.",
        )


@router.get("/orgs/{organization_id}/analytics/heatmap")
async def get_heatmap(
    organization_id: UUID,
    days: int = Query(90, ge=1, le=365),
    channel: str | None = Query(None),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    await _require_member(session, user, organization_id)
    cutoff = datetime.now(timezone.utc) - timedelta(days=int(days))

    stmt = select(Touchpoint.occurred_at, Touchpoint.channel).where(
        Touchpoint.organization_id == organization_id,
        Touchpoint.occurred_at >= cutoff,
    )
    if channel:
        stmt = stmt.where(Touchpoint.channel == channel)
    rows = (await session.execute(stmt)).all()

    grid = [[0 for _ in range(24)] for _ in range(7)]
    total = 0
    mx = 0
    for occurred_at, _ch in rows:
        # ``occurred_at`` is timezone-aware; weekday(): Mon=0..Sun=6
        wd = occurred_at.weekday()
        hr = occurred_at.hour
        grid[wd][hr] += 1
        total += 1
        if grid[wd][hr] > mx:
            mx = grid[wd][hr]

    return {
        "organization_id": str(organization_id),
        "window_days": days,
        "channel": channel,
        "total": total,
        "max": mx,
        "grid": grid,
    }
