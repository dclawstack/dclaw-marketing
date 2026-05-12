"""BrandKitInsight CRUD — Phase 2 / Q3 §6.2 KG write-back surface.

Endpoints:

  POST   /api/v1/orgs/{org}/brand-kits/{kit}/insights
  GET    /api/v1/orgs/{org}/brand-kits/{kit}/insights
  PATCH  /api/v1/brand-insights/{id}
  DELETE /api/v1/brand-insights/{id}

Used by:
  - Analyst Agent's weekly report task → auto-creates insights when
    something notable happens (auto-generated rows have
    ``is_human_edited=False`` and ``generated_by_agent=<name>``).
  - Future ``/orgs/[id]/brand/insights`` UI → humans review, edit,
    archive.
  - System-prompt composition pulls the top-K confidence-ordered
    insights when an agent runs.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.brand_kit import BrandKit
from app.models.brand_kit_insight import BrandKitInsight, BrandKitInsightKind
from app.models.organization import OrganizationMembership, OrganizationRole
from app.models.user import User


router = APIRouter(tags=["brand-insights"])


class InsightCreate(BaseModel):
    kind: BrandKitInsightKind
    summary: str = Field(min_length=1, max_length=512)
    detail: str | None = None
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    generated_by_agent: str | None = None
    payload_json: dict | None = None


class InsightUpdate(BaseModel):
    summary: str | None = Field(default=None, max_length=512)
    detail: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    is_archived: bool | None = None


class InsightRead(BaseModel):
    id: UUID
    organization_id: UUID
    brand_kit_id: UUID
    kind: BrandKitInsightKind
    summary: str
    detail: str | None
    confidence: float
    source_run_id: UUID | None
    generated_by_agent: str | None
    is_human_edited: bool
    is_archived: bool

    model_config = ConfigDict(from_attributes=True)


async def _require_member(
    session: AsyncSession, user: User, org_id: UUID
) -> None:
    if user.is_superuser:
        return
    res = await session.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == org_id,
        )
    )
    if res.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not a member."
        )


@router.post(
    "/orgs/{org_id}/brand-kits/{kit_id}/insights",
    response_model=InsightRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_insight(
    org_id: UUID,
    kit_id: UUID,
    body: InsightCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> BrandKitInsight:
    await _require_member(session, user, org_id)
    kit = await session.get(BrandKit, kit_id)
    if kit is None or kit.organization_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Brand kit not found.",
        )
    insight = BrandKitInsight(
        organization_id=org_id,
        brand_kit_id=kit_id,
        kind=body.kind,
        summary=body.summary,
        detail=body.detail,
        confidence=body.confidence,
        generated_by_agent=body.generated_by_agent,
        payload_json=body.payload_json,
        is_human_edited=body.generated_by_agent is None,
    )
    session.add(insight)
    await session.flush()
    await session.commit()
    await session.refresh(insight)
    return insight


@router.get(
    "/orgs/{org_id}/brand-kits/{kit_id}/insights",
    response_model=list[InsightRead],
)
async def list_insights(
    org_id: UUID,
    kit_id: UUID,
    include_archived: bool = False,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> list[BrandKitInsight]:
    await _require_member(session, user, org_id)
    stmt = (
        select(BrandKitInsight)
        .where(
            BrandKitInsight.organization_id == org_id,
            BrandKitInsight.brand_kit_id == kit_id,
        )
        .order_by(desc(BrandKitInsight.confidence), desc(BrandKitInsight.created_at))
    )
    if not include_archived:
        stmt = stmt.where(BrandKitInsight.is_archived.is_(False))
    res = await session.execute(stmt)
    return list(res.scalars().all())


@router.patch("/brand-insights/{insight_id}", response_model=InsightRead)
async def update_insight(
    insight_id: UUID,
    body: InsightUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> BrandKitInsight:
    row = await session.get(BrandKitInsight, insight_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Insight not found.")
    await _require_member(session, user, row.organization_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    row.is_human_edited = True
    await session.flush()
    await session.commit()
    await session.refresh(row)
    return row


@router.delete(
    "/brand-insights/{insight_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_insight(
    insight_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    row = await session.get(BrandKitInsight, insight_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Insight not found.")
    await _require_member(session, user, row.organization_id)
    await session.delete(row)
    await session.commit()


__all__ = ["router"]
