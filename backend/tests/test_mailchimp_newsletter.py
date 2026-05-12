"""Phase 7.5 — Mailchimp newsletter adapter unit tests."""

from __future__ import annotations

import json

import httpx
import pytest
import pytest_asyncio

from app.services.newsletter import mailchimp as mc
from app.services.newsletter.mailchimp import (
    MailchimpAuthError,
    MailchimpPublishError,
    send_campaign,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


@pytest.mark.asyncio
async def test_stub_when_no_api_key(monkeypatch):
    monkeypatch.setattr(mc.settings, "mailchimp_api_key", "")
    monkeypatch.setattr(mc.settings, "mailchimp_server_prefix", "us21")

    res = await send_campaign(
        list_id="abc", subject="hello", html="<p>x</p>",
    )
    assert res.provider == "mailchimp"
    assert res.campaign_id.startswith("mc_stub_")
    assert res.raw["stub"] is True


@pytest.mark.asyncio
async def test_stub_when_no_server_prefix(monkeypatch):
    monkeypatch.setattr(mc.settings, "mailchimp_api_key", "key")
    monkeypatch.setattr(mc.settings, "mailchimp_server_prefix", "")

    res = await send_campaign(
        list_id="abc", subject="hello", html="<p>x</p>",
    )
    assert res.raw["stub"] is True


@pytest.mark.asyncio
async def test_full_three_step_flow(monkeypatch):
    monkeypatch.setattr(mc.settings, "mailchimp_api_key", "key-us21")
    monkeypatch.setattr(mc.settings, "mailchimp_server_prefix", "us21")
    monkeypatch.setattr(
        mc.settings, "resend_from_email", "DClaw <noreply@dclaw.io>"
    )

    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        calls.append(f"{request.method} {path}")
        if request.method == "POST" and path.endswith("/campaigns"):
            return httpx.Response(
                200,
                json={
                    "id": "camp-1",
                    "recipients": {"recipient_count": 1234, "list_id": "abc"},
                },
            )
        if request.method == "PUT" and "/content" in path:
            return httpx.Response(200, json={"ok": True})
        if request.method == "POST" and "/actions/send" in path:
            return httpx.Response(204)
        return httpx.Response(404, text=f"unexpected {request.method} {path}")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    res = await send_campaign(
        list_id="abc",
        subject="hello",
        html="<p>x</p>",
        client=client,
    )
    await client.aclose()

    assert calls == [
        "POST /3.0/campaigns",
        "PUT /3.0/campaigns/camp-1/content",
        "POST /3.0/campaigns/camp-1/actions/send",
    ]
    assert res.campaign_id == "camp-1"
    assert res.recipient_count == 1234


@pytest.mark.asyncio
async def test_create_401_raises_auth_error(monkeypatch):
    monkeypatch.setattr(mc.settings, "mailchimp_api_key", "bad")
    monkeypatch.setattr(mc.settings, "mailchimp_server_prefix", "us21")
    monkeypatch.setattr(mc.settings, "resend_from_email", "x <x@y.io>")

    def handler(request):
        return httpx.Response(401, text="invalid api key")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with pytest.raises(MailchimpAuthError):
        await send_campaign(
            list_id="abc", subject="x", html="<p>x</p>", client=client,
        )
    await client.aclose()


@pytest.mark.asyncio
async def test_content_step_failure(monkeypatch):
    monkeypatch.setattr(mc.settings, "mailchimp_api_key", "k")
    monkeypatch.setattr(mc.settings, "mailchimp_server_prefix", "us21")
    monkeypatch.setattr(mc.settings, "resend_from_email", "x <x@y.io>")

    def handler(request):
        if request.method == "POST" and request.url.path.endswith("/campaigns"):
            return httpx.Response(
                200, json={"id": "c1", "recipients": {"recipient_count": 1}}
            )
        return httpx.Response(500, text="content failed")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with pytest.raises(MailchimpPublishError, match="content"):
        await send_campaign(
            list_id="abc", subject="x", html="<p>x</p>", client=client,
        )
    await client.aclose()


@pytest.mark.asyncio
async def test_send_step_failure(monkeypatch):
    monkeypatch.setattr(mc.settings, "mailchimp_api_key", "k")
    monkeypatch.setattr(mc.settings, "mailchimp_server_prefix", "us21")
    monkeypatch.setattr(mc.settings, "resend_from_email", "x <x@y.io>")

    def handler(request):
        path = request.url.path
        if request.method == "POST" and path.endswith("/campaigns"):
            return httpx.Response(
                200, json={"id": "c1", "recipients": {"recipient_count": 1}}
            )
        if request.method == "PUT" and "/content" in path:
            return httpx.Response(200, json={})
        return httpx.Response(500, text="send failed")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with pytest.raises(MailchimpPublishError, match="send"):
        await send_campaign(
            list_id="abc", subject="x", html="<p>x</p>", client=client,
        )
    await client.aclose()


@pytest.mark.asyncio
async def test_create_body_shape(monkeypatch):
    monkeypatch.setattr(mc.settings, "mailchimp_api_key", "k")
    monkeypatch.setattr(mc.settings, "mailchimp_server_prefix", "us21")
    monkeypatch.setattr(mc.settings, "resend_from_email", "DClaw <noreply@dclaw.io>")

    captured: dict = {}

    def handler(request):
        path = request.url.path
        if request.method == "POST" and path.endswith("/campaigns"):
            captured["body"] = json.loads(request.content.decode("utf-8"))
            return httpx.Response(
                200, json={"id": "c1", "recipients": {"recipient_count": 1}}
            )
        if request.method == "PUT" and "/content" in path:
            return httpx.Response(200, json={})
        return httpx.Response(204)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    await send_campaign(
        list_id="my-list",
        subject="Q2 launch",
        html="<h1>hi</h1>",
        from_name="DClaw Team",
        reply_to="hi@dclaw.io",
        client=client,
    )
    await client.aclose()

    body = captured["body"]
    assert body["type"] == "regular"
    assert body["recipients"]["list_id"] == "my-list"
    assert body["settings"]["subject_line"] == "Q2 launch"
    assert body["settings"]["from_name"] == "DClaw Team"
    assert body["settings"]["reply_to"] == "hi@dclaw.io"
