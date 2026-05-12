"""Phase 11 / I3 — cost-cap evaluator + confidence-threshold tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.models.ops import CostLedger
from app.models.organization import Organization
from app.services.cost_caps import (
    confidence_threshold_for,
    evaluate_caps_sync,
    should_escalate,
)


def _session():
    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng)
    return sessionmaker(eng, expire_on_commit=False)()


def test_no_cap_returns_no_cap_state():
    with _session() as s:
        org = Organization(slug="x", name="x")
        s.add(org)
        s.flush()
        states = evaluate_caps_sync(s, org.id)
        assert all(st.state == "no_cap" for st in states)
        assert all(st.pct_of_cap is None for st in states)


def test_warn_when_above_80_pct_daily():
    with _session() as s:
        org = Organization(
            slug="x",
            name="x",
            autonomy_posture_json={"daily_cap_usd": 100.0},
        )
        s.add(org)
        s.flush()
        # Spend $85 today.
        for _ in range(85):
            s.add(
                CostLedger(
                    organization_id=org.id,
                    provider="x",
                    kind="x",
                    amount_usd=1.0,
                )
            )
        s.flush()
        states = evaluate_caps_sync(s, org.id)
        day = [st for st in states if st.period == "day"][0]
        assert day.state == "warn"
        assert 84.0 < day.pct_of_cap <= 86.0


def test_blocked_when_at_or_above_cap():
    with _session() as s:
        org = Organization(
            slug="y",
            name="y",
            autonomy_posture_json={"daily_cap_usd": 50.0},
        )
        s.add(org)
        s.flush()
        s.add(
            CostLedger(
                organization_id=org.id,
                provider="x",
                kind="x",
                amount_usd=75.0,
            )
        )
        s.flush()
        states = evaluate_caps_sync(s, org.id)
        day = [st for st in states if st.period == "day"][0]
        assert day.state == "blocked"


def test_confidence_threshold_lookup_default():
    cfg = {
        "confidence_thresholds": {
            "publish": 0.7,
            "default": 0.6,
        }
    }
    assert confidence_threshold_for(cfg, "publish") == 0.7
    assert confidence_threshold_for(cfg, "anything_else") == 0.6
    assert confidence_threshold_for(None, "publish") is None
    assert confidence_threshold_for({}, "publish") is None


def test_should_escalate_when_below_threshold():
    cfg = {"confidence_thresholds": {"publish": 0.7}}
    assert should_escalate(
        autonomy_posture_json=cfg, action_class="publish", confidence=0.6
    )
    assert not should_escalate(
        autonomy_posture_json=cfg, action_class="publish", confidence=0.8
    )


def test_should_escalate_returns_false_when_no_threshold():
    cfg = {}
    assert not should_escalate(
        autonomy_posture_json=cfg, action_class="publish", confidence=0.1
    )
