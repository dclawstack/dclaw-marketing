"""Phase 5.1 — Bluesky publisher unit tests.

We use httpx's MockTransport so the publisher hits an in-memory
fake instead of bsky.social — no network, no env wiring.
"""

from __future__ import annotations

import json

import httpx
import pytest
import pytest_asyncio

from app.services.publishers.bluesky import (
    BlueskyAuthError,
    BlueskyPublishError,
    publish_to_bluesky,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


def _mock_transport(handler):
    return httpx.MockTransport(handler)


def _ok_session_handler(create_record_response: dict):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("createSession"):
            return httpx.Response(
                200,
                json={
                    "accessJwt": "fake-access",
                    "did": "did:plc:fakeuser",
                    "handle": "alice.bsky.social",
                },
            )
        if request.url.path.endswith("createRecord"):
            return httpx.Response(200, json=create_record_response)
        return httpx.Response(404, text="unexpected route")
    return handler


def test_stub_when_no_password():
    res = publish_to_bluesky(
        handle="alice.bsky.social",
        app_password=None,
        text="hello",
    )
    assert res.provider == "bluesky"
    assert res.raw.get("stub") is True
    assert res.permalink is None
    assert res.remote_id.startswith("at://stub/")


def test_real_post_returns_permalink():
    handler = _ok_session_handler(
        {
            "uri": "at://did:plc:fakeuser/app.bsky.feed.post/abc123",
            "cid": "bafy...",
        }
    )
    client = httpx.Client(transport=_mock_transport(handler))
    res = publish_to_bluesky(
        handle="alice.bsky.social",
        app_password="x-app-pass",
        text="hello from dclaw",
        client=client,
    )
    assert res.provider == "bluesky"
    assert res.remote_id == "at://did:plc:fakeuser/app.bsky.feed.post/abc123"
    assert res.permalink == "https://bsky.app/profile/alice.bsky.social/post/abc123"


def test_session_failure_raises_auth_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="bad creds")
    client = httpx.Client(transport=_mock_transport(handler))
    with pytest.raises(BlueskyAuthError):
        publish_to_bluesky(
            handle="alice.bsky.social",
            app_password="wrong",
            text="nope",
            client=client,
        )


def test_publish_failure_raises_publish_error():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("createSession"):
            return httpx.Response(
                200,
                json={"accessJwt": "fake", "did": "did:plc:x", "handle": "h"},
            )
        return httpx.Response(400, text="bad record")
    client = httpx.Client(transport=_mock_transport(handler))
    with pytest.raises(BlueskyPublishError):
        publish_to_bluesky(
            handle="h",
            app_password="ok",
            text="x",
            client=client,
        )


def test_text_truncates_to_300():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("createSession"):
            return httpx.Response(
                200,
                json={"accessJwt": "fake", "did": "did:plc:x", "handle": "h"},
            )
        body = json.loads(request.content.decode("utf-8"))
        captured["text"] = body["record"]["text"]
        return httpx.Response(200, json={"uri": "at://did:plc:x/app.bsky.feed.post/k", "cid": "c"})

    client = httpx.Client(transport=_mock_transport(handler))
    long_text = "x" * 400
    publish_to_bluesky(
        handle="h", app_password="ok", text=long_text, client=client,
    )
    assert len(captured["text"]) == 300
    assert captured["text"].endswith("…")
