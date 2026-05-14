"""AEO API endpoints (S4-K2/K4).

  POST /api/v1/aeo/score            — score a single page
  POST /api/v1/aeo/batch            — score N pages, return summary
  POST /api/v1/aeo/suggest-rewrite  — LLM-driven fix suggestion
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime import run_completion
from app.auth import current_active_user
from app.core.database import get_db
from app.models.model_registry import Capability
from app.models.user import User
from app.services.aeo_scorer import build_fix_prompt, score_page


router = APIRouter(prefix="/aeo", tags=["aeo"])


class ScoreBody(BaseModel):
    text: str


@router.post("/score")
async def score(
    body: ScoreBody, _: User = Depends(current_active_user)
) -> dict[str, Any]:
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="text is required")
    return score_page(body.text)


class BatchBody(BaseModel):
    pages: list[dict[str, str]]  # [{name, text}, ...]


@router.post("/batch")
async def batch(
    body: BatchBody, _: User = Depends(current_active_user)
) -> dict[str, Any]:
    if not body.pages:
        raise HTTPException(status_code=400, detail="pages is required")
    rows: list[dict[str, Any]] = []
    total = 0
    for p in body.pages:
        s = score_page(p.get("text", ""))
        rows.append({"name": p.get("name") or "(unnamed)", **s})
        total += s["score"]
    average = total // len(body.pages) if body.pages else 0
    return {"average": average, "rows": rows}


class SuggestBody(BaseModel):
    text: str
    organization_id: UUID | None = None


@router.post("/suggest-rewrite")
async def suggest_rewrite(
    body: SuggestBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
) -> dict[str, Any]:
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="text is required")
    s = score_page(body.text)
    if not s["weak_spots"]:
        return {"score": s["score"], "rewrite": None}
    prompt = build_fix_prompt(body.text, s)
    res = await run_completion(
        db=db,
        org_id=body.organization_id,
        user_id=user.id,
        caller_component="aeo_scorer",
        system="You are the SEO Agent rewriting for Answer Engine Optimisation.",
        user=prompt,
        max_tokens=1500,
        capability=Capability.text,
    )
    return {
        "score": s["score"],
        "weak_spots": s["weak_spots"],
        "rewrite": res["text"],
        "model_id": res.get("model_id"),
        "resolved_by": res.get("resolved_by"),
    }
