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
from app.services.asset_gen import (
    generate_music,
    generate_video,
    generate_voice,
)


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


# ---------- Phase 3.3 — video / voice / music ------------------------


class AssetResultItem(BaseModel):
    url: str
    provider: str
    approval_request_id: str
    duration_s: float | None = None


def _file_asset(
    *,
    session: AsyncSession,
    user: User,
    organization_id: UUID,
    project_id: UUID | None,
    asset_kind: str,
    action_type: str,
    target_type: str,
    prompt: str,
    payload_extra: dict,
    summary_prefix: str,
) -> ApprovalRequest:
    """Helper to build a pending ApprovalRequest from an asset hit."""
    ar = ApprovalRequest(
        organization_id=organization_id,
        project_id=project_id,
        requested_by_user_id=user.id,
        requested_by_agent="creatives_agent_v1",
        action_type=action_type,
        target_type=target_type,
        payload_json={
            "prompt": prompt,
            "asset_kind": asset_kind,
            **payload_extra,
        },
        summary=(
            f"{summary_prefix}: "
            f"{prompt[:80]}{'…' if len(prompt) > 80 else ''}"
        ),
        status=ApprovalStatus.pending,
    )
    session.add(ar)
    return ar


class VideosGenerateRequest(BaseModel):
    organization_id: UUID
    project_id: UUID | None = None
    prompt: str = Field(min_length=4, max_length=4000)
    n: int = Field(default=1, ge=1, le=4)
    duration_s: float = Field(default=4.0, ge=1.0, le=30.0)


class VideosGenerateResponse(BaseModel):
    organization_id: UUID
    project_id: UUID | None
    prompt: str
    n: int
    duration_s: float
    results: list[AssetResultItem]


@router.post("/creatives/videos", response_model=VideosGenerateResponse)
async def creatives_generate_videos(
    body: VideosGenerateRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> VideosGenerateResponse:
    await _user_in_org(
        session, user, body.organization_id, allowed_roles=_CREATIVES_ROLES
    )
    assets = await generate_video(
        body.prompt, n=body.n, duration_s=body.duration_s
    )
    results: list[AssetResultItem] = []
    for a in assets:
        ar = _file_asset(
            session=session,
            user=user,
            organization_id=body.organization_id,
            project_id=body.project_id,
            asset_kind="video",
            action_type="publish_video_asset",
            target_type="video_draft",
            prompt=body.prompt,
            payload_extra={
                "url": a.url,
                "provider": a.provider.value,
                "duration_s": a.duration_s,
                "seed": a.seed,
            },
            summary_prefix=f"Video draft ({a.provider.value}, {a.duration_s:g}s)",
        )
        await session.flush()
        results.append(
            AssetResultItem(
                url=a.url,
                provider=a.provider.value,
                approval_request_id=str(ar.id),
                duration_s=a.duration_s,
            )
        )
    await session.commit()
    return VideosGenerateResponse(
        organization_id=body.organization_id,
        project_id=body.project_id,
        prompt=body.prompt,
        n=body.n,
        duration_s=body.duration_s,
        results=results,
    )


class VoiceGenerateRequest(BaseModel):
    organization_id: UUID
    project_id: UUID | None = None
    text: str = Field(min_length=2, max_length=4000)
    voice_id: str | None = None
    n: int = Field(default=1, ge=1, le=3)


class VoiceGenerateResponse(BaseModel):
    organization_id: UUID
    project_id: UUID | None
    text: str
    n: int
    results: list[AssetResultItem]


@router.post("/creatives/voice", response_model=VoiceGenerateResponse)
async def creatives_generate_voice(
    body: VoiceGenerateRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> VoiceGenerateResponse:
    await _user_in_org(
        session, user, body.organization_id, allowed_roles=_CREATIVES_ROLES
    )
    assets = await generate_voice(body.text, voice_id=body.voice_id, n=body.n)
    results: list[AssetResultItem] = []
    for a in assets:
        ar = _file_asset(
            session=session,
            user=user,
            organization_id=body.organization_id,
            project_id=body.project_id,
            asset_kind="voice",
            action_type="publish_voice_asset",
            target_type="voice_draft",
            prompt=body.text,
            payload_extra={
                "url": a.url,
                "provider": a.provider.value,
                "voice_id": body.voice_id,
                "duration_s": a.duration_s,
                "seed": a.seed,
            },
            summary_prefix=f"Voice draft ({a.provider.value})",
        )
        await session.flush()
        results.append(
            AssetResultItem(
                url=a.url,
                provider=a.provider.value,
                approval_request_id=str(ar.id),
                duration_s=a.duration_s,
            )
        )
    await session.commit()
    return VoiceGenerateResponse(
        organization_id=body.organization_id,
        project_id=body.project_id,
        text=body.text,
        n=body.n,
        results=results,
    )


class MusicGenerateRequest(BaseModel):
    organization_id: UUID
    project_id: UUID | None = None
    prompt: str = Field(min_length=4, max_length=4000)
    n: int = Field(default=1, ge=1, le=4)
    duration_s: float = Field(default=15.0, ge=2.0, le=120.0)


class MusicGenerateResponse(BaseModel):
    organization_id: UUID
    project_id: UUID | None
    prompt: str
    n: int
    duration_s: float
    results: list[AssetResultItem]


@router.post("/creatives/music", response_model=MusicGenerateResponse)
async def creatives_generate_music(
    body: MusicGenerateRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> MusicGenerateResponse:
    await _user_in_org(
        session, user, body.organization_id, allowed_roles=_CREATIVES_ROLES
    )
    assets = await generate_music(
        body.prompt, n=body.n, duration_s=body.duration_s
    )
    results: list[AssetResultItem] = []
    for a in assets:
        ar = _file_asset(
            session=session,
            user=user,
            organization_id=body.organization_id,
            project_id=body.project_id,
            asset_kind="music",
            action_type="publish_music_asset",
            target_type="music_draft",
            prompt=body.prompt,
            payload_extra={
                "url": a.url,
                "provider": a.provider.value,
                "duration_s": a.duration_s,
                "seed": a.seed,
            },
            summary_prefix=f"Music draft ({a.provider.value}, {a.duration_s:g}s)",
        )
        await session.flush()
        results.append(
            AssetResultItem(
                url=a.url,
                provider=a.provider.value,
                approval_request_id=str(ar.id),
                duration_s=a.duration_s,
            )
        )
    await session.commit()
    return MusicGenerateResponse(
        organization_id=body.organization_id,
        project_id=body.project_id,
        prompt=body.prompt,
        n=body.n,
        duration_s=body.duration_s,
        results=results,
    )
