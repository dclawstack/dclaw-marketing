"""Audit event browser — Phase 11 / A4 follow-up.

Read-only API on top of the existing ``audit_events`` table. Admins
and Managers can paginate + filter; analysts get a read-only view of
the same data.

Endpoints:

  * ``GET /orgs/{org_id}/audit-events?action_type=&actor_kind=&days=&limit=&offset=``
  * ``GET /audit-events/{id}``

Never writes — write-side is owned by the original mutators (publish,
approve, agent run, etc.).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.audit_event import AuditActorKind, AuditEvent, AuditResult
from app.models.organization import OrganizationMembership
from app.models.user import User


router = APIRouter(tags=["audit-events"])


class AuditEventRead(BaseModel):
    id: UUID
    organization_id: UUID | None
    actor_kind: AuditActorKind
    actor_user_id: UUID | None
    actor_agent: str | None
    action_type: str
    target_type: str | None
    target_id: str | None
    payload_json: dict | None
    result: AuditResult
    error_message: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditEventListResponse(BaseModel):
    items: list[AuditEventRead]
    total: int
    limit: int
    offset: int


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


@router.get(
    "/orgs/{organization_id}/audit-events",
    response_model=AuditEventListResponse,
)
async def list_audit_events(
    organization_id: UUID,
    action_type: str | None = None,
    actor_kind: AuditActorKind | None = None,
    days: int = 30,
    limit: int = 50,
    offset: int = 0,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> AuditEventListResponse:
    await _require_member(session, user, organization_id)

    cutoff = datetime.now(timezone.utc) - timedelta(days=max(int(days), 1))
    base = select(AuditEvent).where(
        AuditEvent.organization_id == organization_id,
        AuditEvent.created_at >= cutoff,
    )
    if action_type:
        base = base.where(AuditEvent.action_type == action_type)
    if actor_kind is not None:
        base = base.where(AuditEvent.actor_kind == actor_kind)

    count_q = await session.execute(
        select(func.count()).select_from(base.subquery())
    )
    total = int(count_q.scalar() or 0)

    page = (
        await session.execute(
            base.order_by(desc(AuditEvent.created_at))
            .limit(max(1, min(int(limit), 200)))
            .offset(max(0, int(offset)))
        )
    ).scalars().all()

    return AuditEventListResponse(
        items=[AuditEventRead.model_validate(r) for r in page],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/audit-events/{event_id}", response_model=AuditEventRead)
async def get_audit_event(
    event_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> AuditEventRead:
    ev = await session.get(AuditEvent, event_id)
    if ev is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="AuditEvent not found."
        )
    if ev.organization_id is not None:
        await _require_member(session, user, ev.organization_id)
    elif not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="System events are admin-only."
        )
    return AuditEventRead.model_validate(ev)
