"""Agents API — kick off agent runs.

For v0.1 only the Creatives Agent is wired. Others (SMM, SEO, Paid
Media, Analyst) follow the same shape and land in Phase 3.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.creatives import generate_social_posts
from app.auth import current_active_user
from app.core.database import get_db
from app.models.organization import OrganizationMembership, OrganizationRole
from app.models.user import User


router = APIRouter(prefix="/agents", tags=["agents"])


class CreativesGenerateRequest(BaseModel):
    organization_id: UUID
    project_id: UUID | None = None
    brief: str = Field(min_length=4, max_length=8000)
    n_variants: int = Field(default=3, ge=1, le=10)
    channel: str = Field(default="linkedin", min_length=1, max_length=64)


class CreativesGenerateResultItem(BaseModel):
    variant: str
    approval_request_id: str


class CreativesGenerateResponse(BaseModel):
    organization_id: UUID
    project_id: UUID | None
    channel: str
    n_variants: int
    results: list[CreativesGenerateResultItem]


async def _user_in_org(
    session: AsyncSession,
    user: User,
    org_id: UUID,
    *,
    allowed_roles: tuple[OrganizationRole, ...],
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
    if m.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role {m.role.value} cannot run this agent.",
        )


_CREATIVES_ROLES = (
    OrganizationRole.admin,
    OrganizationRole.manager,
    OrganizationRole.creatives,
    OrganizationRole.social_media_manager,
)


@router.post("/creatives/generate", response_model=CreativesGenerateResponse)
async def creatives_generate(
    body: CreativesGenerateRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> CreativesGenerateResponse:
    """Runs the Creatives Agent. Output lands in the Approval Inbox
    (Hard-gate; the agent itself never publishes).
    """
    await _user_in_org(session, user, body.organization_id, allowed_roles=_CREATIVES_ROLES)

    results = await generate_social_posts(
        session=session,
        organization_id=body.organization_id,
        project_id=body.project_id,
        brief=body.brief,
        n_variants=body.n_variants,
        channel=body.channel,
        requesting_user_id=user.id,
    )

    return CreativesGenerateResponse(
        organization_id=body.organization_id,
        project_id=body.project_id,
        channel=body.channel,
        n_variants=body.n_variants,
        results=[CreativesGenerateResultItem(**r) for r in results],
    )
