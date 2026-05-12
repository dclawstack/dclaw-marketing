"""Daily analytics rollup task (Phase 8.1).

Aggregates yesterday's Touchpoints + Conversions per org+channel into
AnalyticsRollup rows. The Analyst Agent and the /analytics dashboard
read from these rollups instead of scanning the raw event tables.

Run via Celery Beat — see ``app.worker.celery_app.beat_schedule``.
The job is idempotent: re-running for the same (org, scope, scope_key,
day) updates the existing rollup row.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.attribution import AnalyticsRollup, Conversion, Touchpoint
from app.models.organization import Organization
from app.worker.celery_app import celery_app
from app.worker.helpers import SyncSession


def _day_bounds(target_day: datetime) -> tuple[datetime, datetime]:
    """Inclusive start, exclusive end of the UTC day containing target_day."""
    start = datetime(
        target_day.year, target_day.month, target_day.day, tzinfo=timezone.utc
    )
    return start, start + timedelta(days=1)


def compute_rollup_for_day(
    session: Session, organization_id: UUID, day: datetime
) -> list[dict]:
    """Builds per-channel rollups for one org for one UTC day.

    Returns a list of {scope, scope_key, metric_json} dicts. The
    caller persists them as AnalyticsRollup rows (or updates in place).
    """
    start, end = _day_bounds(day)

    # ----- Per-channel touchpoint counts -----
    tp_rows = session.execute(
        select(
            func.coalesce(Touchpoint.channel, "unknown").label("channel"),
            func.count().label("count"),
            func.count(func.distinct(Touchpoint.visitor_id)).label("uniques"),
        )
        .where(
            Touchpoint.organization_id == organization_id,
            Touchpoint.occurred_at >= start,
            Touchpoint.occurred_at < end,
        )
        .group_by("channel")
    ).all()

    # ----- Conversions: total count + revenue -----
    conv_row = session.execute(
        select(
            func.count().label("count"),
            func.coalesce(func.sum(Conversion.amount_usd), 0.0).label("revenue"),
        ).where(
            Conversion.organization_id == organization_id,
            Conversion.occurred_at >= start,
            Conversion.occurred_at < end,
        )
    ).one()

    rollups: list[dict] = []

    # One row per channel
    for r in tp_rows:
        rollups.append(
            {
                "scope": "channel",
                "scope_key": str(r.channel),
                "metric_json": {
                    "touchpoints": int(r.count or 0),
                    "uniques": int(r.uniques or 0),
                },
            }
        )

    # Org-wide summary row
    rollups.append(
        {
            "scope": "org",
            "scope_key": str(organization_id),
            "metric_json": {
                "touchpoints": sum(int(r.count or 0) for r in tp_rows),
                "uniques_sum_by_channel": sum(int(r.uniques or 0) for r in tp_rows),
                "conversions": int(conv_row.count or 0),
                "revenue_usd": float(conv_row.revenue or 0.0),
            },
        }
    )

    return rollups


def _upsert_rollup(
    session: Session,
    *,
    organization_id: UUID,
    scope: str,
    scope_key: str,
    day: datetime,
    metric_json: dict,
) -> None:
    start, _ = _day_bounds(day)
    existing = session.execute(
        select(AnalyticsRollup).where(
            AnalyticsRollup.organization_id == organization_id,
            AnalyticsRollup.scope == scope,
            AnalyticsRollup.scope_key == scope_key,
            AnalyticsRollup.day == start,
        )
    ).scalar_one_or_none()

    now = datetime.now(tz=timezone.utc)
    if existing is None:
        session.add(
            AnalyticsRollup(
                organization_id=organization_id,
                scope=scope,
                scope_key=scope_key,
                day=start,
                metric_json=metric_json,
                computed_at=now,
            )
        )
    else:
        existing.metric_json = metric_json
        existing.computed_at = now


@celery_app.task(name="app.worker.tasks.analytics.compute_daily_rollups")
def compute_daily_rollups(target_day_iso: str | None = None) -> dict:
    """Beat-driven: build yesterday's rollups for every org.

    Idempotent — running twice in a day overwrites the same row. If
    ``target_day_iso`` is supplied, computes for that specific UTC
    day instead of yesterday (useful for backfills).
    """
    if target_day_iso:
        target = datetime.fromisoformat(target_day_iso)
        if target.tzinfo is None:
            target = target.replace(tzinfo=timezone.utc)
    else:
        target = datetime.now(tz=timezone.utc) - timedelta(days=1)

    total = 0
    org_count = 0
    with SyncSession() as session:
        orgs = session.execute(select(Organization.id)).all()
        for (org_id,) in orgs:
            rollups = compute_rollup_for_day(session, org_id, target)
            for r in rollups:
                _upsert_rollup(
                    session,
                    organization_id=org_id,
                    scope=r["scope"],
                    scope_key=r["scope_key"],
                    day=target,
                    metric_json=r["metric_json"],
                )
                total += 1
            org_count += 1
        session.commit()

    return {
        "day": _day_bounds(target)[0].isoformat(),
        "orgs": org_count,
        "rollups_upserted": total,
    }
