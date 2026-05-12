"""Phase 8.3 — attribution allocation unit tests (pure function)."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest_asyncio

from app.models.attribution import AttributionModel
from app.worker.tasks.attribution import _allocate


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


def _tp(label: str | None = None):
    """Minimal Touchpoint-shaped duck — only .id is read by _allocate."""
    return SimpleNamespace(id=uuid4(), _label=label or "")


def test_empty_journey_returns_empty():
    for model in AttributionModel:
        assert _allocate(model, []) == {}


def test_first_touch_gives_100_to_first():
    journey = [_tp("a"), _tp("b"), _tp("c")]
    w = _allocate(AttributionModel.first_touch, journey)
    assert w == {journey[0].id: 1.0}


def test_last_touch_gives_100_to_last():
    journey = [_tp("a"), _tp("b"), _tp("c")]
    w = _allocate(AttributionModel.last_touch, journey)
    assert w == {journey[-1].id: 1.0}


def test_linear_splits_equally():
    journey = [_tp("a"), _tp("b"), _tp("c"), _tp("d")]
    w = _allocate(AttributionModel.linear, journey)
    assert len(w) == 4
    for tp in journey:
        assert w[tp.id] == 0.25
    assert sum(w.values()) == 1.0


def test_linear_single_touchpoint_is_100():
    journey = [_tp("only")]
    w = _allocate(AttributionModel.linear, journey)
    assert w == {journey[0].id: 1.0}


def test_unsupported_model_returns_empty():
    """Per-conversion Markov is intentionally a no-op — see _allocate."""
    journey = [_tp("a"), _tp("b")]
    assert _allocate(AttributionModel.markov, journey) == {}


def test_weights_sum_to_one_for_supported():
    journey = [_tp("a"), _tp("b"), _tp("c"), _tp("d"), _tp("e")]
    for model in (
        AttributionModel.first_touch,
        AttributionModel.last_touch,
        AttributionModel.linear,
    ):
        w = _allocate(model, journey)
        assert abs(sum(w.values()) - 1.0) < 1e-9, f"{model.value} weights don't sum to 1"
