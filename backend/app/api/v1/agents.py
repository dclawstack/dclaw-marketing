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
from app.models.approval_request import ApprovalRequest, ApprovalStatus
from app.models.organization import OrganizationMembership, OrganizationRole
from app.models.user import User
from app.services.image_gen import generate_image


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


# ---------- Phase 3.1 — image generation ------------------------------


class ImagesGenerateRequest(BaseModel):
    organization_id: UUID
    project_id: UUID | None = None
    prompt: str = Field(min_length=4, max_length=4000)
    n: int = Field(default=3, ge=1, le=8)
    aspect_ratio: str = Field(default="1:1", pattern=r"^(1:1|16:9|9:16|4:5)$")


class ImagesGenerateResultItem(BaseModel):
    url: str
    provider: str
    approval_request_id: str


class ImagesGenerateResponse(BaseModel):
    organization_id: UUID
    project_id: UUID | None
    prompt: str
    n: int
    aspect_ratio: str
    results: list[ImagesGenerateResultItem]


@router.post("/creatives/images", response_model=ImagesGenerateResponse)
async def creatives_generate_images(
    body: ImagesGenerateRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> ImagesGenerateResponse:
    """Generates image variants and files each as a pending
    ApprovalRequest (Hard-gate; the agent itself never publishes).

    Uses Replicate when ``REPLICATE_API_TOKEN`` is set, otherwise the
    deterministic SVG stub — both feed the same approval flow.
    """
    await _user_in_org(
        session, user, body.organization_id, allowed_roles=_CREATIVES_ROLES
    )

    images = await generate_image(
        body.prompt, n=body.n, aspect_ratio=body.aspect_ratio
    )

    results: list[ImagesGenerateResultItem] = []
    for img in images:
        ar = ApprovalRequest(
            organization_id=body.organization_id,
            project_id=body.project_id,
            requested_by_user_id=user.id,
            requested_by_agent="creatives_agent_v1",
            action_type="publish_image_asset",
            target_type="image_draft",
            payload_json={
                "prompt": body.prompt,
                "url": img.url,
                "provider": img.provider.value,
                "aspect_ratio": body.aspect_ratio,
                "seed": img.seed,
            },
            summary=(
                f"Image draft ({img.provider.value}, {body.aspect_ratio}): "
                f"{body.prompt[:80]}{'…' if len(body.prompt) > 80 else ''}"
            ),
            status=ApprovalStatus.pending,
        )
        session.add(ar)
        await session.flush()
        results.append(
            ImagesGenerateResultItem(
                url=img.url,
                provider=img.provider.value,
                approval_request_id=str(ar.id),
            )
        )

    await session.commit()
    return ImagesGenerateResponse(
        organization_id=body.organization_id,
        project_id=body.project_id,
        prompt=body.prompt,
        n=body.n,
        aspect_ratio=body.aspect_ratio,
        results=results,
    )
