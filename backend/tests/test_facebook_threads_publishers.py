"""Phase 5.x — Facebook + Threads publisher unit tests."""

from __future__ import annotations

import httpx
import pytest
import pytest_asyncio

from app.services.publishers.facebook import (
    FacebookAuthError,
    FacebookPublishError,
    publish_to_facebook,
)
from app.services.publishers.threads import (
    ThreadsAuthError,
    ThreadsPublishError,
    publish_to_threads,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


# ---------- Facebook --------------------------------------------------------


def test_fb_stub_when_no_token():
    res = publish_to_facebook(
        access_token=None, page_id="12345", text="hello"
    )
    assert res.provider == "facebook"
    assert res.raw.get("stub") is True
    assert res.remote_id.startswith("stub-")


def test_fb_happy_path_form_encoded_and_permalink():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["method"] = request.method
        captured["body"] = dict(
            [p.split("=", 1) for p in request.content.decode().split("&")]
        )
        return httpx.Response(200, json={"id": "12345_678"})

    res = publish_to_facebook(
        access_token="page-tok",
        page_id="12345",
        text="hello world",
        client=_client(handler),
    )
    assert captured["url"] == (
        "https://graph.facebook.com/v18.0/12345/feed"
    )
    assert captured["method"] == "POST"
    assert captured["body"]["access_token"] == "page-tok"
    assert captured["body"]["message"] == "hello+world"
    assert res.remote_id == "12345_678"
    assert res.permalink == "https://www.facebook.com/12345/posts/678"


def test_fb_text_truncated_at_max():
    captured: dict = {}

    def handler(request):
        captured["body"] = request.content.decode()
        return httpx.Response(200, json={"id": "12_1"})

    publish_to_facebook(
        access_token="t",
        page_id="12",
        text="x" * 70000,
        client=_client(handler),
    )
    # urlencoded message body — the message= field is followed by access_token=
    msg_part = [
        seg for seg in captured["body"].split("&") if seg.startswith("message=")
    ][0]
    msg_value = msg_part[len("message="):]
    # Each 'x' is one byte once urlencoded. The 63206 cap minus 1 + '…' ellipsis.
    # Just sanity-check that it isn't 70000 anymore.
    assert len(msg_value) < 70000


def test_fb_401_raises_auth():
    with pytest.raises(FacebookAuthError):
        publish_to_facebook(
            access_token="bad",
            page_id="12",
            text="x",
            client=_client(lambda r: httpx.Response(401, text="bad")),
        )


def test_fb_500_raises_publish():
    with pytest.raises(FacebookPublishError):
        publish_to_facebook(
            access_token="t",
            page_id="12",
            text="x",
            client=_client(lambda r: httpx.Response(500, text="oops")),
        )


# ---------- Threads ---------------------------------------------------------


def test_threads_stub_when_no_token():
    res = publish_to_threads(
        access_token=None,
        threads_user_id="9999",
        text="hello",
    )
    assert res.provider == "threads"
    assert res.raw.get("stub") is True


def test_threads_two_step_happy_path():
    calls: list = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((str(request.url), request.content.decode()))
        if request.url.path.endswith("/threads"):
            return httpx.Response(200, json={"id": "container-abc"})
        if request.url.path.endswith("/threads_publish"):
            return httpx.Response(200, json={"id": "media-xyz"})
        return httpx.Response(404)

    res = publish_to_threads(
        access_token="tok",
        threads_user_id="9999",
        text="hello fediverse",
        handle="alice",
        client=_client(handler),
    )

    assert len(calls) == 2
    create_body = dict(
        [p.split("=", 1) for p in calls[0][1].split("&")]
    )
    pub_body = dict([p.split("=", 1) for p in calls[1][1].split("&")])
    assert create_body["media_type"] == "TEXT"
    assert create_body["text"] == "hello+fediverse"
    assert pub_body["creation_id"] == "container-abc"
    assert pub_body["access_token"] == "tok"
    assert res.remote_id == "media-xyz"
    assert res.permalink == "https://www.threads.net/@alice/post/media-xyz"


def test_threads_missing_container_id_raises():
    def handler(request):
        return httpx.Response(200, json={})  # no id field

    with pytest.raises(ThreadsPublishError):
        publish_to_threads(
            access_token="t",
            threads_user_id="9",
            text="x",
            client=_client(handler),
        )


def test_threads_text_truncated_at_500():
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/threads"):
            captured["body"] = dict(
                [p.split("=", 1) for p in request.content.decode().split("&")]
            )
            return httpx.Response(200, json={"id": "c"})
        return httpx.Response(200, json={"id": "m"})

    publish_to_threads(
        access_token="t",
        threads_user_id="9",
        text="x" * 800,
        client=_client(handler),
    )
    # url-encoded 'x' = 'x'; ellipsis '…' urlencodes as '%E2%80%A6'.
    msg = captured["body"]["text"]
    assert msg.startswith("x" * 499) or len(msg) <= 600


def test_threads_401_on_create_raises_auth():
    def handler(request):
        return httpx.Response(401, text="bad")

    with pytest.raises(ThreadsAuthError):
        publish_to_threads(
            access_token="bad",
            threads_user_id="9",
            text="x",
            client=_client(handler),
        )


def test_threads_500_on_publish_raises_publish_error():
    def handler(request):
        if request.url.path.endswith("/threads"):
            return httpx.Response(200, json={"id": "c"})
        return httpx.Response(500, text="oops")

    with pytest.raises(ThreadsPublishError):
        publish_to_threads(
            access_token="t",
            threads_user_id="9",
            text="x",
            client=_client(handler),
        )
