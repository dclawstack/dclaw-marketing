"""Phase 11 / I1 — Sliding-window QuotaCounter writer + circuit breaker tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.services.quota import (
    DEFAULT_WINDOW_SECONDS,
    check_and_increment,
    check_and_increment_sync,
    is_breaker_open_sync,
    register_failure_sync,
)
from tests.conftest import test_engine


@pytest.mark.asyncio
async def test_check_and_increment_increments_within_limit():
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        org = Organization(slug="q1", name="Q1")
        session.add(org)
        await session.flush()

        d1 = await check_and_increment(
            session, organization_id=org.id, channel="x"
        )
        d2 = await check_and_increment(
            session, organization_id=org.id, channel="x"
        )
        assert d1.allowed and d1.count == 1
        assert d2.allowed and d2.count == 2
        assert d1.limit == d2.limit


@pytest.mark.asyncio
async def test_check_and_increment_blocks_at_limit():
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        org = Organization(
            slug="q2",
            name="Q2",
            constraints_json={"quota_overrides": {"linkedin": 2}},
        )
        session.add(org)
        await session.flush()

        a = await check_and_increment(
            session, organization_id=org.id, channel="linkedin"
        )
        b = await check_and_increment(
            session, organization_id=org.id, channel="linkedin"
        )
        c = await check_and_increment(
            session, organization_id=org.id, channel="linkedin"
        )
        assert a.allowed and a.count == 1
        assert b.allowed and b.count == 2
        assert not c.allowed
        assert c.count == 2  # didn't bump after refusal
        assert c.limit == 2


@pytest.mark.asyncio
async def test_check_and_increment_separate_windows_separate_counters():
    """Two timestamps an hour apart roll over to a fresh bucket."""
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        org = Organization(slug="q3", name="Q3")
        session.add(org)
        await session.flush()

        now = datetime(2026, 5, 19, 12, 0, 0, tzinfo=timezone.utc)
        later = now + timedelta(seconds=DEFAULT_WINDOW_SECONDS + 60)

        d1 = await check_and_increment(
            session, organization_id=org.id, channel="x", now=now
        )
        d2 = await check_and_increment(
            session, organization_id=org.id, channel="x", now=later
        )
        assert d1.count == 1
        # New window → counter restarts at 1
        assert d2.count == 1
        assert d2.window_start != d1.window_start


def test_sync_increment_and_decision(monkeypatch):
    """Cover the sync code-path used by the Celery worker."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.base import Base

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine, expire_on_commit=False)

    with Session() as s:
        org = Organization(
            slug="qs", name="QS",
            constraints_json={"quota_overrides": {"discord": 2}},
        )
        s.add(org)
        s.flush()
        d1 = check_and_increment_sync(
            s, organization_id=org.id, channel="discord"
        )
        d2 = check_and_increment_sync(
            s, organization_id=org.id, channel="discord"
        )
        d3 = check_and_increment_sync(
            s, organization_id=org.id, channel="discord"
        )
        assert d1.allowed and d2.allowed and not d3.allowed


def test_circuit_breaker_trips_then_recovers():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.models.base import Base

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    Session = sessionmaker(engine, expire_on_commit=False)

    with Session() as s:
        org = Organization(slug="br", name="Br")
        s.add(org)
        s.flush()

        # Default failure threshold is 5.
        tripped = False
        for i in range(5):
            tripped = register_failure_sync(
                s, organization_id=org.id, channel="x"
            )
        assert tripped is True

        is_open, opens_at = is_breaker_open_sync(
            s, organization_id=org.id, channel="x"
        )
        assert is_open is True
        assert opens_at is not None

        # Advance well past the cool-off
        future = datetime.now(tz=timezone.utc) + timedelta(hours=2)
        is_open_later, _ = is_breaker_open_sync(
            s, organization_id=org.id, channel="x", now=future
        )
        assert is_open_later is False
