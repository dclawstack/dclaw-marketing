"""B4 Repurposing Engine API.

POST /api/v1/repurpose
body: {organization_id, source_text, target_channels: [...], brand_kit_id?}
→ {results: [{channel, output, model, stub}, ...]}
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
from app.services.repurpose import CHANNEL_HINTS, repurpose


router = APIRouter(prefix="/repurpose", tags=["repurpose"])


class RepurposeRequest(BaseModel):
    organization_id: UUID
    source_text: str = Field(min_length=1, max_length=20_000)
    target_channels: list[str] = Field(min_length=1, max_length=10)
    brand_kit_id: UUID | None = None


class RepurposeResult(BaseModel):
    channel: str
    output: str
    model: str
    stub: bool


class RepurposeResponse(BaseModel):
    results: list[RepurposeResult]


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


@router.get("/channels")
async def list_supported_channels() -> dict:
    """Returns the channel slugs the engine knows how to shape for."""
    return {
        "channels": [
            {"slug": k, "limit": v["limit"], "shape": v["shape"]}
            for k, v in CHANNEL_HINTS.items()
        ]
    }


@router.post("", response_model=RepurposeResponse)
async def post_repurpose(
    body: RepurposeRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> RepurposeResponse:
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

    results = []
    for channel in body.target_channels:
        out = await repurpose(
            source_text=body.source_text,
            target_channel=channel,
            brand_voice=brand_voice,
        )
        results.append(RepurposeResult(**out))
    return RepurposeResponse(results=results)
