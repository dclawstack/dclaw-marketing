"""Phase 5.x — Substack publisher unit tests."""

from __future__ import annotations

import json

import httpx
import pytest
import pytest_asyncio

from app.services.publishers.substack import (
    SubstackAuthError,
    SubstackPublishError,
    publish_to_substack,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_stub_when_no_api_key():
    res = publish_to_substack(
        api_key=None,
        publication="acmenews",
        text="Daily digest\n\nBody copy here.",
    )
    assert res.provider == "substack"
    assert res.raw.get("stub") is True
    assert res.raw["publication"] == "acmenews"
    assert res.remote_id.startswith("stub-")


def test_stub_with_no_publication_uses_fallback_slug():
    res = publish_to_substack(api_key=None, publication=None, text="hi")
    assert res.raw["publication"] == "stub-publication"


def test_real_draft_creates_post_and_returns_edit_url():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["cookie"] = request.headers.get("Cookie")
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            200,
            json={"id": 99887766, "draft_id": 99887766, "slug": "daily-digest"},
        )

    res = publish_to_substack(
        api_key="sess-cookie-value",
        publication="acmenews",
        text="Daily digest\n\nBody copy here.\n\nMore body.",
        client=_client(handler),
    )
    assert captured["url"] == "https://acmenews.substack.com/api/v1/drafts"
    assert captured["cookie"] == "substack.sid=sess-cookie-value"
    assert captured["body"]["title"] == "Daily digest"
    assert "Body copy here." in captured["body"]["body"]
    assert "More body." in captured["body"]["body"]
    assert captured["body"]["type"] == "newsletter"
    assert captured["body"]["audience"] == "everyone"
    assert res.remote_id == "99887766"
    assert (
        res.permalink
        == "https://acmenews.substack.com/publish/post/99887766"
    )


def test_title_falls_back_when_text_blank():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(200, json={"id": 1, "draft_id": 1})

    publish_to_substack(
        api_key="k",
        publication="acme",
        text="",
        client=_client(handler),
    )
    assert captured["body"]["title"] == "Untitled"
    assert captured["body"]["body"] == ""


def test_title_capped_at_280_chars():
    captured: dict = {}

    def handler(request):
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(200, json={"id": 1, "draft_id": 1})

    long_title = "x" * 600
    publish_to_substack(
        api_key="k",
        publication="acme",
        text=f"{long_title}\n\nbody",
        client=_client(handler),
    )
    assert len(captured["body"]["title"]) == 280


def test_401_raises_auth_error():
    def handler(request):
        return httpx.Response(401, text="session expired")

    with pytest.raises(SubstackAuthError):
        publish_to_substack(
            api_key="bad",
            publication="acme",
            text="x",
            client=_client(handler),
        )


def test_500_raises_publish_error():
    def handler(request):
        return httpx.Response(500, text="upstream oops")

    with pytest.raises(SubstackPublishError):
        publish_to_substack(
            api_key="k",
            publication="acme",
            text="x",
            client=_client(handler),
        )


def test_publication_lowercased():
    """Substack subdomains are always lowercase — adapter normalises."""
    captured: dict = {}

    def handler(request):
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"id": 1, "draft_id": 1})

    publish_to_substack(
        api_key="k",
        publication="AcmeNews",
        text="hi",
        client=_client(handler),
    )
    assert captured["url"] == "https://acmenews.substack.com/api/v1/drafts"
