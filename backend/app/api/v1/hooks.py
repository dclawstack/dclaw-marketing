"""B6 Hook & Headline Lab API.

Single endpoint:
  POST /api/v1/hooks/generate
  body: {organization_id, draft_text, n=30, brand_kit_id?}
  → {hooks: [...], model, stub}
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.brand_kit import BrandKit
from app.models.organization import OrganizationMembership
from app.models.user import User
from app.services.hooks import generate_hooks


router = APIRouter(prefix="/hooks", tags=["hooks"])


class HooksRequest(BaseModel):
    organization_id: UUID
    draft_text: str = Field(min_length=1, max_length=10_000)
    n: int = Field(default=30, ge=1, le=60)
    brand_kit_id: UUID | None = None


class HooksResponse(BaseModel):
    hooks: list[str]
    model: str
    stub: bool


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


@router.post("/generate", response_model=HooksResponse)
async def generate(
    body: HooksRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> HooksResponse:
    await _require_member(session, user, body.organization_id)

    brand_voice: dict[str, Any] | None = None
    if body.brand_kit_id is not None:
        kit = await session.get(BrandKit, body.brand_kit_id)
        if kit is None or kit.organization_id != body.organization_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Brand kit not found in this organization.",
            )
        brand_voice = kit.voice_json or {}

    result = await generate_hooks(
        draft_text=body.draft_text, n=body.n, brand_voice=brand_voice
    )
    return HooksResponse(**result)
