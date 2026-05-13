"""N — Playbook search + editor API (SP3-18).

Endpoints:
  GET   /api/v1/orgs/{org}/playbooks?q=&kind=&is_template=
  POST  /api/v1/orgs/{org}/playbooks
  GET   /api/v1/playbooks/{id}
  PATCH /api/v1/playbooks/{id}
  DELETE /api/v1/playbooks/{id}

Search: substring match against name + body_markdown. Vector search
follows when DocumentChunk-style embeddings on Playbooks are added.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.ops import Playbook, PlaybookKind
from app.models.organization import OrganizationMembership
from app.models.user import User


router = APIRouter(tags=["playbooks"])


class PlaybookCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=255)
    kind: PlaybookKind
    body_markdown: str = Field(min_length=1)
    tags: list[str] | None = None
    is_template: bool = False


class PlaybookUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    kind: PlaybookKind | None = None
    body_markdown: str | None = None
    tags: list[str] | None = None
    is_template: bool | None = None


class PlaybookRead(BaseModel):
    id: UUID
    organization_id: UUID
    slug: str
    name: str
    kind: PlaybookKind
    body_markdown: str
    tags: list[str] | None
    is_template: bool

    class Config:
        from_attributes = True


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
    "/orgs/{organization_id}/playbooks", response_model=list[PlaybookRead]
)
async def list_playbooks(
    organization_id: UUID,
    q: str | None = Query(None),
    kind: PlaybookKind | None = Query(None),
    is_template: bool | None = Query(None),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> list[PlaybookRead]:
    await _require_member(session, user, organization_id)
    stmt = select(Playbook).where(Playbook.organization_id == organization_id)
    if kind is not None:
        stmt = stmt.where(Playbook.kind == kind)
    if is_template is not None:
        stmt = stmt.where(Playbook.is_template.is_(is_template))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(Playbook.name.ilike(like), Playbook.body_markdown.ilike(like))
        )
    stmt = stmt.order_by(desc(Playbook.updated_at))
    rows = (await session.execute(stmt)).scalars().all()
    return [PlaybookRead.model_validate(r) for r in rows]


@router.post(
    "/orgs/{organization_id}/playbooks",
    response_model=PlaybookRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_playbook(
    organization_id: UUID,
    body: PlaybookCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> PlaybookRead:
    await _require_member(session, user, organization_id)
    p = Playbook(
        organization_id=organization_id,
        slug=body.slug,
        name=body.name,
        kind=body.kind,
        body_markdown=body.body_markdown,
        tags=body.tags,
        is_template=body.is_template,
        created_by_user_id=user.id,
    )
    session.add(p)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A playbook with this slug already exists in this organization.",
        )
    await session.refresh(p)
    return PlaybookRead.model_validate(p)


@router.get("/playbooks/{playbook_id}", response_model=PlaybookRead)
async def get_playbook(
    playbook_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> PlaybookRead:
    p = await session.get(Playbook, playbook_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Playbook not found.")
    await _require_member(session, user, p.organization_id)
    return PlaybookRead.model_validate(p)


@router.patch("/playbooks/{playbook_id}", response_model=PlaybookRead)
async def update_playbook(
    playbook_id: UUID,
    body: PlaybookUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> PlaybookRead:
    p = await session.get(Playbook, playbook_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Playbook not found.")
    await _require_member(session, user, p.organization_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(p, field, value)
    await session.commit()
    await session.refresh(p)
    return PlaybookRead.model_validate(p)


@router.delete("/playbooks/{playbook_id}", status_code=204)
async def delete_playbook(
    playbook_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    p = await session.get(Playbook, playbook_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Playbook not found.")
    await _require_member(session, user, p.organization_id)
    await session.delete(p)
    await session.commit()
    return None
