"""ScheduledPost API — calendar + dispatcher backend (Theme C1, Phase 4).

Endpoints:
  POST   /orgs/{org_id}/scheduled-posts       — create a new scheduled post
  GET    /orgs/{org_id}/scheduled-posts       — list (filterable by date range / status / channel)
  GET    /orgs/{org_id}/scheduled-posts/{id}  — get one
  PATCH  /orgs/{org_id}/scheduled-posts/{id}  — edit (reschedule / change copy)
  DELETE /orgs/{org_id}/scheduled-posts/{id}  — cancel (sets status=cancelled, doesn't delete)
  POST   /orgs/{org_id}/scheduled-posts/{id}/publish-now
                                              — bump scheduled_at to NOW so the
                                                next beat tick picks it up
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.organization import (
    OrganizationMembership,
    OrganizationRole,
)
from app.models.scheduled_post import (
    ScheduledPost,
    ScheduledPostChannel,
    ScheduledPostStatus,
)
from app.models.user import User


router = APIRouter(prefix="/orgs/{org_id}/scheduled-posts", tags=["scheduled-posts"])


_WRITE_ROLES: tuple[OrganizationRole, ...] = (
    OrganizationRole.admin,
    OrganizationRole.manager,
    OrganizationRole.creatives,
    OrganizationRole.social_media_manager,
)


# ---------- schemas -----------------------------------------------------


class ScheduledPostCreate(BaseModel):
    channel: ScheduledPostChannel
    scheduled_at: datetime = Field(
        description="When the post should go out. Must be in the future."
    )
    copy: str | None = Field(default=None, max_length=10_000)
    asset_ids: list[UUID] | None = None
    tags: list[str] | None = None
    project_id: UUID | None = None
    parent_campaign_id: UUID | None = None


class ScheduledPostUpdate(BaseModel):
    channel: ScheduledPostChannel | None = None
    scheduled_at: datetime | None = None
    copy: str | None = Field(default=None, max_length=10_000)
    asset_ids: list[UUID] | None = None
    tags: list[str] | None = None


class ScheduledPostRead(BaseModel):
    id: UUID
    organization_id: UUID
    project_id: UUID | None
    parent_campaign_id: UUID | None
    channel: ScheduledPostChannel
    asset_ids: list[str] | None
    copy: str | None
    tags: list[str] | None
    scheduled_at: datetime
    published_at: datetime | None
    error_message: str | None
    publisher_response: dict | None
    status: ScheduledPostStatus
    created_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------- helpers -----------------------------------------------------


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
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not a member."
        )
    if write and m.role not in _WRITE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your role can't schedule posts.",
        )


async def _get_or_404(
    session: AsyncSession, org_id: UUID, post_id: UUID
) -> ScheduledPost:
    result = await session.execute(
        select(ScheduledPost).where(
            ScheduledPost.id == post_id,
            ScheduledPost.organization_id == org_id,
        )
    )
    p = result.scalar_one_or_none()
    if p is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scheduled post not found.",
        )
    return p


# ---------- endpoints ----------------------------------------------------


@router.post(
    "",
    response_model=ScheduledPostRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_scheduled_post(
    org_id: UUID,
    body: ScheduledPostCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> ScheduledPostRead:
    await _require_member(session, user, org_id, write=True)

    now = datetime.now(tz=timezone.utc)
    if body.scheduled_at < now:
        # We still allow it but flag — useful for "publish immediately".
        # Hard rule: never more than 24h in the past (prevents accidental
        # backfill of fake post history).
        if (now - body.scheduled_at).total_seconds() > 24 * 60 * 60:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="scheduled_at cannot be more than 24h in the past.",
            )

    post = ScheduledPost(
        organization_id=org_id,
        project_id=body.project_id,
        parent_campaign_id=body.parent_campaign_id,
        channel=body.channel,
        copy=body.copy,
        asset_ids=[str(a) for a in body.asset_ids] if body.asset_ids else None,
        tags=body.tags,
        scheduled_at=body.scheduled_at,
        status=ScheduledPostStatus.queued,
        created_by_user_id=user.id,
    )
    session.add(post)
    await session.commit()
    await session.refresh(post)
    return ScheduledPostRead.model_validate(post)


@router.get("", response_model=list[ScheduledPostRead])
async def list_scheduled_posts(
    org_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    channel: ScheduledPostChannel | None = Query(default=None),
    status_filter: ScheduledPostStatus | None = Query(default=None, alias="status"),
    project_id: UUID | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
) -> list[ScheduledPostRead]:
    await _require_member(session, user, org_id)

    conditions: list[Any] = [ScheduledPost.organization_id == org_id]
    if from_ is not None:
        conditions.append(ScheduledPost.scheduled_at >= from_)
    if to is not None:
        conditions.append(ScheduledPost.scheduled_at <= to)
    if channel is not None:
        conditions.append(ScheduledPost.channel == channel)
    if status_filter is not None:
        conditions.append(ScheduledPost.status == status_filter)
    if project_id is not None:
        conditions.append(ScheduledPost.project_id == project_id)

    result = await session.execute(
        select(ScheduledPost)
        .where(and_(*conditions))
        .order_by(ScheduledPost.scheduled_at.asc())
        .limit(limit)
    )
    return [ScheduledPostRead.model_validate(p) for p in result.scalars().all()]


@router.get("/{post_id}", response_model=ScheduledPostRead)
async def get_scheduled_post(
    org_id: UUID,
    post_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> ScheduledPostRead:
    await _require_member(session, user, org_id)
    p = await _get_or_404(session, org_id, post_id)
    return ScheduledPostRead.model_validate(p)


@router.patch("/{post_id}", response_model=ScheduledPostRead)
async def update_scheduled_post(
    org_id: UUID,
    post_id: UUID,
    body: ScheduledPostUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> ScheduledPostRead:
    await _require_member(session, user, org_id, write=True)
    p = await _get_or_404(session, org_id, post_id)

    # Only allow edits while still queued — once it's published/failed/
    # cancelled the row is immutable.
    if p.status not in (ScheduledPostStatus.queued,):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot edit a post in status '{p.status.value}'.",
        )

    data = body.model_dump(exclude_unset=True)
    if "asset_ids" in data and data["asset_ids"] is not None:
        data["asset_ids"] = [str(a) for a in data["asset_ids"]]
    for k, v in data.items():
        setattr(p, k, v)
    await session.commit()
    await session.refresh(p)
    return ScheduledPostRead.model_validate(p)


@router.delete("/{post_id}", response_model=ScheduledPostRead)
async def cancel_scheduled_post(
    org_id: UUID,
    post_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> ScheduledPostRead:
    """Soft-cancel: flip status to cancelled, retain row for audit."""
    await _require_member(session, user, org_id, write=True)
    p = await _get_or_404(session, org_id, post_id)
    if p.status not in (
        ScheduledPostStatus.queued,
        ScheduledPostStatus.would_publish,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot cancel a post in status '{p.status.value}'.",
        )
    p.status = ScheduledPostStatus.cancelled
    await session.commit()
    await session.refresh(p)
    return ScheduledPostRead.model_validate(p)


@router.post("/{post_id}/publish-now", response_model=ScheduledPostRead)
async def publish_now(
    org_id: UUID,
    post_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> ScheduledPostRead:
    """Bump scheduled_at to now so the dispatcher fires it next tick."""
    await _require_member(session, user, org_id, write=True)
    p = await _get_or_404(session, org_id, post_id)
    if p.status != ScheduledPostStatus.queued:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Can only publish-now a queued post (current: '{p.status.value}').",
        )
    p.scheduled_at = datetime.now(tz=timezone.utc)
    await session.commit()
    await session.refresh(p)
    return ScheduledPostRead.model_validate(p)
