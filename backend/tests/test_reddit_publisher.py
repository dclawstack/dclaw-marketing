"""Phase 5.6 — Reddit publisher unit tests."""

from __future__ import annotations

import httpx
import pytest
import pytest_asyncio

from app.services.publishers.reddit import (
    RedditAuthError,
    RedditPublishError,
    publish_to_reddit,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_stub_when_no_token():
    res = publish_to_reddit(
        access_token=None,
        subreddit="testsub",
        text="title here\n\nbody here",
    )
    assert res.provider == "reddit"
    assert res.raw.get("stub") is True
    assert res.remote_id.startswith("stub-")


def test_real_post_returns_id_and_url():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["ua"] = request.headers.get("User-Agent")
        captured["auth"] = request.headers.get("Authorization")
        captured["body"] = request.content.decode("utf-8")
        return httpx.Response(
            200,
            json={
                "json": {
                    "errors": [],
                    "data": {
                        "name": "t3_abc123",
                        "url": "https://reddit.com/r/test/comments/abc123",
                    },
                }
            },
        )

    res = publish_to_reddit(
        access_token="tok",
        subreddit="test",
        text="My title\n\nThe body of the post.",
        client=_client(handler),
    )
    assert captured["url"].endswith("/api/submit")
    assert captured["auth"] == "Bearer tok"
    assert captured["ua"].startswith("DClawMarketing")
    # Form-encoded
    assert "kind=self" in captured["body"]
    assert "sr=test" in captured["body"]
    assert "title=My+title" in captured["body"]
    assert res.remote_id == "t3_abc123"
    assert res.permalink == "https://reddit.com/r/test/comments/abc123"


def test_first_line_used_as_title():
    captured: dict = {}

    def handler(request):
        captured["body"] = request.content.decode("utf-8")
        return httpx.Response(
            200,
            json={"json": {"errors": [], "data": {"name": "t3_x", "url": "u"}}},
        )

    publish_to_reddit(
        access_token="tok",
        subreddit="test",
        text="Single line",
        client=_client(handler),
    )
    assert "title=Single+line" in captured["body"]


def test_explicit_title_overrides_first_line():
    captured: dict = {}

    def handler(request):
        captured["body"] = request.content.decode("utf-8")
        return httpx.Response(
            200,
            json={"json": {"errors": [], "data": {"name": "t3_x", "url": "u"}}},
        )

    publish_to_reddit(
        access_token="tok",
        subreddit="test",
        text="all of this becomes the body",
        title="Explicit Title",
        client=_client(handler),
    )
    assert "title=Explicit+Title" in captured["body"]


def test_401_raises_auth_error():
    def handler(request):
        return httpx.Response(401, text="bad token")

    with pytest.raises(RedditAuthError):
        publish_to_reddit(
            access_token="bad",
            subreddit="test",
            text="hi",
            client=_client(handler),
        )


def test_403_raises_auth_error():
    def handler(request):
        return httpx.Response(403, text="no scope")

    with pytest.raises(RedditAuthError):
        publish_to_reddit(
            access_token="t",
            subreddit="test",
            text="hi",
            client=_client(handler),
        )


def test_500_raises_publish_error():
    def handler(request):
        return httpx.Response(500, text="oops")

    with pytest.raises(RedditPublishError):
        publish_to_reddit(
            access_token="t",
            subreddit="test",
            text="hi",
            client=_client(handler),
        )


def test_errors_in_body_raise_publish_error():
    def handler(request):
        return httpx.Response(
            200,
            json={
                "json": {
                    "errors": [["NOT_LOGGED_IN", "Not allowed", "title"]],
                    "data": {},
                }
            },
        )

    with pytest.raises(RedditPublishError, match="errors"):
        publish_to_reddit(
            access_token="t",
            subreddit="test",
            text="hi",
            client=_client(handler),
        )


def test_title_truncated_to_300():
    captured: dict = {}

    def handler(request):
        captured["body"] = request.content.decode("utf-8")
        return httpx.Response(
            200,
            json={"json": {"errors": [], "data": {"name": "t3_x", "url": "u"}}},
        )

    long_title = "x" * 500
    publish_to_reddit(
        access_token="t",
        subreddit="test",
        text=long_title,
        client=_client(handler),
    )
    # Find title= in form body; it should be at most 300 chars + URL-encoded ellipsis
    # The "x" * 299 + "%E2%80%A6" (the ellipsis)
    body = captured["body"]
    title_part = body.split("title=")[1].split("&")[0]
    # x's URL-encoded as themselves; ellipsis as %E2%80%A6
    assert title_part.count("x") == 299


def test_empty_title_raises():
    """If text is empty / has no first line, we should raise."""
    with pytest.raises(RedditPublishError, match="non-empty title"):
        publish_to_reddit(
            access_token="t",
            subreddit="test",
            text="",
        )
