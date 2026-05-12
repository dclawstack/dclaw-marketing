"""Phase 11.2 — quota guard unit tests (pure cost calculation)."""

from __future__ import annotations

import pytest_asyncio

from app.services.quota_guard import _cost_of


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


def test_send_email_cost_is_recipient_count():
    key, cost = _cost_of("send_email", {"to": ["a@x.io", "b@x.io", "c@x.io"]})
    assert key == "email_sends"
    assert cost == 3.0


def test_send_email_missing_to_is_zero():
    key, cost = _cost_of("send_email", {})
    assert key == "email_sends"
    assert cost == 0.0


def test_publish_ad_cost_is_amount_usd():
    key, cost = _cost_of("publish_ad", {"amount_usd": 125.5})
    assert key == "ads"
    assert cost == 125.5


def test_publish_ad_bad_amount_is_zero():
    key, cost = _cost_of("publish_ad", {"amount_usd": "not a number"})
    assert key == "ads"
    assert cost == 0.0


def test_publish_social_post_cost_is_one():
    for action in (
        "publish_social_post",
        "publish_image_asset",
        "publish_video_asset",
    ):
        key, cost = _cost_of(action, {})
        assert key == "social_posts"
        assert cost == 1.0


def test_unknown_action_is_uncosted():
    key, cost = _cost_of("send_telepathy", {"thought": "hi"})
    assert key is None
    assert cost == 0.0


def test_none_payload_safe():
    key, cost = _cost_of("send_email", None)
    assert key == "email_sends"
    assert cost == 0.0
