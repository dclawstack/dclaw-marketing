"""Attribution computation (Phase 8.3).

For every Conversion in the org, build the journey of Touchpoints
that preceded it (linked via ``Touchpoint.lead_id`` matching the
conversion's lead), then allocate credit across them under each
configured AttributionModel. Writes one ``AttributionResult`` row per
(conversion × touchpoint × model).

Models implemented in v1:
- ``first_touch``: 100% to the earliest touchpoint
- ``last_touch``:  100% to the latest touchpoint
- ``linear``:      equal share across all touchpoints

Time-decay and Markov-chain models land in a follow-up — they need a
half-life parameter and conversion-graph sampling respectively, which
deserve their own PRs.

The job is idempotent: it deletes any existing AttributionResult rows
for the (conversion, model) pair before writing new ones, so repeated
runs converge on the latest journey state.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.attribution import (
    AnalyticsRollup,
    AttributionModel,
    AttributionResult,
    Conversion,
    Touchpoint,
)
from app.models.organization import Organization
from app.worker.celery_app import celery_app
from app.worker.helpers import SyncSession


# Lookback window — touchpoints older than this don't get credit.
_LOOKBACK = timedelta(days=30)


def _touchpoints_for(
    session: Session, conv: Conversion
) -> list[Touchpoint]:
    """Returns touchpoints attributable to this conversion, ordered
    by occurred_at ascending.

    Currently joined on ``lead_id``; once identity resolution lands,
    we'll widen this to walk visitor_id → lead_id mappings.
    """
    if conv.lead_id is None:
        return []
    cutoff = conv.occurred_at - _LOOKBACK
    result = session.execute(
        select(Touchpoint)
        .where(
            Touchpoint.lead_id == conv.lead_id,
            Touchpoint.organization_id == conv.organization_id,
            Touchpoint.occurred_at >= cutoff,
            Touchpoint.occurred_at <= conv.occurred_at,
        )
        .order_by(Touchpoint.occurred_at.asc())
    )
    return list(result.scalars().all())


# Time-decay half-life (days). 7d is the industry-default — a touch
# 7 days before the conversion contributes 50%, 14d → 25%, etc.
_TIME_DECAY_HALF_LIFE_DAYS = 7.0


def _time_decay_weights(
    journey: list[Touchpoint], *, conversion_at
) -> dict[UUID, float]:
    """Exponential decay normalised so the per-touchpoint weights sum
    to 1.0. ``weight_raw = 0.5 ** (age_days / half_life)`` with
    ``age_days`` measured from the conversion timestamp.
    """
    if not journey:
        return {}
    raw: dict[UUID, float] = {}
    half = _TIME_DECAY_HALF_LIFE_DAYS
    for tp in journey:
        age = (conversion_at - tp.occurred_at).total_seconds() / 86400.0
        raw[tp.id] = 0.5 ** (max(0.0, age) / half)
    total = sum(raw.values())
    if total <= 0:
        # All weights are zero (edge case) — fall back to linear.
        share = 1.0 / len(journey)
        return {tp.id: share for tp in journey}
    return {tp_id: w / total for tp_id, w in raw.items()}


def _allocate(
    model: AttributionModel,
    journey: list[Touchpoint],
    *,
    conversion=None,
) -> dict[UUID, float]:
    """Returns a {touchpoint_id: weight} map summing to 1.0 (or 0.0
    if the journey is empty).
    """
    if not journey:
        return {}
    if model == AttributionModel.first_touch:
        return {journey[0].id: 1.0}
    if model == AttributionModel.last_touch:
        return {journey[-1].id: 1.0}
    if model == AttributionModel.linear:
        share = 1.0 / len(journey)
        return {tp.id: share for tp in journey}
    if model == AttributionModel.time_decay:
        if conversion is None:
            # Shouldn't happen in production — callers must pass conv;
            # fall back to linear so we don't silently lose journeys.
            share = 1.0 / len(journey)
            return {tp.id: share for tp in journey}
        return _time_decay_weights(
            journey, conversion_at=conversion.occurred_at
        )
    # markov: per-conversion Markov isn't meaningful (you need many
    # journeys to estimate transition probabilities). The population-
    # level Markov writer ships in a follow-up; for now return empty
    # so the beat task simply skips this model per row.
    return {}


_SUPPORTED_MODELS = (
    AttributionModel.first_touch,
    AttributionModel.last_touch,
    AttributionModel.linear,
    AttributionModel.time_decay,
)


def compute_for_conversion(session: Session, conv: Conversion) -> int:
    """Computes + persists attribution rows for one conversion.

    Returns the count of AttributionResult rows written across all
    supported models. Caller is responsible for the commit.
    """
    journey = _touchpoints_for(session, conv)
    written = 0
    for model in _SUPPORTED_MODELS:
        # Wipe any prior rows for this (conversion, model) — idempotent.
        session.execute(
            delete(AttributionResult).where(
                AttributionResult.conversion_id == conv.id,
                AttributionResult.model == model,
            )
        )
        weights = _allocate(model, journey, conversion=conv)
        for touchpoint_id, weight in weights.items():
            credited = (
                (conv.amount_usd or 0.0) * weight
                if conv.amount_usd is not None
                else None
            )
            session.add(
                AttributionResult(
                    organization_id=conv.organization_id,
                    conversion_id=conv.id,
                    touchpoint_id=touchpoint_id,
                    model=model,
                    weight=weight,
                    credited_amount_usd=credited,
                )
            )
            written += 1
    return written


@celery_app.task(name="app.worker.tasks.attribution.compute_attribution")
def compute_attribution(target_day_iso: str | None = None) -> dict:
    """Beat-driven: compute attribution for every conversion that
    occurred on the target UTC day (defaults to yesterday).

    Also emits a per-org rollup row of model-level credited revenue
    into AnalyticsRollup so the dashboard can plot model-vs-model
    side by side without recomputing.
    """
    if target_day_iso:
        target = datetime.fromisoformat(target_day_iso)
        if target.tzinfo is None:
            target = target.replace(tzinfo=timezone.utc)
    else:
        target = datetime.now(tz=timezone.utc) - timedelta(days=1)

    day_start = datetime(target.year, target.month, target.day, tzinfo=timezone.utc)
    day_end = day_start + timedelta(days=1)

    summary: dict = {
        "day": day_start.isoformat(),
        "conversions": 0,
        "rows_written": 0,
        "orgs_touched": 0,
    }

    with SyncSession() as session:
        orgs = session.execute(select(Organization.id)).all()
        for (org_id,) in orgs:
            convs = (
                session.execute(
                    select(Conversion).where(
                        Conversion.organization_id == org_id,
                        Conversion.occurred_at >= day_start,
                        Conversion.occurred_at < day_end,
                    )
                )
                .scalars()
                .all()
            )
            if not convs:
                continue

            org_rows = 0
            credited_by_model: dict[str, float] = {
                m.value: 0.0 for m in _SUPPORTED_MODELS
            }
            for conv in convs:
                org_rows += compute_for_conversion(session, conv)
                # Pre-compute the per-model credited revenue from the
                # just-written rows.
                for model in _SUPPORTED_MODELS:
                    row_sum = session.execute(
                        select(
                            AttributionResult.credited_amount_usd
                        ).where(
                            AttributionResult.conversion_id == conv.id,
                            AttributionResult.model == model,
                        )
                    ).all()
                    credited_by_model[model.value] += sum(
                        float(r[0] or 0.0) for r in row_sum
                    )

            # Upsert AnalyticsRollup with model-by-model summary
            existing = session.execute(
                select(AnalyticsRollup).where(
                    AnalyticsRollup.organization_id == org_id,
                    AnalyticsRollup.scope == "attribution_models",
                    AnalyticsRollup.scope_key == "summary",
                    AnalyticsRollup.day == day_start,
                )
            ).scalar_one_or_none()
            metric = {
                "conversions": len(convs),
                "credited_by_model": credited_by_model,
            }
            now = datetime.now(tz=timezone.utc)
            if existing is None:
                session.add(
                    AnalyticsRollup(
                        organization_id=org_id,
                        scope="attribution_models",
                        scope_key="summary",
                        day=day_start,
                        metric_json=metric,
                        computed_at=now,
                    )
                )
            else:
                existing.metric_json = metric
                existing.computed_at = now

            summary["conversions"] += len(convs)
            summary["rows_written"] += org_rows
            summary["orgs_touched"] += 1

        session.commit()

    return summary
