"""Quotas API (Phase 11 / I1).

Read-only browse of live ``QuotaCounter`` rows for the dashboard.
Write side is owned by the sliding-window writer in
``app.services.quota``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.ops import QuotaCounter
from app.models.organization import OrganizationMembership
from app.models.user import User


router = APIRouter(prefix="/quotas", tags=["quotas"])


class QuotaCounterRead(BaseModel):
    id: UUID
    organization_id: UUID
    channel: str
    window_start: datetime
    window_seconds: int
    limit: int
    count: int
    last_used_at: datetime | None
    pct_used: float
    is_breaker: bool

    class Config:
        from_attributes = True


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
            status_code=status.HTTP_403_FORBIDDEN, detail="Not a member."
        )


@router.get("", response_model=list[QuotaCounterRead])
async def list_quotas(
    organization_id: UUID,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
) -> list[QuotaCounterRead]:
    """Returns active QuotaCounter rows (windows that overlap "now")
    for the given Org, freshest window first."""
    await _require_member(db, user, organization_id)

    now = datetime.now(tz=timezone.utc)
    rows = (
        (
            await db.execute(
                select(QuotaCounter)
                .where(QuotaCounter.organization_id == organization_id)
                .order_by(desc(QuotaCounter.window_start))
                .limit(200)
            )
        )
        .scalars()
        .all()
    )

    out: list[QuotaCounterRead] = []
    for r in rows:
        window_end = r.window_start.replace(
            tzinfo=timezone.utc
        ) + _duration(r.window_seconds)
        if window_end < now:
            continue  # window already closed
        pct = (r.count / r.limit) * 100.0 if r.limit > 0 else 0.0
        out.append(
            QuotaCounterRead(
                id=r.id,
                organization_id=r.organization_id,
                channel=r.channel,
                window_start=r.window_start,
                window_seconds=r.window_seconds,
                limit=r.limit,
                count=r.count,
                last_used_at=r.last_used_at,
                pct_used=round(pct, 1),
                is_breaker=r.channel.endswith(":breaker"),
            )
        )
    return out


def _duration(seconds: int):
    from datetime import timedelta

    return timedelta(seconds=int(seconds))
