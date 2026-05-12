"""Theme H — SEO Agent depth tests.

Three layers:

  * audit run → AuditEvent persistence + GET listing
  * internal-link suggester returns top-K KG matches
  * ranking-delta tracker computes current vs previous SERP positions
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_event import AuditEvent
from app.models.ingestion import (
    DocumentChunk,
    IngestionSource,
    IngestionSourceType,
    IngestionStatus,
)
from app.models.organization import Organization
from app.services.mcp import MCPAdapterResult
from app.services.seo import audit as seo_audit
from app.services.seo import ranking_delta as seo_ranking
from app.services.seo.audit import list_audit_findings, run_site_audit
from app.services.seo.internal_linking import suggest_internal_links
from app.services.seo.ranking_delta import (
    ACTION_RANKING_SNAPSHOT,
    compute_ranking_delta,
    snapshot_keyword_positions,
)
from tests.conftest import test_engine


@pytest_asyncio.fixture
async def org():
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        o = Organization(slug="seo", name="SEO Co")
        session.add(o)
        await session.commit()
        await session.refresh(o)
        return o


# ---------- audit -----------------------------------------------------------


@pytest.mark.asyncio
async def test_site_audit_persists_findings(monkeypatch, org):
    async def fake_site_audit(session, *, organization_id, domain):
        return MCPAdapterResult(
            server="ahrefs",
            tool="site_audit",
            arguments={"domain": domain},
            result={
                "findings": [
                    {
                        "kind": "broken_link",
                        "severity": "high",
                        "url": f"https://{domain}/missing",
                        "detail": "404 not found",
                    },
                    {
                        "kind": "missing_meta",
                        "severity": "medium",
                        "url": f"https://{domain}/",
                        "detail": "no meta description",
                    },
                ]
            },
            duration_ms=12,
            stub=True,
        )

    monkeypatch.setattr(seo_audit, "site_audit", fake_site_audit)

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        summary = await run_site_audit(
            session, organization_id=org.id, domain="example.com"
        )
        await session.commit()

    assert summary["findings_count"] == 2
    assert summary["stub"] is True

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        rows = await list_audit_findings(
            session, organization_id=org.id, days=1, limit=10
        )
    assert len(rows) == 2
    kinds = sorted(r["kind"] for r in rows)
    assert kinds == ["broken_link", "missing_meta"]


# ---------- internal links --------------------------------------------------


@pytest.mark.asyncio
async def test_internal_link_suggester_returns_top_k(org):
    """Seed two URL sources with embedded chunks and confirm the
    suggester picks the matching one as top result.
    """
    from app.services.embeddings import embed_text

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        src_a = IngestionSource(
            organization_id=org.id,
            source_type=IngestionSourceType.url,
            source_reference="https://example.com/pricing",
            name="Pricing page",
            status=IngestionStatus.ready,
        )
        src_b = IngestionSource(
            organization_id=org.id,
            source_type=IngestionSourceType.url,
            source_reference="https://example.com/about",
            name="About",
            status=IngestionStatus.ready,
        )
        session.add_all([src_a, src_b])
        await session.flush()

        vec_a, _ = await embed_text("pricing details and enterprise tiers")
        vec_b, _ = await embed_text("founders biography and history")
        session.add_all([
            DocumentChunk(
                organization_id=org.id,
                source_id=src_a.id,
                position=0,
                text="Pricing details and enterprise tiers.",
                embedding=vec_a,
                embedding_model="stub/sha256",
            ),
            DocumentChunk(
                organization_id=org.id,
                source_id=src_b.id,
                position=0,
                text="Our founders started the company in 2024.",
                embedding=vec_b,
                embedding_model="stub/sha256",
            ),
        ])
        await session.commit()

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        out = await suggest_internal_links(
            session,
            organization_id=org.id,
            draft_text="pricing details and enterprise tiers",
            top_k=2,
        )

    assert len(out) == 2
    # The matching chunk should rank first.
    assert out[0]["source_reference"] == "https://example.com/pricing"
    assert out[0]["similarity"] > out[1]["similarity"]


@pytest.mark.asyncio
async def test_internal_link_suggester_empty_draft(org):
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        out = await suggest_internal_links(
            session, organization_id=org.id, draft_text="   "
        )
    assert out == []


# ---------- ranking delta ---------------------------------------------------


@pytest.mark.asyncio
async def test_ranking_snapshot_persists_audit_rows(monkeypatch, org):
    async def fake_serp(session, *, organization_id, keyword, country, limit):
        return MCPAdapterResult(
            server="ahrefs",
            tool="serp_overview",
            arguments={"keyword": keyword, "country": country, "limit": limit},
            result={
                "results": [
                    {"position": 1, "domain": "competitor.com", "url": "https://competitor.com"},
                    {"position": 5, "domain": "example.com", "url": "https://example.com/p"},
                ]
            },
            duration_ms=5,
            stub=True,
        )

    monkeypatch.setattr(seo_ranking, "serp_overview", fake_serp)

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        out = await snapshot_keyword_positions(
            session,
            organization_id=org.id,
            keywords=["dclaw", "marketing os"],
            country="us",
            own_domain="example.com",
        )
        await session.commit()

    assert len(out["snapshots"]) == 2
    assert all(s["own_position"] == 5 for s in out["snapshots"])

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        rows = (await session.execute(
            select(AuditEvent).where(
                AuditEvent.organization_id == org.id,
                AuditEvent.action_type == ACTION_RANKING_SNAPSHOT,
            )
        )).scalars().all()
    assert len(rows) == 2


@pytest.mark.asyncio
async def test_ranking_delta_compares_previous_to_current(org):
    """Seed an older snapshot at position 3 and a newer one at position
    8; the delta should be +5 (we moved down the SERP).
    """
    now = datetime.now(timezone.utc)
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        prev = AuditEvent(
            organization_id=org.id,
            actor_kind="system",
            actor_agent="seo_agent",
            action_type=ACTION_RANKING_SNAPSHOT,
            target_type="keyword",
            target_id="dclaw",
            payload_json={"keyword": "dclaw", "country": "us", "own_position": 3},
        )
        cur = AuditEvent(
            organization_id=org.id,
            actor_kind="system",
            actor_agent="seo_agent",
            action_type=ACTION_RANKING_SNAPSHOT,
            target_type="keyword",
            target_id="dclaw",
            payload_json={"keyword": "dclaw", "country": "us", "own_position": 8},
        )
        session.add_all([prev, cur])
        await session.flush()
        # Backdate the previous snapshot 10 days.
        prev.created_at = now - timedelta(days=10)
        cur.created_at = now
        await session.commit()

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        deltas = await compute_ranking_delta(
            session, organization_id=org.id, days=7
        )

    assert len(deltas) == 1
    d = deltas[0]
    assert d["keyword"] == "dclaw"
    assert d["current"] == 8
    assert d["previous"] == 3
    assert d["delta"] == 5
