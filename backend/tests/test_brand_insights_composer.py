"""§6.2 follow-up — BrandKitInsight system-prompt composition.

Covers the helper layer (`app.agents.brand_style.fetch_brand_insights`
+ `format_insights_block`). End-to-end wiring into the Creatives Agent
system prompt is exercised in `test_agents.py` once integration tests
are extended.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.brand_style import fetch_brand_insights, format_insights_block
from app.models.brand_kit import BrandKit
from app.models.brand_kit_insight import BrandKitInsight, BrandKitInsightKind
from app.models.organization import Organization
from tests.conftest import test_engine


@pytest_asyncio.fixture
async def kit_with_insights():
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        org = Organization(slug="bi", name="BI Co")
        session.add(org)
        await session.flush()
        kit = BrandKit(
            organization_id=org.id,
            version=1,
            is_active=True,
            palette_json={},
            fonts_json={},
            voice_json={},
            positioning_json={},
        )
        session.add(kit)
        await session.flush()

        # Three insights with varying confidence + one archived + one
        # below the floor so we can verify filtering.
        session.add_all([
            BrandKitInsight(
                organization_id=org.id,
                brand_kit_id=kit.id,
                kind=BrandKitInsightKind.performance,
                summary="Posts shipped Tue 10am UTC outperform Mon by 38%.",
                confidence=0.92,
            ),
            BrandKitInsight(
                organization_id=org.id,
                brand_kit_id=kit.id,
                kind=BrandKitInsightKind.voice,
                summary="Sentences <20 words drive higher engagement on LinkedIn.",
                confidence=0.81,
            ),
            BrandKitInsight(
                organization_id=org.id,
                brand_kit_id=kit.id,
                kind=BrandKitInsightKind.hashtag,
                summary="#AgenticAI consistently appears in top-3 by reach.",
                confidence=0.66,
            ),
            BrandKitInsight(
                organization_id=org.id,
                brand_kit_id=kit.id,
                kind=BrandKitInsightKind.other,
                summary="(archived) old hypothesis; ignore.",
                confidence=0.95,
                is_archived=True,
            ),
            BrandKitInsight(
                organization_id=org.id,
                brand_kit_id=kit.id,
                kind=BrandKitInsightKind.audience,
                summary="Low-confidence noise.",
                confidence=0.40,
            ),
        ])
        await session.commit()
        await session.refresh(kit)
        return kit


@pytest.mark.asyncio
async def test_fetch_brand_insights_orders_and_filters(kit_with_insights):
    kit = kit_with_insights
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        insights = await fetch_brand_insights(
            session, brand_kit_id=kit.id, top_k=5, min_confidence=0.6
        )

    # Archived + below-floor entries excluded; highest confidence first.
    assert len(insights) == 3
    assert insights[0]["confidence"] >= insights[1]["confidence"]
    summaries = [i["summary"] for i in insights]
    assert "Posts shipped Tue 10am UTC outperform Mon by 38%." in summaries
    assert all("archived" not in s.lower() for s in summaries)
    assert all("noise" not in s.lower() for s in summaries)


@pytest.mark.asyncio
async def test_format_insights_block_renders_or_empty():
    out = format_insights_block([
        {"kind": "performance", "summary": "Mondays are bad.", "confidence": 0.9},
    ])
    assert "INSIGHTS LEARNED FROM PRIOR RUNS" in out
    assert "Mondays are bad." in out
    assert "performance" in out

    # Empty list short-circuits.
    assert format_insights_block([]) == ""
