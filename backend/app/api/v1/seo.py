"""SEO API — Theme H.

Surfaces the SEO Agent's outputs:

  * ``GET  /orgs/{org_id}/seo/audit`` — list recent audit findings
  * ``POST /orgs/{org_id}/seo/audit/run`` — kick a fresh audit for a domain
  * ``POST /orgs/{org_id}/seo/internal-links`` — suggest internal-link targets for a draft
  * ``GET  /orgs/{org_id}/seo/ranking-delta`` — delta over the configured window

All endpoints require Org membership (or superuser).
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
from app.models.organization import Organization, OrganizationMembership
from app.models.user import User
from app.services.seo.audit import list_audit_findings, run_site_audit
from app.services.seo.internal_linking import suggest_internal_links
from app.services.seo.ranking_delta import compute_ranking_delta


router = APIRouter(prefix="/orgs/{organization_id}/seo", tags=["seo"])


async def _require_member(
    session: AsyncSession, user: User, organization_id: UUID
) -> Organization:
    org = await session.get(Organization, organization_id)
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found."
        )
    if user.is_superuser:
        return org
    membership = (
        await session.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.organization_id == organization_id,
            )
        )
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization.",
        )
    return org


# ---------- audit -----------------------------------------------------------


class AuditFinding(BaseModel):
    id: str
    created_at: str
    domain: str | None
    kind: str | None
    severity: str | None
    url: str | None
    detail: str | None
    stub: bool = False


@router.get("/audit", response_model=list[AuditFinding])
async def get_audit(
    organization_id: UUID,
    domain: str | None = None,
    days: int = 30,
    limit: int = 200,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> list[AuditFinding]:
    await _require_member(session, user, organization_id)
    rows = await list_audit_findings(
        session,
        organization_id=organization_id,
        domain=domain,
        days=days,
        limit=limit,
    )
    return [AuditFinding(**r) for r in rows]


class RunAuditRequest(BaseModel):
    domain: str = Field(min_length=3, max_length=255)


class RunAuditResponse(BaseModel):
    domain: str
    findings_count: int
    stub: bool
    findings: list[dict[str, Any]]


@router.post("/audit/run", response_model=RunAuditResponse)
async def post_run_audit(
    organization_id: UUID,
    body: RunAuditRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> RunAuditResponse:
    await _require_member(session, user, organization_id)
    summary = await run_site_audit(
        session, organization_id=organization_id, domain=body.domain
    )
    await session.commit()
    return RunAuditResponse(**summary)


# ---------- internal links --------------------------------------------------


class InternalLinkRequest(BaseModel):
    draft_text: str = Field(min_length=1, max_length=20_000)
    top_k: int = Field(default=5, ge=1, le=25)
    min_similarity: float = Field(default=0.0, ge=0.0, le=1.0)


class InternalLinkSuggestion(BaseModel):
    chunk_id: str
    source_id: str
    source_type: str
    source_reference: str
    anchor: str
    similarity: float


@router.post("/internal-links", response_model=list[InternalLinkSuggestion])
async def post_internal_links(
    organization_id: UUID,
    body: InternalLinkRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> list[InternalLinkSuggestion]:
    await _require_member(session, user, organization_id)
    rows = await suggest_internal_links(
        session,
        organization_id=organization_id,
        draft_text=body.draft_text,
        top_k=body.top_k,
        min_similarity=body.min_similarity,
    )
    return [InternalLinkSuggestion(**r) for r in rows]


# ---------- ranking delta ---------------------------------------------------


class RankingDelta(BaseModel):
    keyword: str
    country: str = "us"
    current: int | None = None
    previous: int | None = None
    delta: int | None = None
    snapshot_at: str


@router.get("/ranking-delta", response_model=list[RankingDelta])
async def get_ranking_delta(
    organization_id: UUID,
    days: int = 7,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> list[RankingDelta]:
    await _require_member(session, user, organization_id)
    rows = await compute_ranking_delta(
        session, organization_id=organization_id, days=days
    )
    return [RankingDelta(**r) for r in rows]
