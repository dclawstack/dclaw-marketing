"""Phase 8.x — time-decay attribution + Sankey shape tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.models.attribution import AttributionModel
from app.worker.tasks.attribution import _allocate, _time_decay_weights


def _tp(occurred_at):
    return SimpleNamespace(id=uuid4(), occurred_at=occurred_at)


def _conv(at):
    return SimpleNamespace(occurred_at=at)


def test_time_decay_weights_sum_to_one():
    base = datetime(2026, 5, 19, tzinfo=timezone.utc)
    tps = [_tp(base - timedelta(days=d)) for d in (0, 3, 7, 14)]
    weights = _time_decay_weights(tps, conversion_at=base)
    assert pytest.approx(sum(weights.values())) == 1.0


def test_time_decay_recent_touchpoint_gets_more_credit():
    base = datetime(2026, 5, 19, tzinfo=timezone.utc)
    fresh = _tp(base - timedelta(days=1))
    stale = _tp(base - timedelta(days=14))
    weights = _time_decay_weights([fresh, stale], conversion_at=base)
    assert weights[fresh.id] > weights[stale.id]
    # 1d-old should be ~ 2x more than 14d-old when half_life=7
    # ratio = 0.5^(1/7) / 0.5^(14/7) = 0.5^-1.857 ≈ 3.6
    assert weights[fresh.id] / weights[stale.id] > 3.0


def test_time_decay_zero_age_when_conversion_first():
    """Edge case: a touchpoint that occurs after the conversion gets
    weight 0.5^0 = 1.0 (we clamp negative ages to 0)."""
    base = datetime(2026, 5, 19, tzinfo=timezone.utc)
    future_tp = _tp(base + timedelta(days=5))
    past_tp = _tp(base - timedelta(days=5))
    weights = _time_decay_weights(
        [future_tp, past_tp], conversion_at=base
    )
    # Future touchpoint has age clamped to 0 → max weight; past gets less.
    assert weights[future_tp.id] >= weights[past_tp.id]


def test_allocate_dispatches_to_time_decay():
    base = datetime(2026, 5, 19, tzinfo=timezone.utc)
    tps = [_tp(base - timedelta(days=d)) for d in (0, 7, 14)]
    weights = _allocate(
        AttributionModel.time_decay, tps, conversion=_conv(base)
    )
    assert len(weights) == 3
    assert pytest.approx(sum(weights.values())) == 1.0


def test_allocate_first_touch_unchanged():
    base = datetime(2026, 5, 19, tzinfo=timezone.utc)
    tps = [_tp(base - timedelta(days=d)) for d in (10, 5, 0)]
    weights = _allocate(AttributionModel.first_touch, tps)
    assert weights == {tps[0].id: 1.0}


def test_allocate_markov_returns_empty_per_conversion():
    """Per-conversion Markov isn't meaningful; the population-level
    writer ships separately. Beat task skips empty allocations."""
    base = datetime(2026, 5, 19, tzinfo=timezone.utc)
    tps = [_tp(base - timedelta(days=d)) for d in (0, 5)]
    assert _allocate(AttributionModel.markov, tps) == {}


def test_allocate_empty_journey_returns_empty():
    assert _allocate(AttributionModel.linear, []) == {}
    assert _allocate(AttributionModel.time_decay, [], conversion=None) == {}
