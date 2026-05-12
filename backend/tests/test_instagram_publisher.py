"""Phase 5.4 — Instagram Business publisher unit tests."""

from __future__ import annotations

import httpx
import pytest
import pytest_asyncio

from app.services.publishers.instagram import (
    InstagramAuthError,
    InstagramMissingMediaError,
    InstagramPublishError,
    publish_to_instagram,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_stub_when_no_token():
    res = publish_to_instagram(
        access_token=None,
        ig_user_id="ig-123",
        image_url=None,
        caption="hello",
    )
    assert res.provider == "instagram"
    assert res.raw.get("stub") is True
    assert res.remote_id.startswith("stub-")
    assert res.permalink is None


def test_token_without_image_raises():
    """With a token but no image, we raise — Instagram requires media."""
    with pytest.raises(InstagramMissingMediaError):
        publish_to_instagram(
            access_token="tok",
            ig_user_id="ig-123",
            image_url=None,
            caption="hello",
        )


def test_real_two_step_flow():
    """First POST creates container, second POST publishes it."""
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        calls.append(path)
        if path.endswith("/media"):
            assert "image_url" in request.url.params
            assert request.url.params.get("caption") == "hello world"
            return httpx.Response(200, json={"id": "container-99"})
        if path.endswith("/media_publish"):
            assert request.url.params.get("creation_id") == "container-99"
            return httpx.Response(200, json={"id": "media-12345"})
        return httpx.Response(404, text="unexpected")

    res = publish_to_instagram(
        access_token="long-lived-token",
        ig_user_id="ig-acct-42",
        image_url="https://cdn.example.com/img.jpg",
        caption="hello world",
        client=_client(handler),
    )
    assert calls == [
        "/v19.0/ig-acct-42/media",
        "/v19.0/ig-acct-42/media_publish",
    ]
    assert res.remote_id == "media-12345"
    assert res.permalink == "https://www.instagram.com/p/media-12345/"


def test_step_one_401_raises_auth_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="bad token")

    with pytest.raises(InstagramAuthError):
        publish_to_instagram(
            access_token="bad",
            ig_user_id="ig-1",
            image_url="https://x/y.jpg",
            caption="x",
            client=_client(handler),
        )


def test_step_two_500_raises_publish_error():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/media"):
            return httpx.Response(200, json={"id": "c-1"})
        return httpx.Response(500, text="internal")

    with pytest.raises(InstagramPublishError):
        publish_to_instagram(
            access_token="tok",
            ig_user_id="ig-1",
            image_url="https://x/y.jpg",
            caption="x",
            client=_client(handler),
        )


def test_caption_truncated_to_2200():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/media"):
            captured["caption"] = request.url.params.get("caption")
            return httpx.Response(200, json={"id": "c-1"})
        return httpx.Response(200, json={"id": "m-1"})

    long_caption = "x" * 3000
    publish_to_instagram(
        access_token="tok",
        ig_user_id="ig-1",
        image_url="https://x/y.jpg",
        caption=long_caption,
        client=_client(handler),
    )
    assert len(captured["caption"]) == 2200
    assert captured["caption"].endswith("…")
