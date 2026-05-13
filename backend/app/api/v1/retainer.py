"""Per-Org retainer burn-down (SP3-22).

The constraints_json on Organization carries:
  {
    "retainer": {
      "monthly_hours_cap": 40,
      "monthly_budget_usd": 5000
    }
  }

This endpoint sums TimeEntry hours + (hours * rate) for the current
calendar month and reports the burn-down state.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.ops import TimeEntry
from app.models.organization import Organization, OrganizationMembership
from app.models.user import User


router = APIRouter(tags=["retainer"])


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


@router.get("/orgs/{organization_id}/retainer-status")
async def retainer_status(
    organization_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    await _require_member(session, user, organization_id)
    org = await session.get(Organization, organization_id)
    if org is None:
        raise HTTPException(status_code=404, detail="Organization not found.")

    retainer = (org.constraints_json or {}).get("retainer") or {}
    hours_cap = retainer.get("monthly_hours_cap")
    budget_cap = retainer.get("monthly_budget_usd")

    now = datetime.now(timezone.utc)
    month_start = date(year=now.year, month=now.month, day=1)

    # SUM(duration_seconds) over current month
    secs_q = await session.execute(
        select(func.coalesce(func.sum(TimeEntry.duration_seconds), 0)).where(
            TimeEntry.organization_id == organization_id,
            TimeEntry.started_at >= month_start,
        )
    )
    seconds_logged = int(secs_q.scalar() or 0)
    hours_logged = round(seconds_logged / 3600.0, 2)

    # Approximate spend: hours × rate where set, billable only.
    rev_q = await session.execute(
        select(
            func.coalesce(
                func.sum(
                    TimeEntry.rate_usd_per_hour
                    * (TimeEntry.duration_seconds / 3600.0)
                ),
                0.0,
            )
        ).where(
            TimeEntry.organization_id == organization_id,
            TimeEntry.started_at >= month_start,
            TimeEntry.billable.is_(True),
            TimeEntry.rate_usd_per_hour.is_not(None),
        )
    )
    billable_usd = float(rev_q.scalar() or 0.0)

    def _pct(used: float, cap: float | None) -> float | None:
        if cap is None or cap <= 0:
            return None
        return round((used / cap) * 100.0, 1)

    return {
        "organization_id": str(organization_id),
        "month_start": month_start.isoformat(),
        "hours": {
            "used": hours_logged,
            "cap": hours_cap,
            "pct_used": _pct(hours_logged, hours_cap),
            "remaining": (
                round(max(0.0, hours_cap - hours_logged), 2)
                if hours_cap is not None
                else None
            ),
        },
        "budget_usd": {
            "used": round(billable_usd, 2),
            "cap": budget_cap,
            "pct_used": _pct(billable_usd, budget_cap),
            "remaining": (
                round(max(0.0, budget_cap - billable_usd), 2)
                if budget_cap is not None
                else None
            ),
        },
    }
