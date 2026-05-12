"""Phase 5.7 — Discord + Pinterest publisher unit tests."""

from __future__ import annotations

import json

import httpx
import pytest
import pytest_asyncio

from app.services.publishers.discord import (
    DiscordPublishError,
    publish_to_discord,
)
from app.services.publishers.pinterest import (
    PinterestAuthError,
    PinterestMissingMediaError,
    PinterestPublishError,
    publish_to_pinterest,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


# ===== Discord =====


def test_discord_stub_when_no_webhook():
    res = publish_to_discord(webhook_url=None, text="hi")
    assert res.provider == "discord"
    assert res.raw.get("stub") is True
    assert res.remote_id.startswith("stub-")


def test_discord_real_post_returns_id():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200, json={"id": "msg-99", "content": "hello"}
        )

    res = publish_to_discord(
        webhook_url="https://discord.com/api/webhooks/abc/def",
        text="hello",
        client=_client(handler),
    )
    assert "wait=true" in captured["url"]
    assert captured["body"] == {"content": "hello"}
    assert res.remote_id == "msg-99"


def test_discord_username_passes_through():
    captured: dict = {}

    def handler(request):
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(204)

    publish_to_discord(
        webhook_url="https://discord.com/api/webhooks/x/y",
        text="hi",
        username="DClaw Bot",
        client=_client(handler),
    )
    assert captured["body"]["username"] == "DClaw Bot"


def test_discord_2000_char_truncation():
    captured: dict = {}

    def handler(request):
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(204)

    publish_to_discord(
        webhook_url="https://discord.com/api/webhooks/x/y",
        text="x" * 3000,
        client=_client(handler),
    )
    assert len(captured["body"]["content"]) == 2000
    assert captured["body"]["content"].endswith("…")


def test_discord_500_raises():
    def handler(request):
        return httpx.Response(500, text="oops")

    with pytest.raises(DiscordPublishError):
        publish_to_discord(
            webhook_url="https://discord.com/api/webhooks/x/y",
            text="hi",
            client=_client(handler),
        )


# ===== Pinterest =====


def test_pinterest_stub_when_no_token():
    res = publish_to_pinterest(
        access_token=None,
        board_id="b-1",
        image_url=None,
        title="t",
    )
    assert res.provider == "pinterest"
    assert res.raw.get("stub") is True


def test_pinterest_token_without_image_raises():
    with pytest.raises(PinterestMissingMediaError):
        publish_to_pinterest(
            access_token="t",
            board_id="b-1",
            image_url=None,
            title="t",
        )


def test_pinterest_real_pin_returns_id_and_permalink():
    captured: dict = {}

    def handler(request):
        captured["url"] = str(request.url)
        captured["auth"] = request.headers["Authorization"]
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(201, json={"id": "pin-77"})

    res = publish_to_pinterest(
        access_token="tok",
        board_id="board-1",
        image_url="https://cdn/img.jpg",
        title="My new pin",
        description="nice desc",
        client=_client(handler),
    )
    assert captured["url"].endswith("/v5/pins")
    assert captured["auth"] == "Bearer tok"
    assert captured["body"]["board_id"] == "board-1"
    assert captured["body"]["media_source"]["url"] == "https://cdn/img.jpg"
    assert captured["body"]["description"] == "nice desc"
    assert res.remote_id == "pin-77"
    assert res.permalink == "https://pinterest.com/pin/pin-77/"


def test_pinterest_401_raises_auth():
    def handler(request):
        return httpx.Response(401, text="bad token")

    with pytest.raises(PinterestAuthError):
        publish_to_pinterest(
            access_token="bad",
            board_id="b-1",
            image_url="https://cdn/x.jpg",
            title="t",
            client=_client(handler),
        )


def test_pinterest_500_raises_publish_error():
    def handler(request):
        return httpx.Response(500, text="oops")

    with pytest.raises(PinterestPublishError):
        publish_to_pinterest(
            access_token="t",
            board_id="b-1",
            image_url="https://cdn/x.jpg",
            title="t",
            client=_client(handler),
        )


def test_pinterest_title_truncated_to_100():
    captured: dict = {}

    def handler(request):
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(201, json={"id": "1"})

    publish_to_pinterest(
        access_token="t",
        board_id="b",
        image_url="https://x.jpg",
        title="x" * 200,
        client=_client(handler),
    )
    assert len(captured["body"]["title"]) == 100
    assert captured["body"]["title"].endswith("…")
