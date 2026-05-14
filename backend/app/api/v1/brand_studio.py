"""Brand Setup Studio API (S4-E).

  POST /api/v1/brand-studio/extract     — extract palette/fonts/voice from text
  GET  /api/v1/brand-studio/bandit/{org_id} — top-N bandit-ranked insights
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.user import User
from app.services.brand_bandit import rank_insights_for
from app.services.brand_pdf_extract import extract_brand_kit_from_text


router = APIRouter(prefix="/brand-studio", tags=["brand-studio"])


class ExtractBody(BaseModel):
    text: str


@router.post("/extract")
async def extract(
    body: ExtractBody,
    _: User = Depends(current_active_user),
) -> dict[str, Any]:
    """Extract a draft BrandKit suggestion from the raw text of a
    brand-guidelines PDF (or any pasted source)."""
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="text is required")
    return extract_brand_kit_from_text(body.text)


@router.get("/bandit/{organization_id}")
async def bandit(
    organization_id: UUID,
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(current_active_user),
) -> dict[str, Any]:
    ranked = await rank_insights_for(
        db, organization_id=organization_id, limit=limit
    )
    return {
        "items": [
            {"id": str(r.id), "score": r.score, "text": r.text} for r in ranked
        ]
    }
