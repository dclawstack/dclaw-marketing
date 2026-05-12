"""Phase 4.3 + 4.4 — conflict detection + best-time recommender tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.models.attribution import AnalyticsRollup
from app.models.base import Base
from app.models.organization import Organization
from app.models.scheduled_post import (
    ScheduledPost,
    ScheduledPostChannel,
    ScheduledPostStatus,
)
from app.services.scheduling import (
    BestTimeSuggestion,
    ConflictResult,
    _FALLBACK_HOURS_UTC,
    _cooldown_for,
    check_conflict,
    suggest_best_time,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


@pytest_asyncio.fixture()
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        yield s
    await engine.dispose()


async def _org(s: AsyncSession) -> Organization:
    o = Organization(slug=f"o-{uuid4().hex[:8]}", name="T", is_external=False)
    s.add(o)
    await s.commit()
    await s.refresh(o)
    return o


async def _post(
    s: AsyncSession,
    org,
    *,
    channel: ScheduledPostChannel,
    when: datetime,
    status: ScheduledPostStatus = ScheduledPostStatus.queued,
    save: bool = True,
) -> ScheduledPost:
    p = ScheduledPost(
        organization_id=org.id,
        channel=channel,
        scheduled_at=when,
        status=status,
    )
    if save:
        s.add(p)
        await s.commit()
        await s.refresh(p)
    return p


# ---------- _cooldown_for --------------------------------------------


def test_cooldown_for_known_channels():
    assert _cooldown_for(ScheduledPostChannel.linkedin) == 60
    assert _cooldown_for(ScheduledPostChannel.x) == 15
    assert _cooldown_for(ScheduledPostChannel.discord) == 5


def test_cooldown_for_unknown_defaults_60():
    assert _cooldown_for(ScheduledPostChannel.blog) == 60


# ---------- check_conflict -------------------------------------------


@pytest.mark.asyncio
async def test_no_conflict_when_alone(session):
    org = await _org(session)
    now = datetime.now(tz=timezone.utc)
    p = ScheduledPost(
        organization_id=org.id,
        channel=ScheduledPostChannel.linkedin,
        scheduled_at=now,
        status=ScheduledPostStatus.queued,
    )
    res = await check_conflict(session, p)
    assert res.in_conflict is False
    assert res.conflicting_post_id is None
    assert res.cooldown_minutes == 60


@pytest.mark.asyncio
async def test_conflict_within_cooldown(session):
    org = await _org(session)
    base = datetime.now(tz=timezone.utc).replace(microsecond=0)
    # Existing post at T+0
    existing = await _post(
        session, org, channel=ScheduledPostChannel.linkedin, when=base
    )
    # New post at T+30min — within LinkedIn's 60min cooldown
    new = ScheduledPost(
        organization_id=org.id,
        channel=ScheduledPostChannel.linkedin,
        scheduled_at=base + timedelta(minutes=30),
        status=ScheduledPostStatus.queued,
    )
    res = await check_conflict(session, new)
    assert res.in_conflict is True
    assert res.conflicting_post_id == existing.id
    assert res.minutes_to_next == 30


@pytest.mark.asyncio
async def test_no_conflict_just_outside_cooldown(session):
    org = await _org(session)
    base = datetime.now(tz=timezone.utc).replace(microsecond=0)
    await _post(session, org, channel=ScheduledPostChannel.linkedin, when=base)
    new = ScheduledPost(
        organization_id=org.id,
        channel=ScheduledPostChannel.linkedin,
        scheduled_at=base + timedelta(minutes=61),
        status=ScheduledPostStatus.queued,
    )
    res = await check_conflict(session, new)
    assert res.in_conflict is False


@pytest.mark.asyncio
async def test_cancelled_post_ignored(session):
    org = await _org(session)
    base = datetime.now(tz=timezone.utc).replace(microsecond=0)
    await _post(
        session, org,
        channel=ScheduledPostChannel.linkedin,
        when=base,
        status=ScheduledPostStatus.cancelled,
    )
    new = ScheduledPost(
        organization_id=org.id,
        channel=ScheduledPostChannel.linkedin,
        scheduled_at=base + timedelta(minutes=30),
        status=ScheduledPostStatus.queued,
    )
    res = await check_conflict(session, new)
    assert res.in_conflict is False


@pytest.mark.asyncio
async def test_different_channel_no_conflict(session):
    org = await _org(session)
    base = datetime.now(tz=timezone.utc).replace(microsecond=0)
    await _post(session, org, channel=ScheduledPostChannel.linkedin, when=base)
    new = ScheduledPost(
        organization_id=org.id,
        channel=ScheduledPostChannel.x,
        scheduled_at=base + timedelta(minutes=10),
        status=ScheduledPostStatus.queued,
    )
    res = await check_conflict(session, new)
    assert res.in_conflict is False


@pytest.mark.asyncio
async def test_different_org_no_conflict(session):
    org_a = await _org(session)
    org_b = await _org(session)
    base = datetime.now(tz=timezone.utc).replace(microsecond=0)
    await _post(session, org_a, channel=ScheduledPostChannel.linkedin, when=base)
    new = ScheduledPost(
        organization_id=org_b.id,
        channel=ScheduledPostChannel.linkedin,
        scheduled_at=base + timedelta(minutes=10),
        status=ScheduledPostStatus.queued,
    )
    res = await check_conflict(session, new)
    assert res.in_conflict is False


@pytest.mark.asyncio
async def test_self_excluded_when_id_set(session):
    """Editing an existing post shouldn't conflict with itself."""
    org = await _org(session)
    base = datetime.now(tz=timezone.utc).replace(microsecond=0)
    p = await _post(session, org, channel=ScheduledPostChannel.linkedin, when=base)
    res = await check_conflict(session, p)
    assert res.in_conflict is False


