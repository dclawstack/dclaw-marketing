"""Phase 8.1 — daily rollup unit tests.

We use a SQLite in-memory engine because the existing setup_db fixture
points at a Postgres test DB that may or may not be available in unit
mode. Override the autouse fixture with a fresh in-memory schema for
each test.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.attribution import Conversion, Touchpoint
from app.models.base import Base
from app.models.organization import Organization
from app.worker.tasks.analytics import compute_rollup_for_day


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


@pytest.fixture()
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _make_org(session: Session) -> Organization:
    org = Organization(
        slug=f"o-{uuid4().hex[:8]}",
        name="Test Org",
        is_external=False,
    )
    session.add(org)
    session.commit()
    session.refresh(org)
    return org


def test_empty_day_returns_only_org_summary(session: Session):
    org = _make_org(session)
    day = datetime(2026, 5, 11, 12, tzinfo=timezone.utc)
    rollups = compute_rollup_for_day(session, org.id, day)
    # No touchpoints, no conversions → just one org-scope summary row
    assert len(rollups) == 1
    assert rollups[0]["scope"] == "org"
    assert rollups[0]["metric_json"]["touchpoints"] == 0
    assert rollups[0]["metric_json"]["conversions"] == 0
    assert rollups[0]["metric_json"]["revenue_usd"] == 0.0


def test_touchpoints_aggregate_by_channel(session: Session):
    org = _make_org(session)
    day = datetime(2026, 5, 11, 12, tzinfo=timezone.utc)
    # Two channels, three touchpoints from two visitors
    for ch, visitor in [
        ("twitter", "v1"),
        ("twitter", "v1"),  # repeat visitor on twitter
        ("linkedin", "v2"),
    ]:
        session.add(
            Touchpoint(
                organization_id=org.id,
                source="pixel",
                channel=ch,
                visitor_id=visitor,
                occurred_at=day,
            )
        )
    session.commit()

    rollups = compute_rollup_for_day(session, org.id, day)
    by_key = {r["scope_key"]: r for r in rollups if r["scope"] == "channel"}
    assert by_key["twitter"]["metric_json"] == {"touchpoints": 2, "uniques": 1}
    assert by_key["linkedin"]["metric_json"] == {"touchpoints": 1, "uniques": 1}

    org_row = next(r for r in rollups if r["scope"] == "org")
    assert org_row["metric_json"]["touchpoints"] == 3


def test_conversions_sum_into_org_revenue(session: Session):
    org = _make_org(session)
    day = datetime(2026, 5, 11, 12, tzinfo=timezone.utc)
    session.add_all(
        [
            Conversion(
                organization_id=org.id,
                kind="purchase",
                amount_usd=49.99,
                occurred_at=day,
            ),
            Conversion(
                organization_id=org.id,
                kind="purchase",
                amount_usd=125.00,
                occurred_at=day,
            ),
        ]
    )
    session.commit()
    rollups = compute_rollup_for_day(session, org.id, day)
    org_row = next(r for r in rollups if r["scope"] == "org")
    assert org_row["metric_json"]["conversions"] == 2
    assert org_row["metric_json"]["revenue_usd"] == pytest.approx(174.99)


def test_only_counts_within_day_bounds(session: Session):
    org = _make_org(session)
    target_day = datetime(2026, 5, 11, 12, tzinfo=timezone.utc)
    # Add a touchpoint the day before — must be excluded
    yesterday = target_day - timedelta(days=1)
    session.add(
        Touchpoint(
            organization_id=org.id,
            source="pixel",
            channel="x",
            visitor_id="vY",
            occurred_at=yesterday,
        )
    )
    # And one inside the target day
    session.add(
        Touchpoint(
            organization_id=org.id,
            source="pixel",
            channel="x",
            visitor_id="vT",
            occurred_at=target_day,
        )
    )
    session.commit()
    rollups = compute_rollup_for_day(session, org.id, target_day)
    org_row = next(r for r in rollups if r["scope"] == "org")
    assert org_row["metric_json"]["touchpoints"] == 1
