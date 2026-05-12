"""Phase 5.2 — LinkedIn publisher unit tests."""

from __future__ import annotations

import json

import httpx
import pytest
import pytest_asyncio

from app.services.publishers.linkedin import (
    LinkedInAuthError,
    LinkedInPublishError,
    publish_to_linkedin,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_stub_when_no_token():
    res = publish_to_linkedin(
        access_token=None,
        author_urn="urn:li:person:abc",
        text="hello world",
    )
    assert res.provider == "linkedin"
    assert res.raw.get("stub") is True
    assert res.remote_id.startswith("urn:li:share:stub-")
    assert res.permalink is None


def test_real_post_uses_restli_id_header_for_remote_id():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization")
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            201,
            headers={"x-restli-id": "urn:li:share:7012345678901234567"},
            json={"id": "urn:li:share:7012345678901234567"},
        )

    res = publish_to_linkedin(
        access_token="tok-abc",
        author_urn="urn:li:person:xyz",
        text="hello from dclaw",
        client=_client(handler),
    )
    assert captured["url"].endswith("/v2/ugcPosts")
    assert captured["auth"] == "Bearer tok-abc"
    assert captured["body"]["author"] == "urn:li:person:xyz"
    assert (
        captured["body"]["specificContent"][
            "com.linkedin.ugc.ShareContent"
        ]["shareCommentary"]["text"]
        == "hello from dclaw"
    )
    assert res.remote_id == "urn:li:share:7012345678901234567"
    assert res.permalink == (
        "https://www.linkedin.com/feed/update/urn:li:share:7012345678901234567/"
    )


def test_401_raises_auth_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="bad token")

    with pytest.raises(LinkedInAuthError):
        publish_to_linkedin(
            access_token="expired",
            author_urn="urn:li:person:x",
            text="x",
            client=_client(handler),
        )


def test_500_raises_publish_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="internal")

    with pytest.raises(LinkedInPublishError):
        publish_to_linkedin(
            access_token="tok",
            author_urn="urn:li:person:x",
            text="x",
            client=_client(handler),
        )


def test_long_text_truncated_to_3000():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            201, headers={"x-restli-id": "urn:li:share:1"}, json={"id": "1"}
        )

    long_text = "x" * 5000
    publish_to_linkedin(
        access_token="tok",
        author_urn="urn:li:person:x",
        text=long_text,
        client=_client(handler),
    )
    sent = captured["body"]["specificContent"][
        "com.linkedin.ugc.ShareContent"
    ]["shareCommentary"]["text"]
    assert len(sent) == 3000
    assert sent.endswith("…")