@pytest.mark.asyncio
async def test_explicit_cooldown_override(session):
    org = await _org(session)
    base = datetime.now(tz=timezone.utc).replace(microsecond=0)
    await _post(session, org, channel=ScheduledPostChannel.x, when=base)
    new = ScheduledPost(
        organization_id=org.id,
        channel=ScheduledPostChannel.x,
        scheduled_at=base + timedelta(minutes=20),
        status=ScheduledPostStatus.queued,
    )
    # X default cooldown is 15min — 20min apart would be FINE.
    # But if we override to 30min, it conflicts.
    res_default = await check_conflict(session, new)
    assert res_default.in_conflict is False
    res_override = await check_conflict(session, new, min_minutes_between=30)
    assert res_override.in_conflict is True
    assert res_override.cooldown_minutes == 30


# ---------- suggest_best_time ----------------------------------------


@pytest.mark.asyncio
async def test_suggest_uses_fallback_when_no_rollups(session):
    org = await _org(session)
    suggestions = await suggest_best_time(
        session,
        organization_id=org.id,
        channel=ScheduledPostChannel.linkedin,
        top_k=3,
    )
    assert len(suggestions) == 3
    # All in the future
    now = datetime.now(tz=timezone.utc)
    for s in suggestions:
        assert s.when > now
    # Scores monotonically non-increasing
    assert suggestions[0].score >= suggestions[1].score >= suggestions[2].score
    # Hours match the fallback table
    expected_hours = _FALLBACK_HOURS_UTC[ScheduledPostChannel.linkedin]
    assert {s.when.hour for s in suggestions} <= set(expected_hours)


@pytest.mark.asyncio
async def test_suggest_top_k_respected(session):
    org = await _org(session)
    s = await suggest_best_time(
        session,
        organization_id=org.id,
        channel=ScheduledPostChannel.x,
        top_k=5,
    )
    assert len(s) == 5


@pytest.mark.asyncio
async def test_suggest_uses_rollups_when_present(session):
    org = await _org(session)
    # Add some AnalyticsRollup history to boost confidence score
    day = datetime.now(tz=timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    for i in range(7):
        session.add(
            AnalyticsRollup(
                organization_id=org.id,
                scope="channel",
                scope_key="linkedin",
                day=day - timedelta(days=i),
                metric_json={"touchpoints": 500},
                computed_at=day,
            )
        )
    await session.commit()
    s = await suggest_best_time(
        session,
        organization_id=org.id,
        channel=ScheduledPostChannel.linkedin,
        top_k=3,
    )
    assert len(s) == 3
    # With 7 days × 500 touchpoints = 3500, score should be at the cap (1.0)
    assert s[0].score == 1.0


@pytest.mark.asyncio
async def test_suggest_returns_dataclass(session):
    org = await _org(session)
    s = await suggest_best_time(
        session,
        organization_id=org.id,
        channel=ScheduledPostChannel.linkedin,
        top_k=1,
    )
    assert isinstance(s[0], BestTimeSuggestion)
    assert isinstance(s[0].when, datetime)
    assert isinstance(s[0].score, float)
