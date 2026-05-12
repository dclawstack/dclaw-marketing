"""SEO blog pipeline endpoints (SP3-17 — Theme H2)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.auth import current_active_user
from app.models.user import User
from app.services import seo_pipeline


router = APIRouter(prefix="/seo/pipeline", tags=["seo-pipeline"])


class KeywordReq(BaseModel):
    brand_context: dict = Field(default_factory=dict)
    count: int = Field(default=8, ge=1, le=25)


class OutlineReq(BaseModel):
    keyword: str = Field(min_length=1, max_length=255)
    target_word_count: int = Field(default=1200, ge=300, le=5000)


class DraftReq(BaseModel):
    keyword: str = Field(min_length=1, max_length=255)
    outline: dict | None = None
    brand_context: dict = Field(default_factory=dict)


@router.post("/keywords")
async def keywords(
    body: KeywordReq,
    user: User = Depends(current_active_user),
) -> dict:
    items = seo_pipeline.suggest_keywords(
        brand_context=body.brand_context, count=body.count
    )
    return {"items": items}


@router.post("/outline")
async def outline(
    body: OutlineReq,
    user: User = Depends(current_active_user),
) -> dict:
    return seo_pipeline.build_outline(
        keyword=body.keyword, target_word_count=body.target_word_count
    )


@router.post("/draft")
async def draft(
    body: DraftReq,
    user: User = Depends(current_active_user),
) -> dict:
    md = seo_pipeline.draft_post(
        keyword=body.keyword,
        outline=body.outline,
        brand_context=body.brand_context,
    )
    return {"keyword": body.keyword, "markdown": md}
