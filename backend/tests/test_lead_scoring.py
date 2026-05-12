"""Phase 8.8 — Lead scoring unit tests."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio

from app.models.lead import LeadActivityKind, LeadStage
from app.services.lead_scoring import (
    _MAX_AGE_DAYS,
    LeadScore,
    compute_score,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


@dataclass
class FakeActivity:
    kind: LeadActivityKind
    occurred_at: datetime


NOW = datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc)


def _act(kind: LeadActivityKind, days_ago: float = 0.0) -> FakeActivity:
    return FakeActivity(kind=kind, occurred_at=NOW - timedelta(days=days_ago))


# ---------- intrinsic --------------------------------------------------


def test_empty_lead_zero_score():
    s = compute_score({}, [], now=NOW)
    assert s.score == 0.0
    assert s.intrinsic_contribution == 0.0
    assert s.activity_contribution == 0.0


def test_intrinsic_bumps():
    s = compute_score(
        {
            "domain": "example.com",
            "linkedin_url": "https://linkedin/x",
            "company": "Acme",
            "phone": "+1-555",
        },
        [],
        now=NOW,
    )
    # 5 + 10 + 10 + 5 = 30
    assert s.intrinsic_contribution == 30.0
    # Stage default 'new' caps at 75, so 30 is well within
    assert s.score == 30.0


def test_intrinsic_skips_empty_strings():
    s = compute_score(
        {"domain": "", "linkedin_url": None, "company": "Acme"},
        [],
        now=NOW,
    )
    assert s.intrinsic_contribution == 10.0  # company only


# ---------- per-activity weights --------------------------------------


def test_form_submit_today_is_25():
    s = compute_score({}, [_act(LeadActivityKind.form_submit, days_ago=0)], now=NOW)
    assert s.activity_contribution == 25.0
    assert s.score == 25.0


def test_meeting_today_is_30():
    s = compute_score({}, [_act(LeadActivityKind.meeting, days_ago=0)], now=NOW)
    assert s.activity_contribution == 30.0


def test_email_open_today_is_5():
    s = compute_score({}, [_act(LeadActivityKind.email_open, days_ago=0)], now=NOW)
    assert s.activity_contribution == 5.0


def test_zero_weight_kinds_skipped():
    s = compute_score(
        {},
        [
            _act(LeadActivityKind.stage_change, days_ago=0),
            _act(LeadActivityKind.status_change, days_ago=0),
            _act(LeadActivityKind.other, days_ago=0),
        ],
        now=NOW,
    )
    assert s.activity_contribution == 0.0
    assert len(s.scored_activities) == 0


def test_multiple_activities_summed():
    s = compute_score(
        {},
        [
            _act(LeadActivityKind.form_submit, 0),
            _act(LeadActivityKind.email_click, 0),
            _act(LeadActivityKind.email_open, 0),
        ],
        now=NOW,
    )
    # 25 + 15 + 5 = 45
    assert s.activity_contribution == 45.0


# ---------- decay ------------------------------------------------------


def test_decay_5pct_per_day():
    s = compute_score(
        {}, [_act(LeadActivityKind.form_submit, days_ago=1)], now=NOW
    )
    # 25 * 0.95**1 = 23.75 — rounded to 1dp during reporting
    assert s.activity_contribution == pytest.approx(23.75, abs=0.1)


def test_decay_caps_at_30_days():
    """Activities older than 30 days decay no further."""
    s_30 = compute_score(
        {}, [_act(LeadActivityKind.form_submit, days_ago=30)], now=NOW
    ).activity_contribution
    s_60 = compute_score(
        {}, [_act(LeadActivityKind.form_submit, days_ago=60)], now=NOW
    ).activity_contribution
    assert s_30 == s_60  # capped


def test_future_activity_treated_as_zero_age():
    """Negative age (future date) clamps to age 0."""
    future = FakeActivity(
        kind=LeadActivityKind.form_submit,
        occurred_at=NOW + timedelta(days=5),
    )
    s = compute_score({}, [future], now=NOW)
    # Full weight (no decay)
    assert s.activity_contribution == 25.0


# ---------- stage ceilings --------------------------------------------


def test_stage_visitor_caps_at_50():
    activities = [_act(LeadActivityKind.form_submit, 0)] * 5  # 5 × 25 = 125
    s = compute_score(
        {"stage": LeadStage.visitor}, activities, now=NOW
    )
    assert s.score == 50.0
    assert s.ceiling == 50.0


def test_stage_mql_no_ceiling():
    activities = [_act(LeadActivityKind.form_submit, 0)] * 5
    s = compute_score(
        {"stage": LeadStage.mql}, activities, now=NOW
    )
    assert s.score == 100.0
    assert s.ceiling == 100.0


def test_stage_churned_caps_at_30():
    activities = [_act(LeadActivityKind.form_submit, 0)] * 5
    s = compute_score(
        {"stage": LeadStage.churned}, activities, now=NOW
    )
    assert s.score == 30.0


def test_stage_string_value_accepted():
    """Stage passed as a string (e.g. from JSON) is converted."""
    s = compute_score(
        {"stage": "mql"},
        [_act(LeadActivityKind.form_submit, 0)] * 5,
        now=NOW,
    )
    assert s.score == 100.0


# ---------- shape ------------------------------------------------------


def test_returns_lead_score_dataclass():
    s = compute_score({}, [_act(LeadActivityKind.email_open, 0)], now=NOW)
    assert isinstance(s, LeadScore)
    assert len(s.scored_activities) == 1
    a = s.scored_activities[0]
    assert a.kind == LeadActivityKind.email_open
    assert a.raw_weight == 5.0


def test_score_rounded_to_one_decimal():
    s = compute_score(
        {}, [_act(LeadActivityKind.form_submit, 0.3)], now=NOW
    )
    # 25 * 0.95**0.3 ≈ 24.62 → rounded to 24.6
    assert s.score == round(s.score, 1)
