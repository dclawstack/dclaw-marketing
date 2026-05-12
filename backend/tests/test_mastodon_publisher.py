"""Phase 5.5 — Mastodon publisher unit tests."""

from __future__ import annotations

import json

import httpx
import pytest
import pytest_asyncio

from app.services.publishers.mastodon import (
    MastodonAuthError,
    MastodonPublishError,
    publish_to_mastodon,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_stub_when_no_token():
    res = publish_to_mastodon(
        access_token=None,
        instance_url="https://mastodon.social",
        text="hello",
    )
    assert res.provider == "mastodon"
    assert res.raw.get("stub") is True
    assert res.remote_id.startswith("stub-")


def test_real_post_returns_id_and_permalink():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization")
        captured["idem"] = request.headers.get("Idempotency-Key")
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={
                "id": "11122233",
                "url": "https://mastodon.social/@alice/11122233",
            },
        )

    res = publish_to_mastodon(
        access_token="tok-x",
        instance_url="https://mastodon.social",
        text="hello fediverse",
        client=_client(handler),
    )
    assert captured["url"].endswith("/api/v1/statuses")
    assert captured["auth"] == "Bearer tok-x"
    assert captured["idem"] is not None
    assert captured["body"] == {"status": "hello fediverse", "visibility": "public"}
    assert res.remote_id == "11122233"
    assert res.permalink == "https://mastodon.social/@alice/11122233"


def test_visibility_kwarg_passed_through():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(200, json={"id": "1", "url": "https://x/p/1"})

    publish_to_mastodon(
        access_token="t",
        instance_url="https://x",
        text="private",
        visibility="unlisted",
        client=_client(handler),
    )
    assert captured["body"]["visibility"] == "unlisted"


def test_401_raises_auth_error():
    def handler(request):
        return httpx.Response(401, text="invalid bearer")

    with pytest.raises(MastodonAuthError):
        publish_to_mastodon(
            access_token="bad",
            instance_url="https://x",
            text="x",
            client=_client(handler),
        )


def test_500_raises_publish_error():
    def handler(request):
        return httpx.Response(500, text="oops")

    with pytest.raises(MastodonPublishError):
        publish_to_mastodon(
            access_token="t",
            instance_url="https://x",
            text="x",
            client=_client(handler),
        )


def test_text_truncated_to_500():
    captured: dict = {}

    def handler(request):
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(200, json={"id": "1", "url": "https://x/p/1"})

    long_text = "x" * 800
    publish_to_mastodon(
        access_token="t",
        instance_url="https://x",
        text=long_text,
        client=_client(handler),
    )
    assert len(captured["body"]["status"]) == 500
    assert captured["body"]["status"].endswith("…")


def test_falls_back_to_default_instance_when_none():
    """If instance_url is None we use the configured default."""
    res = publish_to_mastodon(
        access_token=None,
        instance_url=None,
        text="hello",
    )
    # No token → stub. The stub's raw should mention the default URL.
    assert res.raw["instance_url"] in (
        "https://mastodon.social",
    )  # whatever settings.mastodon_default_instance is, default value
