"""Phase 7.4 — Email-event webhook unit tests (verification + ingest)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.email_event import EmailEvent, EmailEventKind, EmailEventProvider
from app.models.lead import Lead, LeadActivity
from app.models.organization import Organization
from app.services.email_events import (
    SignatureError,
    normalise_postmark_event,
    normalise_resend_event,
    normalise_sendgrid_event,
    verify_postmark,
    verify_resend,
    verify_sendgrid_present,
)
from tests.conftest import test_engine


# ---------- Signature helpers (pure-Python, no DB) -------------------------


def test_verify_resend_happy_path():
    secret = "whsec_" + base64.b64encode(b"key1234").decode("ascii")
    body = b'{"hello": "world"}'
    msg_id = "msg_1"
    ts = "2026-05-19T12:00:00Z"
    raw_key = base64.b64decode(secret[len("whsec_") :])
    digest = hmac.new(
        raw_key,
        f"{msg_id}.{ts}.{body.decode()}".encode("utf-8"),
        hashlib.sha256,
    ).digest()
    sig = "v1," + base64.b64encode(digest).decode("ascii")

    verify_resend(
        body=body,
        headers={
            "svix-id": msg_id,
            "svix-timestamp": ts,
            "svix-signature": sig,
        },
        secret=secret,
    )


def test_verify_resend_bad_signature_raises():
    secret = "whsec_" + base64.b64encode(b"key1234").decode("ascii")
    with pytest.raises(SignatureError):
        verify_resend(
            body=b"{}",
            headers={
                "svix-id": "x",
                "svix-timestamp": "y",
                "svix-signature": "v1,deadbeef",
            },
            secret=secret,
        )


def test_verify_postmark_happy_path():
    secret = "topsecret"
    body = b'{"RecordType": "Delivery"}'
    expected = base64.b64encode(
        hmac.new(secret.encode(), body, hashlib.sha1).digest()
    ).decode()
    verify_postmark(
        body=body,
        headers={"x-postmark-webhook-signature": expected},
        secret=secret,
    )


def test_verify_postmark_bad_raises():
    with pytest.raises(SignatureError):
        verify_postmark(
            body=b"{}",
            headers={"x-postmark-webhook-signature": "wrong"},
            secret="topsecret",
        )


def test_verify_sendgrid_present_passes_when_header_set():
    verify_sendgrid_present(
        headers={"x-twilio-email-event-webhook-signature": "abc"}
    )


def test_verify_sendgrid_present_raises_when_missing():
    with pytest.raises(SignatureError):
        verify_sendgrid_present(headers={})


# ---------- Normalisers (pure) ---------------------------------------------


def test_normalise_resend_opened():
    out = normalise_resend_event(
        {
            "type": "email.opened",
            "created_at": "2026-05-19T12:34:56Z",
            "data": {
                "email_id": "msg-1",
                "to": ["alice@example.com"],
            },
        }
    )
    assert out["kind"] == EmailEventKind.opened
    assert out["recipient"] == "alice@example.com"
    assert out["provider_message_id"] == "msg-1"
    assert out["occurred_at"].tzinfo is not None


def test_normalise_postmark_bounce():
    out = normalise_postmark_event(
        {
            "RecordType": "Bounce",
            "MessageID": "pm-1",
            "Recipient": "alice@example.com",
            "BouncedAt": "2026-05-19T10:00:00-04:00",
        }
    )
    assert out["kind"] == EmailEventKind.bounced
    assert out["recipient"] == "alice@example.com"
    assert out["provider_message_id"] == "pm-1"


def test_normalise_sendgrid_unsubscribe():
    out = normalise_sendgrid_event(
        {
            "event": "group_unsubscribe",
            "email": "alice@example.com",
            "timestamp": 1700000000,
            "sg_message_id": "sg-1",
        }
    )
    assert out["kind"] == EmailEventKind.unsubscribed
    assert out["recipient"] == "alice@example.com"
    assert out["occurred_at"] == datetime.fromtimestamp(
        1700000000, tz=timezone.utc
    )


# ---------- HTTP ingest endpoints -----------------------------------------


@pytest_asyncio.fixture
async def org_and_lead():
    """Seed an org + a lead with a recognisable email so the webhook can
    bridge to LeadActivity."""
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        org = Organization(slug="hookco", name="Hook Co")
        session.add(org)
        await session.flush()
        lead = Lead(
            organization_id=org.id,
            email="alice@hook.co",
            first_name="Alice",
        )
        session.add(lead)
        await session.commit()
        await session.refresh(org)
        await session.refresh(lead)
        return org, lead


@pytest.mark.asyncio
async def test_resend_webhook_writes_email_event_and_lead_activity(
    client, org_and_lead, monkeypatch
):
    org, lead = org_and_lead
    monkeypatch.setattr(settings, "resend_webhook_secret", "", raising=False)

    payload = {
        "type": "email.opened",
        "created_at": "2026-05-19T12:34:56Z",
        "data": {"email_id": "msg-x1", "to": ["alice@hook.co"]},
    }
    res = await client.post(
        "/api/v1/webhooks/email/resend",
        json=payload,
    )
    assert res.status_code == 202, res.text

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        events = (
            (await session.execute(select(EmailEvent))).scalars().all()
        )
        assert len(events) == 1
        evt = events[0]
        assert evt.provider == EmailEventProvider.resend
        assert evt.kind == EmailEventKind.opened
        assert evt.recipient == "alice@hook.co"
        assert evt.organization_id == lead.organization_id
        assert evt.lead_activity_id is not None

        activity = await session.get(LeadActivity, evt.lead_activity_id)
        assert activity is not None
        assert activity.lead_id == lead.id


@pytest.mark.asyncio
async def test_postmark_webhook_works(client, org_and_lead, monkeypatch):
    monkeypatch.setattr(
        settings, "postmark_webhook_secret", "", raising=False
    )
    payload = {
        "RecordType": "Click",
        "MessageID": "pm-1",
        "Recipient": "alice@hook.co",
        "ReceivedAt": "2026-05-19T11:00:00Z",
    }
    res = await client.post(
        "/api/v1/webhooks/email/postmark",
        json=payload,
    )
    assert res.status_code == 202

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        evt = (
            (await session.execute(select(EmailEvent)))
            .scalars()
            .one_or_none()
        )
        assert evt is not None
        assert evt.kind == EmailEventKind.clicked


@pytest.mark.asyncio
async def test_sendgrid_webhook_accepts_array(client, org_and_lead, monkeypatch):
    monkeypatch.setattr(
        settings, "sendgrid_webhook_verify", False, raising=False
    )
    payload = [
        {
            "event": "delivered",
            "email": "alice@hook.co",
            "timestamp": 1700000000,
            "sg_message_id": "sg-1",
        },
        {
            "event": "bounce",
            "email": "ghost@nowhere.co",
            "timestamp": 1700000001,
            "sg_message_id": "sg-2",
        },
    ]
    res = await client.post(
        "/api/v1/webhooks/email/sendgrid",
        json=payload,
    )
    assert res.status_code == 202
    assert res.json()["events"] == 2

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        events = (await session.execute(select(EmailEvent))).scalars().all()
        assert len(events) == 2
        kinds = sorted(e.kind.value for e in events)
        assert kinds == ["bounced", "delivered"]


@pytest.mark.asyncio
async def test_unknown_recipient_writes_event_without_lead_activity(
    client, monkeypatch
):
    """An event for a recipient we don't have a Lead for still lands in
    email_events but doesn't get a LeadActivity bridge."""
    monkeypatch.setattr(settings, "resend_webhook_secret", "", raising=False)
    res = await client.post(
        "/api/v1/webhooks/email/resend",
        json={
            "type": "email.delivered",
            "created_at": "2026-05-19T12:34:56Z",
            "data": {"email_id": "msg-z", "to": ["stranger@nowhere.co"]},
        },
    )
    assert res.status_code == 202

    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        evt = (
            (await session.execute(select(EmailEvent))).scalars().one()
        )
        assert evt.lead_activity_id is None
        assert evt.organization_id is None
