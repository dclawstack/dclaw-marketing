"""Sprint-4 agent-runtime API.

  POST /agents/role/{name}/run        — S4-A3 generic role-agent runner
  POST /approvals/{id}/sign-off       — S4-A5 4-eye additional approver
  GET  /agents/runs/{request_id}/trace — S4-A6 reasoning-trace replay
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.roles import ROLE_SYSTEM_PROMPTS, run_role
from app.auth import current_active_user
from app.core.database import get_db
from app.models.approval_request import ApprovalRequest, ApprovalStatus
from app.models.model_call_log import ModelCallLog
from app.models.user import User


router = APIRouter(tags=["agent-runtime"])


# ---------- A3: generic role-agent runner -----------------------------------


class RoleRunBody(BaseModel):
    organization_id: UUID | None = None
    brief: str
    max_tokens: int | None = 800
    request_id: str | None = None


class RoleRunOut(BaseModel):
    agent: str
    request_id: str
    text: str
    model_id: str | None
    resolved_by: str | None


@router.post("/agents/role/{agent}/run", response_model=RoleRunOut)
async def role_run(
    agent: str,
    body: RoleRunBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
) -> RoleRunOut:
    if agent not in ROLE_SYSTEM_PROMPTS:
        raise HTTPException(status_code=404, detail=f"Unknown role agent '{agent}'.")
    if not body.brief.strip():
        raise HTTPException(status_code=400, detail="brief is required")
    rr = await run_role(
        db=db,
        agent=agent,
        brief=body.brief,
        org_id=body.organization_id,
        user_id=user.id,
        request_id=body.request_id,
        max_tokens=body.max_tokens or 800,
    )
    return RoleRunOut(
        agent=rr.agent,
        request_id=rr.request_id,
        text=rr.text,
        model_id=rr.model_id,
        resolved_by=rr.resolved_by,
    )


# ---------- A5: 4-eye approval sign-off -------------------------------------


class SignOffOut(BaseModel):
    id: UUID
    status: ApprovalStatus
    approvers: list[str]
    approvers_required: int


@router.post("/approvals/{approval_id}/sign-off", response_model=SignOffOut)
async def sign_off(
    approval_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
) -> SignOffOut:
    """Add this user as an approver. When the count reaches
    `approvers_required`, the approval flips to `approved`."""
    a = await db.get(ApprovalRequest, approval_id)
    if a is None:
        raise HTTPException(status_code=404, detail="Approval not found.")
    if a.status not in (ApprovalStatus.pending,):
        raise HTTPException(
            status_code=400, detail=f"Approval is {a.status.value}; cannot sign off."
        )
    approvers: list[str] = list(a.approvers_user_ids_json or [])
    if str(user.id) in approvers:
        raise HTTPException(status_code=400, detail="Already signed off.")
    approvers.append(str(user.id))
    a.approvers_user_ids_json = approvers
    if len(approvers) >= a.approvers_required:
        a.status = ApprovalStatus.approved
        a.decided_by_user_id = user.id
    await db.commit()
    await db.refresh(a)
    return SignOffOut(
        id=a.id,
        status=a.status,
        approvers=approvers,
        approvers_required=a.approvers_required,
    )


# ---------- A6: reasoning-trace replay --------------------------------------


class TraceRow(BaseModel):
    started_at: str
    component: str
    model_entry_id: UUID
    duration_ms: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    status: str
    error_message: str | None


@router.get("/agents/runs/{request_id}/trace", response_model=list[TraceRow])
async def run_trace(
    request_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
) -> list[TraceRow]:
    """Return the chronological model-call trail for a given request_id."""
    rows = (
        await db.execute(
            select(ModelCallLog)
            .where(ModelCallLog.request_id == request_id)
            .order_by(ModelCallLog.started_at)
        )
    ).scalars().all()
    return [
        TraceRow(
            started_at=r.started_at.isoformat(),
            component=r.caller_component,
            model_entry_id=r.model_entry_id,
            duration_ms=r.duration_ms,
            input_tokens=r.input_tokens,
            output_tokens=r.output_tokens,
            cost_usd=r.cost_usd,
            status=r.status.value,
            error_message=r.error_message,
        )
        for r in rows
    ]
