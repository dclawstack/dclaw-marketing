"""Phase 5.x — TikTok + YouTube publisher unit tests."""

from __future__ import annotations

import json

import httpx
import pytest
import pytest_asyncio

from app.services.publishers.tiktok import (
    TikTokAuthError,
    TikTokMissingMediaError,
    TikTokPublishError,
    publish_to_tiktok,
)
from app.services.publishers.youtube import (
    YouTubeAuthError,
    YouTubeMissingMediaError,
    YouTubePublishError,
    publish_to_youtube,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


# ---------- TikTok ----------------------------------------------------------


def test_tt_stub_when_no_token():
    res = publish_to_tiktok(
        access_token=None,
        video_url="https://cdn.example/v.mp4",
        caption="hello",
    )
    assert res.provider == "tiktok"
    assert res.raw.get("stub") is True


def test_tt_real_init_returns_publish_id():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization")
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={"data": {"publish_id": "v_pub_123"}},
        )

    res = publish_to_tiktok(
        access_token="tok-x",
        video_url="https://cdn.example/v.mp4",
        caption="my caption " * 30,  # over 150 chars
        privacy_level="PUBLIC_TO_EVERYONE",
        client=_client(handler),
    )
    assert captured["url"].endswith("/post/publish/inbox/video/init/")
    assert captured["auth"] == "Bearer tok-x"
    assert captured["body"]["source_info"]["source"] == "PULL_FROM_URL"
    assert (
        captured["body"]["source_info"]["video_url"]
        == "https://cdn.example/v.mp4"
    )
    assert len(captured["body"]["post_info"]["title"]) == 150
    assert captured["body"]["post_info"]["privacy_level"] == "PUBLIC_TO_EVERYONE"
    assert res.remote_id == "v_pub_123"
    assert res.permalink is None


def test_tt_missing_video_url_raises():
    with pytest.raises(TikTokMissingMediaError):
        publish_to_tiktok(
            access_token="tok",
            video_url=None,
            caption="x",
        )


def test_tt_401_raises_auth():
    with pytest.raises(TikTokAuthError):
        publish_to_tiktok(
            access_token="bad",
            video_url="https://x/v.mp4",
            caption="x",
            client=_client(lambda r: httpx.Response(401, text="bad")),
        )


def test_tt_500_raises_publish():
    with pytest.raises(TikTokPublishError):
        publish_to_tiktok(
            access_token="t",
            video_url="https://x/v.mp4",
            caption="x",
            client=_client(lambda r: httpx.Response(500, text="oops")),
        )


# ---------- YouTube ---------------------------------------------------------


def test_yt_stub_when_no_token():
    res = publish_to_youtube(
        access_token=None,
        title="hello",
        video_data=b"fake",
    )
    assert res.provider == "youtube"
    assert res.raw.get("stub") is True


def test_yt_missing_media_raises():
    with pytest.raises(YouTubeMissingMediaError):
        publish_to_youtube(access_token="t", title="hi")


def test_yt_multipart_upload_happy_path_with_video_data():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization")
        captured["ctype"] = request.headers.get("Content-Type")
        captured["body"] = request.content
        return httpx.Response(
            200,
            json={"id": "dQw4w9WgXcQ", "snippet": {"title": "hi"}},
        )

    res = publish_to_youtube(
        access_token="ya29.tok",
        title="hi",
        description="long form",
        tags=["a", "b"],
        privacy_status="unlisted",
        video_data=b"VIDEO-BYTES-HERE",
        client=_client(handler),
    )
    assert captured["url"].startswith(
        "https://www.googleapis.com/upload/youtube/v3/videos"
    )
    assert "uploadType=multipart" in captured["url"]
    assert captured["auth"] == "Bearer ya29.tok"
    assert captured["ctype"].startswith("multipart/related; boundary=DCLAW-YT-")
    assert b"\"privacyStatus\": \"unlisted\"" in captured["body"]
    assert b"VIDEO-BYTES-HERE" in captured["body"]
    assert res.remote_id == "dQw4w9WgXcQ"
    assert res.permalink == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_yt_fetches_video_url_then_uploads():
    calls: list = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, str(request.url)))
        if request.method == "GET":
            return httpx.Response(200, content=b"BYTES-FROM-CDN")
        return httpx.Response(200, json={"id": "abc", "snippet": {}})

    res = publish_to_youtube(
        access_token="t",
        title="x",
        video_url="https://cdn.example/v.mp4",
        client=_client(handler),
    )
    assert calls[0][0] == "GET"
    assert calls[0][1] == "https://cdn.example/v.mp4"
    assert calls[1][0] == "POST"
    assert res.remote_id == "abc"


def test_yt_401_raises_auth():
    def handler(request):
        return httpx.Response(401, text="bad token")

    with pytest.raises(YouTubeAuthError):
        publish_to_youtube(
            access_token="bad",
            title="x",
            video_data=b"v",
            client=_client(handler),
        )


def test_yt_500_raises_publish():
    def handler(request):
        return httpx.Response(500, text="oops")

    with pytest.raises(YouTubePublishError):
        publish_to_youtube(
            access_token="t",
            title="x",
            video_data=b"v",
            client=_client(handler),
        )


def test_yt_fetch_failure_raises_publish_error():
    def handler(request):
        if request.method == "GET":
            return httpx.Response(404, text="not found")
        return httpx.Response(200, json={})

    with pytest.raises(YouTubePublishError):
        publish_to_youtube(
            access_token="t",
            title="x",
            video_url="https://cdn.example/missing.mp4",
            client=_client(handler),
        )
