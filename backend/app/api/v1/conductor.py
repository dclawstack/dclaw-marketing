"""Conductor agent API (S4-A2 / S4-C).

For Sprint 4 we expose two endpoints:

  POST /api/v1/conductor/decompose  — break a brief into role-agent tasks
  POST /api/v1/conductor/dispatch   — run the decomposed plan synchronously,
                                       returning each role-agent's output

The role-agents themselves keep their existing endpoints under /agents/...
This module is just the orchestration layer.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime import decompose_brief, run_completion
from app.auth import current_active_user
from app.core.database import get_db
from app.models.user import User


router = APIRouter(prefix="/conductor", tags=["conductor"])


class BriefIn(BaseModel):
    organization_id: UUID | None = None
    brief: str


class DecomposeOut(BaseModel):
    plan: dict[str, Any]
    model_id: str | None
    resolved_by: str | None


@router.post("/decompose", response_model=DecomposeOut)
async def decompose(
    body: BriefIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
) -> DecomposeOut:
    if not body.brief.strip():
        raise HTTPException(status_code=400, detail="brief is required")
    result = await decompose_brief(
        db=db,
        org_id=body.organization_id,
        user_id=user.id,
        brief=body.brief,
    )
    return DecomposeOut(**result)


class DispatchOut(BaseModel):
    plan: dict[str, Any]
    results: list[dict[str, Any]]


_ROLE_SYSTEM: dict[str, str] = {
    "creatives": "You are the Creatives Agent. Draft text + visual ideas.",
    "smm":       "You are the SMM Agent. Pick channels, schedule cadence.",
    "seo":       "You are the SEO Agent. Suggest keywords, briefs, AEO answers.",
    "paid_media": "You are the Paid Media Agent. Outline campaign structure.",
    "analyst":   "You are the Analyst Agent. Identify metrics + anomalies.",
    "inbox":     "You are the Inbox Agent. Draft reply suggestions.",
    "reviewer":  "You are the Reviewer Agent. Flag compliance / brand issues.",
}


@router.post("/dispatch", response_model=DispatchOut)
async def dispatch(
    body: BriefIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
) -> DispatchOut:
    """Decompose + run every sub-task synchronously. Sprint-4 MVP path —
    later sprints can parallelize + persist as AgentThread messages."""
    decomp = await decompose_brief(
        db=db,
        org_id=body.organization_id,
        user_id=user.id,
        brief=body.brief,
    )
    plan = decomp["plan"]
    out: list[dict[str, Any]] = []
    for task in plan.get("tasks", []):
        agent = task.get("agent", "creatives")
        system = _ROLE_SYSTEM.get(agent, _ROLE_SYSTEM["creatives"])
        res = await run_completion(
            db=db,
            org_id=body.organization_id,
            user_id=user.id,
            caller_component=f"{agent}_agent",
            system=system,
            user=task.get("input") or body.brief,
            max_tokens=600,
        )
        out.append(
            {
                "agent": agent,
                "intent": task.get("intent"),
                "text": res["text"],
                "model_id": res.get("model_id"),
                "resolved_by": res.get("resolved_by"),
            }
        )
    return DispatchOut(plan=plan, results=out)
