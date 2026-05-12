"""Cost ledger reporting (Phase 11.1).

The CostLedger table from #120 collects per-call provider spend.
Until now there was no surface to read it back. This adds the
totals endpoint the /costs admin dashboard needs.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.ops import CostLedger
from app.models.organization import OrganizationMembership
from app.models.user import User


router = APIRouter(prefix="/costs", tags=["costs"])


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


@router.get("/totals")
async def cost_totals(
    organization_id: UUID,
    days: int = Query(30, ge=1, le=365),
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Returns total USD spend over the last N days for the org,
    broken down by kind + provider, with delta-vs-previous-period.
    """
    await _require_member(db, user, organization_id)

    now = datetime.now(tz=timezone.utc)
    cur_start = now - timedelta(days=days)
    prev_start = cur_start - timedelta(days=days)

    # Two windows: current + previous (same length)
    async def _window_breakdown(start: datetime, end: datetime) -> dict:
        # Total
        total = (
            await db.execute(
                select(func.coalesce(func.sum(CostLedger.amount_usd), 0.0)).where(
                    CostLedger.organization_id == organization_id,
                    CostLedger.occurred_at >= start,
                    CostLedger.occurred_at < end,
                )
            )
        ).scalar_one()

        by_kind_rows = (
            await db.execute(
                select(
                    CostLedger.kind,
                    func.coalesce(func.sum(CostLedger.amount_usd), 0.0),
                )
                .where(
                    CostLedger.organization_id == organization_id,
                    CostLedger.occurred_at >= start,
                    CostLedger.occurred_at < end,
                )
                .group_by(CostLedger.kind)
            )
        ).all()
        by_provider_rows = (
            await db.execute(
                select(
                    CostLedger.provider,
                    func.coalesce(func.sum(CostLedger.amount_usd), 0.0),
                )
                .where(
                    CostLedger.organization_id == organization_id,
                    CostLedger.occurred_at >= start,
                    CostLedger.occurred_at < end,
                )
                .group_by(CostLedger.provider)
            )
        ).all()

        return {
            "total_usd": round(float(total or 0.0), 4),
            "by_kind": {
                str(k): round(float(v or 0.0), 4) for k, v in by_kind_rows
            },
            "by_provider": {
                str(p): round(float(v or 0.0), 4) for p, v in by_provider_rows
            },
        }

    current = await _window_breakdown(cur_start, now)
    previous = await _window_breakdown(prev_start, cur_start)

    def _pct(a: float, b: float) -> float | None:
        if b == 0:
            return None
        return round(((a - b) / b) * 100.0, 1)

    return {
        "organization_id": str(organization_id),
        "days": days,
        "current": current,
        "previous": previous,
        "delta_pct": {
            "total_usd": _pct(current["total_usd"], previous["total_usd"]),
        },
    }


@router.get("/recent")
async def cost_recent(
    organization_id: UUID,
    limit: int = Query(50, ge=1, le=500),
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Returns the N most-recent CostLedger rows for drill-down."""
    await _require_member(db, user, organization_id)
    rows = (
        (
            await db.execute(
                select(CostLedger)
                .where(CostLedger.organization_id == organization_id)
                .order_by(CostLedger.occurred_at.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return {
        "organization_id": str(organization_id),
        "items": [
            {
                "id": str(r.id),
                "provider": r.provider,
                "provider_resource": r.provider_resource,
                "kind": r.kind,
                "amount_usd": float(r.amount_usd),
                "units": float(r.units) if r.units is not None else None,
                "units_kind": r.units_kind,
                "occurred_at": r.occurred_at.isoformat(),
            }
            for r in rows
        ],
    }
