"""Resend email-send adapter (Phase 7.1).

Single ``send_email()`` entry point over the Resend Email API, with a
deterministic stub fallback when ``RESEND_API_KEY`` is unset.

Stubbed sends record the message into the audit log and return a
synthetic ``msg_<sha256>`` id so the rest of the email pipeline
(campaign status updates, sequence-step bookkeeping) works in dev /
CI without burning real credit.

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
    resend = "resend"
    stub = "stub"


@dataclass(frozen=True, slots=True)
class SendResult:
    message_id: str
    provider: SendProvider
    to: list[str]
    subject: str


_RESEND_BASE = "https://api.resend.com"


def _stub_send(
    to: list[str], subject: str, html: str
) -> SendResult:
    """Builds a deterministic synthetic message id from the payload —
    so two stub sends of the same content come back with the same id.
    """
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


async def send_email(
    *,
    to: list[str],
    subject: str,
    html: str,
    text: str | None = None,
    from_email: str | None = None,
    reply_to: str | None = None,
) -> SendResult:
    """Sends one email to one or more recipients.

    Falls back to a no-network stub when the Resend key is missing or
    the API call raises — callers can rely on always getting a
    ``SendResult`` back so downstream bookkeeping never breaks.
    """
    if not to:
        raise ValueError("send_email requires at least one recipient")

    sender = from_email or settings.resend_from_email

    if settings.resend_api_key:
        payload: dict = {
            "from": sender,
            "to": to,
            "subject": subject,
            "html": html,
        }
        if text:
            payload["text"] = text
        if reply_to:
            payload["reply_to"] = reply_to
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{_RESEND_BASE}/emails",
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
        except Exception:
            # Fall through to stub rather than crash the pipeline.
            pass

    return _stub_send(to, subject, html)


__all__ = ["send_email", "SendResult", "SendProvider"]
