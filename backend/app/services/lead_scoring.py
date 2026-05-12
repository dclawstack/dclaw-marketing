"""Lead scoring (Phase 8.8).

Computes a 0–100 score for a Lead based on its LeadActivity timeline
and a few intrinsic Lead fields. The scoring function is pure — pass
in a Lead-like dict + the list of activities and you get a number
back.

Per-activity weights (additive, before decay):

    form_submit         +25
    meeting             +30
    call                +25
    email_reply         +20
    email_click         +15
    page_view           + 8
    email_open          + 5
    crm_sync            + 4   (small bump per CRM round-trip)
    enrichment          + 6   (data enrichment hit)
    stage_change        + 0   (recorded but doesn't move the needle)
    status_change       + 0
    note                + 1
    other               + 0

Decay: each activity's weight is multiplied by ``0.95 ** age_days``
(rounded to 30-day cap). A 30-day-old form-submit contributes
``25 * 0.95**30 ≈ 5.3`` points instead of 25.

Intrinsic Lead bumps (added once, no decay):

    + 5 if domain is set
    +10 if linkedin_url is set
    +10 if company is set
    + 5 if phone is set

Final score is clamped to [0, 100] and rounded to 1 decimal place.

Stage influence: visitor/new caps lower; mql/sql/customer caps raise
ceilings to ensure stage and score don't diverge wildly:

    visitor   → max 50
    new       → max 75
    mql / sql → max 100
    customer  → max 100
    churned   → max 30 (cooling-off)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from app.models.lead import LeadActivityKind, LeadStage


_ACTIVITY_WEIGHTS: dict[LeadActivityKind, float] = {
    LeadActivityKind.form_submit: 25.0,
    LeadActivityKind.meeting: 30.0,
    LeadActivityKind.call: 25.0,
    LeadActivityKind.email_reply: 20.0,
    LeadActivityKind.email_click: 15.0,
    LeadActivityKind.page_view: 8.0,
    LeadActivityKind.email_open: 5.0,
    LeadActivityKind.crm_sync: 4.0,
    LeadActivityKind.enrichment: 6.0,
    LeadActivityKind.stage_change: 0.0,
    LeadActivityKind.status_change: 0.0,
    LeadActivityKind.note: 1.0,
    LeadActivityKind.other: 0.0,
}

_INTRINSIC_BUMPS: dict[str, float] = {
    "domain": 5.0,
    "linkedin_url": 10.0,
    "company": 10.0,
    "phone": 5.0,
}

_STAGE_CEILING: dict[LeadStage, float] = {
    LeadStage.visitor: 50.0,
    LeadStage.new: 75.0,
    LeadStage.mql: 100.0,
    LeadStage.sql: 100.0,
    LeadStage.customer: 100.0,
    LeadStage.churned: 30.0,
}

_DECAY_PER_DAY = 0.95
_MAX_AGE_DAYS = 30


@dataclass(frozen=True, slots=True)
class ScoredActivity:
    kind: LeadActivityKind
    age_days: float
    raw_weight: float
    decayed_weight: float


@dataclass(frozen=True, slots=True)
class LeadScore:
    score: float
    intrinsic_contribution: float
    activity_contribution: float
    scored_activities: list[ScoredActivity]
    ceiling: float


def _decay(weight: float, age_days: float) -> float:
    age = max(0.0, min(age_days, _MAX_AGE_DAYS))
    return weight * (_DECAY_PER_DAY ** age)


def compute_score(
    lead: dict,
    activities: Iterable,
    *,
    now: datetime | None = None,
) -> LeadScore:
    """Pure function. Returns a LeadScore breakdown.

    Args:
        lead: dict with optional keys: stage, domain, linkedin_url,
            company, phone.
        activities: iterable of activity-like objects with .kind and
            .occurred_at attributes.
        now: clock override for tests; defaults to UTC now.
    """
    clock = now if now is not None else datetime.now(tz=timezone.utc)

    # 1) Intrinsic
    intrinsic = 0.0
    for field, bump in _INTRINSIC_BUMPS.items():
        v = lead.get(field)
        if v is not None and v != "":
            intrinsic += bump

    # 2) Per-activity, with decay
    scored: list[ScoredActivity] = []
    activity_total = 0.0
    for a in activities:
        kind = a.kind
        # Allow string fallback for tests that pass simple objects
        if isinstance(kind, str):
            try:
                kind = LeadActivityKind(kind)
            except ValueError:
                kind = LeadActivityKind.other
        raw = _ACTIVITY_WEIGHTS.get(kind, 0.0)
        if raw <= 0:
            continue
        occurred = a.occurred_at
        if occurred.tzinfo is None:
            occurred = occurred.replace(tzinfo=timezone.utc)
        age_days = (clock - occurred).total_seconds() / 86400.0
        decayed = _decay(raw, age_days)
        scored.append(
            ScoredActivity(
                kind=kind,
                age_days=round(age_days, 2),
                raw_weight=raw,
                decayed_weight=round(decayed, 2),
            )
        )
        activity_total += decayed

    # 3) Stage ceiling
    stage = lead.get("stage")
    if isinstance(stage, str):
        try:
            stage = LeadStage(stage)
        except ValueError:
            stage = LeadStage.new
    ceiling = _STAGE_CEILING.get(stage or LeadStage.new, 100.0)

    raw_total = intrinsic + activity_total
    final = max(0.0, min(ceiling, raw_total))

    return LeadScore(
        score=round(final, 1),
        intrinsic_contribution=round(intrinsic, 1),
        activity_contribution=round(activity_total, 1),
        scored_activities=scored,
        ceiling=ceiling,
    )


__all__ = ["compute_score", "LeadScore", "ScoredActivity"]
