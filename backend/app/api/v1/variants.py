"""B5 Variant A/B Studio API (Sprint 3 / SP3-10).

Endpoints:
  POST /api/v1/orgs/{org}/variant-sets         — create a set
  GET  /api/v1/orgs/{org}/variant-sets         — list sets
  GET  /api/v1/variant-sets/{id}               — set detail w/ variants
  POST /api/v1/variant-sets/{id}/variants      — add variant
  PATCH /api/v1/variants/{id}                  — update weight / status
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.organization import OrganizationMembership
from app.models.user import User
from app.models.variant import Variant, VariantSet, VariantSetStatus, VariantStatus


router = APIRouter(tags=["variants"])


class VariantSetCreate(BaseModel):
    campaign_id: UUID | None = None
    slot: str = Field(min_length=1, max_length=64)
    hypothesis: str | None = None
    auto_promote_winner: bool = False


class VariantSetRead(BaseModel):
    id: UUID
    organization_id: UUID
    campaign_id: UUID | None
    slot: str
    hypothesis: str | None
    status: VariantSetStatus
    auto_promote_winner: bool

    model_config = ConfigDict(from_attributes=True)


class VariantCreate(BaseModel):
    asset_id: UUID | None = None
    label: str | None = Field(default=None, max_length=255)
    body_text: str | None = None
    weight: float = Field(default=1.0, ge=0.0, le=10.0)


class VariantRead(BaseModel):
    id: UUID
    set_id: UUID
    asset_id: UUID | None
    label: str | None
    body_text: str | None
    weight: float
    status: VariantStatus
    impressions: int
    conversions: int

    model_config = ConfigDict(from_attributes=True)


class VariantUpdate(BaseModel):
    weight: float | None = Field(default=None, ge=0.0, le=10.0)
    status: VariantStatus | None = None


class VariantSetDetail(VariantSetRead):
    variants: list[VariantRead]


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


@router.post(
    "/orgs/{organization_id}/variant-sets",
    response_model=VariantSetRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_variant_set(
    organization_id: UUID,
    body: VariantSetCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> VariantSetRead:
    await _require_member(session, user, organization_id)
    vs = VariantSet(
        organization_id=organization_id,
        campaign_id=body.campaign_id,
        slot=body.slot,
        hypothesis=body.hypothesis,
        auto_promote_winner=body.auto_promote_winner,
    )
    session.add(vs)
    await session.commit()
    await session.refresh(vs)
    return VariantSetRead.model_validate(vs)


@router.get(
    "/orgs/{organization_id}/variant-sets",
    response_model=list[VariantSetRead],
)
async def list_variant_sets(
    organization_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> list[VariantSetRead]:
    await _require_member(session, user, organization_id)
    rows = (
        await session.execute(
            select(VariantSet)
            .where(VariantSet.organization_id == organization_id)
            .order_by(desc(VariantSet.created_at))
        )
    ).scalars().all()
    return [VariantSetRead.model_validate(r) for r in rows]


@router.get("/variant-sets/{set_id}", response_model=VariantSetDetail)
async def get_variant_set(
    set_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> VariantSetDetail:
    vs = await session.get(VariantSet, set_id)
    if vs is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Variant set not found."
        )
    await _require_member(session, user, vs.organization_id)
    variants = (
        await session.execute(
            select(Variant).where(Variant.set_id == set_id).order_by(Variant.created_at)
        )
    ).scalars().all()
    out = VariantSetRead.model_validate(vs).model_dump()
    out["variants"] = [VariantRead.model_validate(v) for v in variants]
    return VariantSetDetail(**out)


@router.post(
    "/variant-sets/{set_id}/variants",
    response_model=VariantRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_variant(
    set_id: UUID,
    body: VariantCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> VariantRead:
    vs = await session.get(VariantSet, set_id)
    if vs is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Variant set not found."
        )
    await _require_member(session, user, vs.organization_id)
    v = Variant(
        set_id=set_id,
        asset_id=body.asset_id,
        label=body.label,
        body_text=body.body_text,
        weight=body.weight,
    )
    session.add(v)
    await session.commit()
    await session.refresh(v)
    return VariantRead.model_validate(v)


@router.patch("/variants/{variant_id}", response_model=VariantRead)
async def update_variant(
    variant_id: UUID,
    body: VariantUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> VariantRead:
    v = await session.get(Variant, variant_id)
    if v is None:
        raise HTTPException(status_code=404, detail="Variant not found.")
    vs = await session.get(VariantSet, v.set_id)
    if vs is None:
        raise HTTPException(status_code=404, detail="Variant set not found.")
    await _require_member(session, user, vs.organization_id)
    if body.weight is not None:
        v.weight = body.weight
    if body.status is not None:
        v.status = body.status
    await session.commit()
    await session.refresh(v)
    return VariantRead.model_validate(v)
