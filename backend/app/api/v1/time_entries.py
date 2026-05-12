"""Time-tracking API (Phase 10.5).

Surfaces the existing ``TimeEntry`` model (#120) as CRUD + a totals
endpoint that powers the retainer burn-down chart on the agency-ops
dashboard.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.ops import TimeEntry
from app.models.organization import OrganizationMembership, OrganizationRole
from app.models.user import User


router = APIRouter(prefix="/time-entries", tags=["time-entries"])


# ---------- schemas ----------------------------------------------------


class TimeEntryCreate(BaseModel):
    organization_id: UUID
    project_id: UUID | None = None
    campaign_id: UUID | None = None
    description: str | None = Field(default=None, max_length=4000)
    started_at: datetime
    ended_at: datetime | None = None
    duration_seconds: int | None = Field(default=None, ge=1, le=24 * 3600)
    billable: bool = True
    rate_usd_per_hour: float | None = None


class TimeEntryUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=4000)
    ended_at: datetime | None = None
    duration_seconds: int | None = Field(default=None, ge=1, le=24 * 3600)
    billable: bool | None = None
    rate_usd_per_hour: float | None = None


class TimeEntryRead(BaseModel):
    id: UUID
    organization_id: UUID
    project_id: UUID | None
    campaign_id: UUID | None
    user_id: UUID
    description: str | None
    started_at: datetime
    ended_at: datetime | None
    duration_seconds: int | None
    billable: bool
    rate_usd_per_hour: float | None

    model_config = ConfigDict(from_attributes=True)


# ---------- helpers ----------------------------------------------------


async def _require_member(
    session: AsyncSession, user: User, org_id: UUID
) -> OrganizationMembership | None:
    if user.is_superuser:
        return None
    result = await session.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == org_id,
        )
    )
    m = result.scalar_one_or_none()
    if m is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not a member."
        )
    return m


def _derive_duration(start: datetime, end: datetime | None, explicit: int | None) -> int | None:
    if explicit is not None:
        return int(explicit)
    if end is None:
        return None
    return int((end - start).total_seconds())


# ---------- routes -----------------------------------------------------


@router.post("", response_model=TimeEntryRead, status_code=status.HTTP_201_CREATED)
async def create_time_entry(
    body: TimeEntryCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> TimeEntryRead:
    await _require_member(session, user, body.organization_id)
    if body.ended_at and body.ended_at <= body.started_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ended_at must be after started_at",
        )
    entry = TimeEntry(
        organization_id=body.organization_id,
        project_id=body.project_id,
        campaign_id=body.campaign_id,
        user_id=user.id,
        description=body.description,
        started_at=body.started_at,
        ended_at=body.ended_at,
        duration_seconds=_derive_duration(body.started_at, body.ended_at, body.duration_seconds),
        billable=body.billable,
        rate_usd_per_hour=body.rate_usd_per_hour,
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    return TimeEntryRead.model_validate(entry)


@router.get("", response_model=list[TimeEntryRead])
async def list_time_entries(
    organization_id: UUID,
    project_id: UUID | None = None,
    campaign_id: UUID | None = None,
    user_id: UUID | None = None,
    days: int = Query(30, ge=1, le=365),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> list[TimeEntryRead]:
    await _require_member(session, user, organization_id)
    since = datetime.now(tz=timezone.utc) - timedelta(days=days)
    stmt = (
        select(TimeEntry)
        .where(
            TimeEntry.organization_id == organization_id,
            TimeEntry.started_at >= since,
        )
        .order_by(TimeEntry.started_at.desc())
    )
    if project_id:
        stmt = stmt.where(TimeEntry.project_id == project_id)
    if campaign_id:
        stmt = stmt.where(TimeEntry.campaign_id == campaign_id)
    if user_id:
        stmt = stmt.where(TimeEntry.user_id == user_id)
    rows = (await session.execute(stmt)).scalars().all()
    return [TimeEntryRead.model_validate(r) for r in rows]


@router.patch("/{entry_id}", response_model=TimeEntryRead)
async def update_time_entry(
    entry_id: UUID,
    body: TimeEntryUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> TimeEntryRead:
    entry = await session.get(TimeEntry, entry_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Time entry not found."
        )
    await _require_member(session, user, entry.organization_id)
    # Only the owner or an admin can edit.
    if entry.user_id != user.id and not user.is_superuser:
        # Check Org admin role
        membership = await session.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.organization_id == entry.organization_id,
            )
        )
        m = membership.scalar_one_or_none()
        if m is None or m.role not in (OrganizationRole.admin, OrganizationRole.manager):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the owner or an Org admin/manager can edit this entry.",
            )

    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(entry, k, v)
    # Recompute duration_seconds if needed
    if "ended_at" in data or "duration_seconds" in data:
        entry.duration_seconds = _derive_duration(
            entry.started_at, entry.ended_at, entry.duration_seconds
        )

    await session.commit()
    await session.refresh(entry)
    return TimeEntryRead.model_validate(entry)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_time_entry(
    entry_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    entry = await session.get(TimeEntry, entry_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Time entry not found."
        )
    if entry.user_id != user.id and not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the owner can delete a time entry.",
        )
    await session.delete(entry)
    await session.commit()


@router.get("/totals")
async def time_entry_totals(
    organization_id: UUID,
    days: int = Query(30, ge=1, le=365),
    group_by: str = Query("project", pattern="^(project|campaign|user)$"),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Aggregates billable + non-billable hours over the window.

    Returns a per-bucket breakdown plus org totals — feeds the
    retainer-burn-down chart.
    """
    await _require_member(session, user, organization_id)
    since = datetime.now(tz=timezone.utc) - timedelta(days=days)

    bucket_col = {
        "project": TimeEntry.project_id,
        "campaign": TimeEntry.campaign_id,
        "user": TimeEntry.user_id,
    }[group_by]

    rows = (
        await session.execute(
            select(
                bucket_col,
                TimeEntry.billable,
                func.coalesce(func.sum(TimeEntry.duration_seconds), 0),
                func.coalesce(
                    func.sum(
                        TimeEntry.duration_seconds
                        * func.coalesce(TimeEntry.rate_usd_per_hour, 0.0)
                        / 3600.0
                    ),
                    0.0,
                ),
            )
            .where(
                TimeEntry.organization_id == organization_id,
                TimeEntry.started_at >= since,
            )
            .group_by(bucket_col, TimeEntry.billable)
        )
    ).all()

    by_bucket: dict[str, dict] = {}
    org_seconds = 0
    org_billable_seconds = 0
    org_revenue = 0.0
    for bucket, billable, seconds, revenue in rows:
        key = str(bucket) if bucket is not None else "(unassigned)"
        b = by_bucket.setdefault(
            key,
            {
                "seconds": 0,
                "billable_seconds": 0,
                "revenue_usd": 0.0,
            },
        )
        s = int(seconds or 0)
        r = float(revenue or 0.0)
        b["seconds"] += s
        org_seconds += s
        if billable:
            b["billable_seconds"] += s
            org_billable_seconds += s
            b["revenue_usd"] += r
            org_revenue += r

    return {
        "organization_id": str(organization_id),
        "days": days,
        "group_by": group_by,
        "buckets": by_bucket,
        "org_totals": {
            "seconds": org_seconds,
            "hours": round(org_seconds / 3600.0, 2),
            "billable_seconds": org_billable_seconds,
            "billable_hours": round(org_billable_seconds / 3600.0, 2),
            "revenue_usd": round(org_revenue, 2),
        },
    }
