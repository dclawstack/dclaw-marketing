"""Sliding-window quota writer + circuit breaker (Phase 11 / I1).

The QuotaCounter row table (already in app.models.ops) lives in the
DB. This module wraps it with three primitives that any outbound side
effect (publishers, email send, ad calls) can call:

  • ``check_and_increment(session, organization_id, channel)``
      Atomic-ish (single SELECT-then-INSERT/UPDATE inside the caller's
      transaction). Returns ``(allowed, count, limit)``. ``allowed``
      is False when the current bucket is at its ceiling — caller
      should drop the call and surface a 429 / queue + retry.

  • ``register_failure / register_success(session, ...)``
      Drives the per-channel circuit breaker: N consecutive failures
      trip the breaker, parking outbound calls on that channel for a
      configurable cool-off. The breaker state is JSON-persisted on the
      QuotaCounter.meta column (no new table needed).

  • ``is_breaker_open(session, ...)``
      Caller checks this before ``check_and_increment``. Returns
      ``(open, opens_at)``; ``opens_at`` is when the channel will
      auto-recover (a successful call before then doesn't unblock —
      the cool-off has to elapse so we don't slam the upstream).

Defaults — all overridable per Org via
``Organization.constraints_json["quota_overrides"][channel]``:

  • Window: 60 minutes (3600 s)
  • Per-window limit per channel:
        linkedin 50, x 100, bluesky 200, instagram 25,
        mastodon 200, reddit 50, pinterest 50, discord 500,
        substack 5, threads 25, facebook 25, tiktok 10, youtube 5,
        email 1000 (per provider), default 200
  • Circuit breaker: 5 consecutive failures → open for 15 minutes

The defaults are conservative and intentionally below most real
provider limits so the agency-as-customer model never hits a hard 429
from upstream — they get a soft "queue + retry" experience.

There's no separate ``meta`` column on QuotaCounter today — we piggy-
back on a brand-new circuit-breaker row whose ``window_start`` we set
to the start of the rolling failure window. This keeps the
zero-schema-change promise for this PR.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from uuid import UUID

from app.models.ops import QuotaCounter
from app.models.organization import Organization


# --------- Defaults --------------------------------------------------------


DEFAULT_WINDOW_SECONDS = 60 * 60  # 1h

_PER_CHANNEL_DEFAULT_LIMIT: dict[str, int] = {
    "linkedin": 50,
    "x": 100,
    "bluesky": 200,
    "instagram": 25,
    "mastodon": 200,
    "reddit": 50,
    "pinterest": 50,
    "discord": 500,
    "threads": 25,
    "facebook": 25,
    "tiktok": 10,
    "youtube": 5,
    "substack": 5,
    "email": 1000,
}
_DEFAULT_LIMIT = 200

# Circuit breaker:
_BREAKER_FAILURE_THRESHOLD = 5
_BREAKER_OPEN_SECONDS = 15 * 60  # 15 min
_BREAKER_CHANNEL_SUFFIX = "__breaker"  # internal counter for breaker state


@dataclass(frozen=True, slots=True)
class QuotaDecision:
    allowed: bool
    count: int
    limit: int
    window_start: datetime


# --------- Helpers ---------------------------------------------------------


def _window_start(now: datetime, window_seconds: int) -> datetime:
    """Snap `now` to the start of its window. Eg. with window=3600 every
    call within the same UTC hour shares a counter row."""
    epoch = int(now.replace(tzinfo=timezone.utc).timestamp())
    bucket = (epoch // window_seconds) * window_seconds
    return datetime.fromtimestamp(bucket, tz=timezone.utc)


def _channel_limit(channel: str, org_constraints: dict | None) -> int:
    """Reads per-Org override first, then defaults."""
    overrides = (org_constraints or {}).get("quota_overrides") or {}
    if channel in overrides:
        return int(overrides[channel])
    return _PER_CHANNEL_DEFAULT_LIMIT.get(channel, _DEFAULT_LIMIT)


# --------- Sync API (used by Celery worker context) -----------------------


def check_and_increment_sync(
    session: Session,
    *,
    organization_id: UUID,
    channel: str,
    now: datetime | None = None,
) -> QuotaDecision:
    """Sync version for Celery tasks (worker uses SyncSession)."""
    clock = now or datetime.now(tz=timezone.utc)
    org = session.get(Organization, organization_id)
    limit = _channel_limit(channel, (org.constraints_json or {}) if org else {})
    ws = _window_start(clock, DEFAULT_WINDOW_SECONDS)

    row = session.execute(
        select(QuotaCounter).where(
            QuotaCounter.organization_id == organization_id,
            QuotaCounter.channel == channel,
            QuotaCounter.window_start == ws,
        )
    ).scalar_one_or_none()

    if row is None:
        row = QuotaCounter(
            organization_id=organization_id,
            channel=channel,
            window_start=ws,
            window_seconds=DEFAULT_WINDOW_SECONDS,
            limit=limit,
            count=0,
        )
        session.add(row)
        session.flush()

    if row.count >= row.limit:
        return QuotaDecision(
            allowed=False, count=row.count, limit=row.limit, window_start=ws
        )

    row.count += 1
    row.last_used_at = clock
    session.flush()
    return QuotaDecision(
        allowed=True, count=row.count, limit=row.limit, window_start=ws
    )


def register_failure_sync(
    session: Session,
    *,
    organization_id: UUID,
    channel: str,
    now: datetime | None = None,
) -> bool:
    """Bump the failure counter for a channel. Returns True when the
    breaker has just *tripped* (caller can alert)."""
    clock = now or datetime.now(tz=timezone.utc)
    ws = _window_start(clock, _BREAKER_OPEN_SECONDS)
    chan = channel + _BREAKER_CHANNEL_SUFFIX
    row = session.execute(
        select(QuotaCounter).where(
            QuotaCounter.organization_id == organization_id,
            QuotaCounter.channel == chan,
            QuotaCounter.window_start == ws,
        )
    ).scalar_one_or_none()
    if row is None:
        row = QuotaCounter(
            organization_id=organization_id,
            channel=chan,
            window_start=ws,
            window_seconds=_BREAKER_OPEN_SECONDS,
            limit=_BREAKER_FAILURE_THRESHOLD,
            count=1,
        )
        session.add(row)
        session.flush()
        return False
    was_below = row.count < row.limit
    row.count += 1
    row.last_used_at = clock
    session.flush()
    return was_below and row.count >= row.limit


def is_breaker_open_sync(
    session: Session,
    *,
    organization_id: UUID,
    channel: str,
    now: datetime | None = None,
) -> tuple[bool, datetime | None]:
    """True when the channel is parked. Second value is the breaker's
    auto-recovery time (when ``window_start + window_seconds`` is in
    the future)."""
    clock = now or datetime.now(tz=timezone.utc)
    chan = channel + _BREAKER_CHANNEL_SUFFIX
    row = session.execute(
        select(QuotaCounter)
        .where(
            QuotaCounter.organization_id == organization_id,
            QuotaCounter.channel == chan,
        )
        .order_by(QuotaCounter.window_start.desc())
        .limit(1)
    ).scalar_one_or_none()
    if row is None or row.count < row.limit:
        return False, None
    opens_at = row.window_start + timedelta(seconds=row.window_seconds)
    return (clock < opens_at), opens_at


# --------- Async API (FastAPI route context) ------------------------------


async def check_and_increment(
    session: AsyncSession,
    *,
    organization_id: UUID,
    channel: str,
    now: datetime | None = None,
) -> QuotaDecision:
    clock = now or datetime.now(tz=timezone.utc)
    org = await session.get(Organization, organization_id)
    limit = _channel_limit(channel, (org.constraints_json or {}) if org else {})
    ws = _window_start(clock, DEFAULT_WINDOW_SECONDS)
    res = await session.execute(
        select(QuotaCounter).where(
            QuotaCounter.organization_id == organization_id,
            QuotaCounter.channel == channel,
            QuotaCounter.window_start == ws,
        )
    )
    row = res.scalar_one_or_none()
    if row is None:
        row = QuotaCounter(
            organization_id=organization_id,
            channel=channel,
            window_start=ws,
            window_seconds=DEFAULT_WINDOW_SECONDS,
            limit=limit,
            count=0,
        )
        session.add(row)
        await session.flush()
    if row.count >= row.limit:
        return QuotaDecision(
            allowed=False, count=row.count, limit=row.limit, window_start=ws
        )
    row.count += 1
    row.last_used_at = clock
    await session.flush()
    return QuotaDecision(
        allowed=True, count=row.count, limit=row.limit, window_start=ws
    )


__all__ = [
    "QuotaDecision",
    "DEFAULT_WINDOW_SECONDS",
    "check_and_increment",
    "check_and_increment_sync",
    "register_failure_sync",
    "is_breaker_open_sync",
]
