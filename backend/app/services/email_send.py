"""Multi-provider email-send adapter (Phase 7.1 + 7.4).

Providers, in send-priority order:

  1. SendGrid (sendgrid_api_key)        ← v3 /mail/send, X-Message-Id response
  2. Postmark (postmark_api_key)        ← /email, MessageID in JSON
  3. Resend   (resend_api_key)          ← /emails, id in JSON
  4. Stub                                 ← deterministic msg_stub_<sha>

The first provider with a non-empty API key wins. On transport error
we fall through to the next provider, then finally to the stub —
callers can always rely on receiving a ``SendResult`` back so
downstream bookkeeping (campaign status, sequence-step state, cost
ledger) never breaks.

Per PLAN-v1.2 §v2.0 §5.2 — outbound email is hard-gated by default;
this adapter is the *transport*, not the policy. Callers must already
have an Approval.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum

import httpx

from app.core.config import settings


class SendProvider(str, Enum):
    sendgrid = "sendgrid"
    postmark = "postmark"
    resend = "resend"
    stub = "stub"


@dataclass(frozen=True, slots=True)
class SendResult:
    message_id: str
    provider: SendProvider
    to: list[str]
    subject: str


# ---------- provider URLs --------------------------------------------

_SENDGRID_URL = "https://api.sendgrid.com/v3/mail/send"
_POSTMARK_URL = "https://api.postmarkapp.com/email"
_RESEND_URL = "https://api.resend.com/emails"


# ---------- stub -----------------------------------------------------


def _stub_send(to: list[str], subject: str, html: str) -> SendResult:
    digest = hashlib.sha256(
        ("|".join(sorted(to)) + "::" + subject + "::" + html[:512]).encode(
            "utf-8"
        )
    ).hexdigest()
    return SendResult(
        message_id=f"msg_stub_{digest[:24]}",
        provider=SendProvider.stub,
        to=list(to),
        subject=subject,
    )


# ---------- provider implementations ---------------------------------


async def _send_via_sendgrid(
    *,
    to: list[str],
    subject: str,
    html: str,
    text: str | None,
    from_email: str,
    reply_to: str | None,
) -> SendResult:
    body = {
        "personalizations": [{"to": [{"email": addr} for addr in to]}],
        "from": {"email": from_email},
        "subject": subject,
        "content": [{"type": "text/html", "value": html}],
    }
    if text:
        body["content"].insert(0, {"type": "text/plain", "value": text})
    if reply_to:
        body["reply_to"] = {"email": reply_to}

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            _SENDGRID_URL,
            headers={
                "Authorization": f"Bearer {settings.sendgrid_api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )
        resp.raise_for_status()
        # SendGrid returns 202 Accepted with the message id in the
        # X-Message-Id header.
        message_id = resp.headers.get("X-Message-Id", "") or resp.headers.get(
            "x-message-id", ""
        )
        return SendResult(
            message_id=str(message_id),
            provider=SendProvider.sendgrid,
            to=list(to),
            subject=subject,
        )


async def _send_via_postmark(
    *,
    to: list[str],
    subject: str,
    html: str,
    text: str | None,
    from_email: str,
    reply_to: str | None,
) -> SendResult:
    body: dict = {
        "From": from_email,
        "To": ",".join(to),
        "Subject": subject,
        "HtmlBody": html,
    }
    if text:
        body["TextBody"] = text
    if reply_to:
        body["ReplyTo"] = reply_to

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            _POSTMARK_URL,
            headers={
                "X-Postmark-Server-Token": settings.postmark_api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json=body,
        )
        resp.raise_for_status()
        data = resp.json() if resp.content else {}
        return SendResult(
            message_id=str(data.get("MessageID", "")),
            provider=SendProvider.postmark,
            to=list(to),
            subject=subject,
        )


async def _send_via_resend(
    *,
    to: list[str],
    subject: str,
    html: str,
    text: str | None,
    from_email: str,
    reply_to: str | None,
) -> SendResult:
    payload: dict = {
        "from": from_email,
        "to": to,
        "subject": subject,
        "html": html,
    }
    if text:
        payload["text"] = text
    if reply_to:
        payload["reply_to"] = reply_to

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            _RESEND_URL,
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return SendResult(
            message_id=str(data.get("id", "")),
            provider=SendProvider.resend,
            to=list(to),
            subject=subject,
        )


# ---------- public entry point ---------------------------------------


async def send_email(
    *,
    to: list[str],
    subject: str,
    html: str,
    text: str | None = None,
    from_email: str | None = None,
    reply_to: str | None = None,
) -> SendResult:
    """Sends one email. Tries providers in priority order; falls
    through to the deterministic stub when all providers are absent
    or all raise.
    """
    if not to:
        raise ValueError("send_email requires at least one recipient")

    sender = from_email or settings.resend_from_email
    common = dict(
        to=to, subject=subject, html=html, text=text,
        from_email=sender, reply_to=reply_to,
    )

    # Try each provider in priority order. On any exception, fall
    # through to the next.
    if settings.sendgrid_api_key:
        try:
            return await _send_via_sendgrid(**common)
        except Exception:
            pass
    if settings.postmark_api_key:
        try:
            return await _send_via_postmark(**common)
        except Exception:
            pass
    if settings.resend_api_key:
        try:
            return await _send_via_resend(**common)
        except Exception:
            pass

    return _stub_send(to, subject, html)


__all__ = ["send_email", "SendResult", "SendProvider"]
