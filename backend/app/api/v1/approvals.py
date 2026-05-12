"""Approval Inbox API — the human's primary UI surface for Hard-gate
items per PLAN-v1.2 §v2.0 §5.

Routes:
- POST /approvals          — agent or human creates a pending request
- GET  /approvals          — list pending (or filter by status)
- GET  /approvals/{id}     — fetch one
- POST /approvals/{id}/approve   — flip to approved + AuditEvent
- POST /approvals/{id}/reject    — flip to rejected + AuditEvent
- POST /approvals/{id}/cancel    — requester pulls back
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.approval_request import ApprovalRequest, ApprovalStatus
from app.models.audit_event import AuditActorKind
from app.models.organization import OrganizationMembership, OrganizationRole
from app.models.user import User
from app.services.audit import write_audit_event


router = APIRouter(prefix="/approvals", tags=["approvals"])


# ---------- schemas -----------------------------------------------------

class ApprovalRequestCreate(BaseModel):
    organization_id: UUID | None = None
    project_id: UUID | None = None
    action_type: str = Field(min_length=1, max_length=128)
    target_type: str | None = None
    target_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    summary: str | None = None
    requested_by_agent: str | None = None
    expires_at: datetime | None = None


class ApprovalRequestRead(BaseModel):
    id: UUID
    organization_id: UUID | None
    project_id: UUID | None
    requested_by_user_id: UUID | None
    requested_by_agent: str | None
    action_type: str
    target_type: str | None
    target_id: str | None
    payload_json: dict | None
    summary: str | None
    status: ApprovalStatus
    decided_by_user_id: UUID | None
    decided_at: datetime | None
    decision_reason: str | None
    expires_at: datetime | None

    class Config:
        from_attributes = True


class ApprovalDecisionIn(BaseModel):
    reason: str | None = None


# ---------- helpers -----------------------------------------------------

async def _user_can_decide(
    session: AsyncSession, user: User, request: ApprovalRequest
) -> None:
    """Check the user can decide on this approval.

    Rules: superuser always can; org admin/manager/reviewer can within
    their Org; the requester themselves cannot approve their own
    request (4-eye rule).
    """
    if user.is_superuser:
        return
    if request.requested_by_user_id == user.id and request.requested_by_user_id is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot decide on your own approval request.",
        )
    if request.organization_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No org context on this approval.",
        )
    result = await session.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == request.organization_id,
            OrganizationMembership.role.in_(
                (OrganizationRole.admin, OrganizationRole.manager, OrganizationRole.reviewer)
            ),
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role admin / manager / reviewer required to decide.",
        )


async def _user_can_view_org(
    session: AsyncSession, user: User, organization_id: UUID | None
) -> None:
    if user.is_superuser or organization_id is None:
        return
    result = await session.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == organization_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization.",
        )


# ---------- routes ------------------------------------------------------

@router.post("", response_model=ApprovalRequestRead, status_code=status.HTTP_201_CREATED)
async def create_approval(
    body: ApprovalRequestCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> ApprovalRequest:
    """Create a new pending approval. Both humans and agents (via API
    keys, future) write through this same endpoint.
    """
    await _user_can_view_org(session, user, body.organization_id)

    approval = ApprovalRequest(
        organization_id=body.organization_id,
        project_id=body.project_id,
        requested_by_user_id=user.id if not body.requested_by_agent else None,
        requested_by_agent=body.requested_by_agent,
        action_type=body.action_type,
        target_type=body.target_type,
        target_id=body.target_id,
        payload_json=body.payload,
        summary=body.summary,
        expires_at=body.expires_at,
        status=ApprovalStatus.pending,
    )
    session.add(approval)
    await session.flush()
    await session.commit()
    await session.refresh(approval)
    return approval


@router.get("", response_model=list[ApprovalRequestRead])
async def list_approvals(
    organization_id: UUID | None = None,
    approval_status: ApprovalStatus | None = None,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
    limit: int = 50,
) -> list[ApprovalRequest]:
    """List approvals visible to the current user, optionally filtered.

    Visibility: superuser sees all; org members see their org's; with
    no org filter, non-superusers see only requests for Orgs they
    belong to.
    """
    stmt = select(ApprovalRequest).order_by(ApprovalRequest.created_at.desc()).limit(limit)
    if approval_status is not None:
        stmt = stmt.where(ApprovalRequest.status == approval_status)

    if user.is_superuser:
        if organization_id is not None:
            stmt = stmt.where(ApprovalRequest.organization_id == organization_id)
    else:
        # Scope to user's Orgs
        mem_q = await session.execute(
            select(OrganizationMembership.organization_id).where(
                OrganizationMembership.user_id == user.id
            )
        )
        my_orgs = [o[0] for o in mem_q.all()]
        if organization_id is not None:
            if organization_id not in my_orgs:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member.")
            stmt = stmt.where(ApprovalRequest.organization_id == organization_id)
        else:
            if not my_orgs:
                return []
            stmt = stmt.where(ApprovalRequest.organization_id.in_(my_orgs))

    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/{approval_id}", response_model=ApprovalRequestRead)
async def get_approval(
    approval_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> ApprovalRequest:
    approval = await session.get(ApprovalRequest, approval_id)
    if approval is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    await _user_can_view_org(session, user, approval.organization_id)
    return approval


@router.post("/{approval_id}/approve", response_model=ApprovalRequestRead)
async def approve(
    approval_id: UUID,
    body: ApprovalDecisionIn,
    request: Request,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> ApprovalRequest:
    approval = await session.get(ApprovalRequest, approval_id)
    if approval is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    if approval.status != ApprovalStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Approval is {approval.status.value}, not pending.",
        )

    await _user_can_decide(session, user, approval)

    approval.status = ApprovalStatus.approved
    approval.decided_by_user_id = user.id
    approval.decided_at = datetime.now(timezone.utc)
    approval.decision_reason = body.reason
    await session.flush()

    await write_audit_event(
        session,
        action_type="approval.approved",
        organization_id=approval.organization_id,
        actor_kind=AuditActorKind.user,
        actor_user_id=user.id,
        target_type="approval_request",
        target_id=str(approval.id),
        payload={"reason": body.reason, "approved_action": approval.action_type},
        approval_request_id=approval.id,
        request=request,
    )
    await session.commit()
    await session.refresh(approval)

    # Phase 7.2 — if this approval was for an email send, enqueue the
    # delivery task now. We do this AFTER commit so the worker sees the
    # row in its own transaction.
    if approval.action_type == "send_email":
        try:
            from app.worker.tasks.email_send import deliver_approved_email

            deliver_approved_email.delay(str(approval.id))
        except Exception:  # pragma: no cover — celery broker down
            # Best-effort: the approval is still recorded; an admin can
            # retrigger by re-enqueueing manually.
            pass

    return approval


@router.post("/{approval_id}/reject", response_model=ApprovalRequestRead)
async def reject(
    approval_id: UUID,
    body: ApprovalDecisionIn,
    request: Request,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> ApprovalRequest:
    approval = await session.get(ApprovalRequest, approval_id)
    if approval is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    if approval.status != ApprovalStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Approval is {approval.status.value}, not pending.",
        )

    await _user_can_decide(session, user, approval)

    approval.status = ApprovalStatus.rejected
    approval.decided_by_user_id = user.id
    approval.decided_at = datetime.now(timezone.utc)
    approval.decision_reason = body.reason
    await session.flush()

    await write_audit_event(
        session,
        action_type="approval.rejected",
        organization_id=approval.organization_id,
        actor_kind=AuditActorKind.user,
        actor_user_id=user.id,
        target_type="approval_request",
        target_id=str(approval.id),
        payload={"reason": body.reason, "rejected_action": approval.action_type},
        approval_request_id=approval.id,
        request=request,
    )
    await session.commit()
    await session.refresh(approval)
    return approval


@router.post("/{approval_id}/cancel", response_model=ApprovalRequestRead)
async def cancel(
    approval_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> ApprovalRequest:
    """Requester pulls back their own approval before a decision."""
    approval = await session.get(ApprovalRequest, approval_id)
    if approval is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    if approval.status != ApprovalStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Approval is {approval.status.value}, cannot cancel.",
        )
    if approval.requested_by_user_id != user.id and not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the requester (or admin) can cancel.",
        )
    approval.status = ApprovalStatus.canceled
    approval.decided_at = datetime.now(timezone.utc)
    await session.flush()
    await session.commit()
    await session.refresh(approval)
    return approval
