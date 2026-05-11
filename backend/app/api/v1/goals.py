"""Org-level goals + constraints + autonomy-posture configuration (Q5).

Free-form JSON blobs. The Conductor + role-Agents pull from these
to plan briefs and constrain their tool use.

Shape suggestions (not enforced — agents tolerate missing fields):

    goals_json = {
        "objectives": ["leads", "revenue", "awareness"],
        "north_star_metric": "monthly_qualified_leads",
        "target_quarterly_value": 500,
        "icps": ["b2b-saas-cmo", "mid-market-marketing-ops"],
        "channels_of_interest": ["linkedin", "x", "seo", "email"]
    }

    constraints_json = {
        "brand_safety_lines": ["no political content", "no competitor names"],
        "monthly_budget_usd": 5000,
        "max_daily_posts": 6,
        "approval_required_for": ["any external publish", "spend > $200/day"]
    }

    autonomy_posture_json = {
        "social_post": "hard_gate",
        "draft_email": "soft_gate",
        "internal_research": "autopilot",
        "send_email_bulk": "hard_gate"
    }
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.organization import Organization, OrganizationMembership, OrganizationRole
from app.models.user import User


router = APIRouter(prefix="/orgs/{org_id}/goals", tags=["goals"])


class GoalsRead(BaseModel):
    organization_id: UUID
    goals: dict[str, Any] | None
    constraints: dict[str, Any] | None
    autonomy_posture: dict[str, Any] | None


class GoalsUpdate(BaseModel):
    """All fields optional — PATCH-style; pass only what you want
    to change. Pass {} to clear a field (vs. omitting to leave alone).
    """
    goals: dict[str, Any] | None = None
    constraints: dict[str, Any] | None = None
    autonomy_posture: dict[str, Any] | None = None


async def _require_member(
    session: AsyncSession,
    user: User,
    org_id: UUID,
    *,
    write: bool = False,
) -> None:
    if user.is_superuser:
        return
    result = await session.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == org_id,
        )
    )
    m = result.scalar_one_or_none()
    if m is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member.")
    if write and m.role not in (OrganizationRole.admin, OrganizationRole.manager):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin or manager can change goals.",
        )


@router.get("", response_model=GoalsRead)
async def get_goals(
    org_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> GoalsRead:
    await _require_member(session, user, org_id)
    org = await session.get(Organization, org_id)
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Org not found.")
    return GoalsRead(
        organization_id=org.id,
        goals=org.goals_json,
        constraints=org.constraints_json,
        autonomy_posture=org.autonomy_posture_json,
    )


@router.put("", response_model=GoalsRead)
async def update_goals(
    org_id: UUID,
    body: GoalsUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> GoalsRead:
    await _require_member(session, user, org_id, write=True)
    org = await session.get(Organization, org_id)
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Org not found.")

    data = body.model_dump(exclude_unset=True)
    if "goals" in data:
        org.goals_json = data["goals"]
    if "constraints" in data:
        org.constraints_json = data["constraints"]
    if "autonomy_posture" in data:
        org.autonomy_posture_json = data["autonomy_posture"]

    await session.flush()
    await session.commit()
    await session.refresh(org)

    return GoalsRead(
        organization_id=org.id,
        goals=org.goals_json,
        constraints=org.constraints_json,
        autonomy_posture=org.autonomy_posture_json,
    )
