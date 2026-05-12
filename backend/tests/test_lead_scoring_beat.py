"""Phase 8.8 follow-up — daily lead rescore + auto-promotion beat task."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.lead import LeadStage
from app.worker.tasks.lead_scoring import (
    _should_promote,
    _stage_from_score,
)


# ---------- Pure helpers ---------------------------------------------------


def test_stage_from_score_thresholds():
    assert _stage_from_score(0.0) == LeadStage.new
    assert _stage_from_score(24.9) == LeadStage.new
    assert _stage_from_score(25.0) == LeadStage.mql
    assert _stage_from_score(59.9) == LeadStage.mql
    assert _stage_from_score(60.0) == LeadStage.sql
    assert _stage_from_score(89.9) == LeadStage.sql
    assert _stage_from_score(90.0) == LeadStage.customer
    assert _stage_from_score(100.0) == LeadStage.customer


def test_should_promote_monotonic():
    # Visitor → new : allowed
    assert _should_promote(LeadStage.visitor, LeadStage.new)
    # New → mql : allowed
    assert _should_promote(LeadStage.new, LeadStage.mql)
    # Mql → sql : allowed
    assert _should_promote(LeadStage.mql, LeadStage.sql)
    # Sql → customer : allowed
    assert _should_promote(LeadStage.sql, LeadStage.customer)
    # mql → new : not a promotion (no demotion via this path)
    assert not _should_promote(LeadStage.mql, LeadStage.new)
    # sql → mql : not a promotion
    assert not _should_promote(LeadStage.sql, LeadStage.mql)
    # mql → mql : no-op
    assert not _should_promote(LeadStage.mql, LeadStage.mql)


def test_churned_never_promoted():
    # No matter what the score says, churned stays churned in the task.
    for proposed in (
        LeadStage.new,
        LeadStage.mql,
        LeadStage.sql,
        LeadStage.customer,
    ):
        assert not _should_promote(LeadStage.churned, proposed)


# ---------- DB integration -------------------------------------------------


@pytest.mark.asyncio
async def test_recompute_promotes_and_writes_stage_change_activity(client):
    """End-to-end with the real (sync) SyncSession — we seed an org, a
    lead at stage=new, and a fresh email_reply activity worth +20 plus
    several +10 intrinsic bumps that push score past 25 → mql."""
    import asyncio
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.lead import Lead, LeadActivity, LeadActivityKind, LeadStage
    from app.models.organization import Organization
    from app.worker.tasks.lead_scoring import recompute_lead_scores
    from tests.conftest import test_engine

    async def seed() -> tuple[str, str]:
        async with AsyncSession(test_engine, expire_on_commit=False) as session:
            org = Organization(slug="scoring-co", name="Scoring Co")
            session.add(org)
            await session.flush()
            lead = Lead(
                organization_id=org.id,
                email="hot@lead.co",
                first_name="Hot",
                last_name="Lead",
                stage=LeadStage.new,
                company="Acme",
                domain="acme.co",
                linkedin_url="https://linkedin.com/in/hot",
                phone="+1-555",
            )
            session.add(lead)
            await session.flush()
            session.add(
                LeadActivity(
                    lead_id=lead.id,
                    organization_id=org.id,
                    kind=LeadActivityKind.email_reply,
                    summary="replied",
                    occurred_at=datetime.now(tz=timezone.utc),
                )
            )
            await session.commit()
            await session.refresh(lead)
            return str(org.id), str(lead.id)

    org_id_str, lead_id_str = await seed()

    # Celery task is sync — call directly without .delay().
    result = recompute_lead_scores()
    assert result["rescored"] >= 1
    assert result["promoted"] >= 1

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        from uuid import UUID

        lead = await session.get(Lead, UUID(lead_id_str))
        assert lead is not None
        # +20 (email_reply) + +5 (domain) + +10 (linkedin_url) + +10 (company) + +5 (phone) = 50
        # Stage was "new" — should promote to "mql" (≥ 25) (note: sql needs ≥ 60).
        assert lead.score is not None
        assert lead.stage == LeadStage.mql

        from sqlalchemy import select

        result = await session.execute(
            select(LeadActivity).where(
                LeadActivity.lead_id == UUID(lead_id_str),
                LeadActivity.kind == LeadActivityKind.stage_change,
            )
        )
        promotions = result.scalars().all()
        assert len(promotions) == 1
        assert promotions[0].payload_json["auto"] is True
        assert promotions[0].payload_json["to"] == "mql"
