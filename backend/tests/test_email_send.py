"""Phase 7.1 + 7.4 — multi-provider email-send adapter unit tests."""

from __future__ import annotations

import httpx
import pytest
import pytest_asyncio

from app.services import email_send as es
from app.services.email_send import SendProvider, send_email


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


# ---------- stub path ------------------------------------------------


@pytest.mark.asyncio
async def test_stub_returns_synthetic_message_id():
    res = await send_email(
        to=["alice@example.com"],
        subject="hi",
        html="<p>hello</p>",
    )
    assert res.provider == SendProvider.stub
    assert res.message_id.startswith("msg_stub_")


@pytest.mark.asyncio
async def test_stub_is_deterministic():
    a = await send_email(
        to=["a@x.io", "b@x.io"], subject="s", html="<p>h</p>"
    )
    b = await send_email(
        to=["b@x.io", "a@x.io"], subject="s", html="<p>h</p>"
    )
    assert a.message_id == b.message_id


@pytest.mark.asyncio
async def test_empty_recipients_raises():
    with pytest.raises(ValueError):
        await send_email(to=[], subject="x", html="x")


# ---------- per-provider direct paths --------------------------------


@pytest.mark.asyncio
async def test_sendgrid_path(monkeypatch):
    """When sendgrid_api_key is set + the API returns 202 with
    X-Message-Id, we get a sendgrid SendResult.
    """
    monkeypatch.setattr(es.settings, "sendgrid_api_key", "sg-key")
    monkeypatch.setattr(es.settings, "postmark_api_key", "")
    monkeypatch.setattr(es.settings, "resend_api_key", "")

    async def fake_client_init(self, **kw):
        pass

    captured = {}

    class FakeResp:
        def __init__(self):
            self.headers = {"X-Message-Id": "sg-msg-xyz"}
            self.status_code = 202
            self.content = b""

        def raise_for_status(self):
            pass

    class FakeClient:
        def __init__(self, *a, **kw):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers=None, json=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return FakeResp()

    monkeypatch.setattr(es.httpx, "AsyncClient", FakeClient)

    res = await send_email(
        to=["alice@example.com"], subject="hi", html="<p>hello</p>"
    )
    assert res.provider == SendProvider.sendgrid
    assert res.message_id == "sg-msg-xyz"
    assert captured["url"].endswith("/v3/mail/send")
    assert captured["headers"]["Authorization"] == "Bearer sg-key"


@pytest.mark.asyncio
async def test_postmark_path(monkeypatch):
    monkeypatch.setattr(es.settings, "sendgrid_api_key", "")
    monkeypatch.setattr(es.settings, "postmark_api_key", "pm-key")
    monkeypatch.setattr(es.settings, "resend_api_key", "")

    class FakeResp:
        status_code = 200
        content = b'{"MessageID":"pm-msg-1"}'

        def raise_for_status(self):
            pass

        def json(self):
            return {"MessageID": "pm-msg-1"}

    class FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers=None, json=None):
            assert url.endswith("/email")
            assert headers["X-Postmark-Server-Token"] == "pm-key"
            return FakeResp()

    monkeypatch.setattr(es.httpx, "AsyncClient", lambda **kw: FakeClient())

    res = await send_email(
        to=["alice@example.com"], subject="hi", html="<p>hello</p>"
    )
    assert res.provider == SendProvider.postmark
    assert res.message_id == "pm-msg-1"


@pytest.mark.asyncio
async def test_fallback_chain_sendgrid_to_postmark(monkeypatch):
    """SendGrid raises, Postmark succeeds — we should land on Postmark."""
    monkeypatch.setattr(es.settings, "sendgrid_api_key", "sg-key")
    monkeypatch.setattr(es.settings, "postmark_api_key", "pm-key")
    monkeypatch.setattr(es.settings, "resend_api_key", "")

    async def boom_sg(**kw):
        raise httpx.HTTPError("sendgrid 500")

    async def ok_pm(**kw):
        return es.SendResult(
            message_id="pm-recovered",
            provider=SendProvider.postmark,
            to=kw["to"],
            subject=kw["subject"],
        )

    monkeypatch.setattr(es, "_send_via_sendgrid", boom_sg)
    monkeypatch.setattr(es, "_send_via_postmark", ok_pm)

    res = await send_email(
        to=["alice@example.com"], subject="hi", html="<p>x</p>"
    )
    assert res.provider == SendProvider.postmark
    assert res.message_id == "pm-recovered"


@pytest.mark.asyncio
async def test_all_providers_fail_falls_through_to_stub(monkeypatch):
    monkeypatch.setattr(es.settings, "sendgrid_api_key", "sg")
    monkeypatch.setattr(es.settings, "postmark_api_key", "pm")
    monkeypatch.setattr(es.settings, "resend_api_key", "r")

    async def boom(**kw):
        raise httpx.HTTPError("nope")

    monkeypatch.setattr(es, "_send_via_sendgrid", boom)
    monkeypatch.setattr(es, "_send_via_postmark", boom)
    monkeypatch.setattr(es, "_send_via_resend", boom)

    res = await send_email(
        to=["alice@example.com"], subject="hi", html="<p>x</p>"
    )
    assert res.provider == SendProvider.stub


@pytest.mark.asyncio
async def test_resend_used_when_only_resend_key(monkeypatch):
    monkeypatch.setattr(es.settings, "sendgrid_api_key", "")
    monkeypatch.setattr(es.settings, "postmark_api_key", "")
    monkeypatch.setattr(es.settings, "resend_api_key", "r-key")

    async def ok_resend(**kw):
        return es.SendResult(
            message_id="re-1",
            provider=SendProvider.resend,
            to=kw["to"],
            subject=kw["subject"],
        )

    monkeypatch.setattr(es, "_send_via_resend", ok_resend)
    res = await send_email(
        to=["alice@example.com"], subject="hi", html="<p>x</p>"
    )
    assert res.provider == SendProvider.resend
