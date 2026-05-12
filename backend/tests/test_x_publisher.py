"""Phase 5.3 — X (Twitter) publisher unit tests."""

from __future__ import annotations

import json

import httpx
import pytest
import pytest_asyncio

from app.services.publishers.x import XAuthError, XPublishError, publish_to_x


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_stub_when_no_token():
    res = publish_to_x(
        access_token=None,
        handle="dclaw",
        text="hello world",
    )
    assert res.provider == "x"
    assert res.raw.get("stub") is True
    assert res.remote_id.startswith("stub-")
    assert res.permalink is None


def test_real_post_returns_id_and_permalink():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization")
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            201, json={"data": {"id": "1234567890", "text": "hello"}}
        )

    res = publish_to_x(
        access_token="user-token",
        handle="dclaw",
        text="hello from dclaw",
        client=_client(handler),
    )
    assert captured["url"].endswith("/2/tweets")
    assert captured["auth"] == "Bearer user-token"
    assert captured["body"] == {"text": "hello from dclaw"}
    assert res.remote_id == "1234567890"
    assert res.permalink == "https://x.com/dclaw/status/1234567890"


def test_401_raises_auth_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="bad token")

    with pytest.raises(XAuthError):
        publish_to_x(
            access_token="bad",
            handle="x",
            text="x",
            client=_client(handler),
        )


def test_403_raises_auth_error_for_write_scope():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="needs tweet.write")

    with pytest.raises(XAuthError):
        publish_to_x(
            access_token="readonly",
            handle="x",
            text="x",
            client=_client(handler),
        )


def test_500_raises_publish_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="internal")

    with pytest.raises(XPublishError):
        publish_to_x(
            access_token="t",
            handle="x",
            text="x",
            client=_client(handler),
        )


def test_long_text_truncated_to_280():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(201, json={"data": {"id": "1"}})

    long_text = "x" * 500
    publish_to_x(
        access_token="t",
        handle="x",
        text=long_text,
        client=_client(handler),
    )
    sent = captured["body"]["text"]
    assert len(sent) == 280
    assert sent.endswith("…")
