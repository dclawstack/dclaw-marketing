"""Email-event normalisation + signature verification (Phase 7.4).

Provider-specific helpers that turn an inbound webhook payload into a
canonical ``(EmailEventKind, occurred_at, recipient, provider_message_id)``
tuple, plus per-provider signature verification.

Verification:
  • Resend  — Svix-style: HMAC-SHA256 of ``f"{msg_id}.{timestamp}.{body}"``,
              base64-encoded, compared against the v1 segment of
              ``svix-signature``. The Svix secret has a ``whsec_``
              prefix that we strip before base64-decoding.
  • Postmark — HMAC-SHA1 of the raw body, base64, compared against
              the ``X-Postmark-Webhook-Signature`` header.
  • SendGrid — ECDSA over the body; we ship a structural check (header
              present + non-empty) plus a TODO marker. The full
              ECDSA-verify ships when the verification public-key
              management lands with the Connect-with-SendGrid OAuth
              flow.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from datetime import datetime, timezone
from typing import Any

from app.models.email_event import EmailEventKind


class SignatureError(RuntimeError):
    pass


# ---------- Verification ---------------------------------------------------


def verify_resend(
    *,
    body: bytes,
    headers: dict[str, str],
    secret: str,
) -> None:
    """Raises ``SignatureError`` when the Svix signature header doesn't
    match the expected HMAC."""
    msg_id = headers.get("svix-id") or headers.get("Svix-Id")
    timestamp = headers.get("svix-timestamp") or headers.get("Svix-Timestamp")
    sig_header = headers.get("svix-signature") or headers.get("Svix-Signature")
    if not (msg_id and timestamp and sig_header and secret):
        raise SignatureError("Resend signature headers/secret missing")
    # Svix secrets are prefixed "whsec_" then base64 of the key bytes.
    raw_secret = (
        base64.b64decode(secret[len("whsec_") :])
        if secret.startswith("whsec_")
        else secret.encode()
    )
    expected = hmac.new(
        raw_secret,
        f"{msg_id}.{timestamp}.{body.decode('utf-8')}".encode("utf-8"),
        hashlib.sha256,
    ).digest()
    expected_b64 = base64.b64encode(expected).decode("ascii")
    # Header is "v1,<b64> v1,<b64> ..." — verify any segment matches.
    for chunk in sig_header.split():
        if "," not in chunk:
            continue
        version, candidate = chunk.split(",", 1)
        if version != "v1":
            continue
        if hmac.compare_digest(candidate, expected_b64):
            return
    raise SignatureError("Resend signature mismatch")


def verify_postmark(
    *,
    body: bytes,
    headers: dict[str, str],
    secret: str,
) -> None:
    header = headers.get("x-postmark-webhook-signature") or headers.get(
        "X-Postmark-Webhook-Signature"
    )
    if not header or not secret:
        raise SignatureError("Postmark signature header/secret missing")
    expected = base64.b64encode(
        hmac.new(secret.encode(), body, hashlib.sha1).digest()
    ).decode("ascii")
    if not hmac.compare_digest(header, expected):
        raise SignatureError("Postmark signature mismatch")


def verify_sendgrid_present(
    *,
    headers: dict[str, str],
) -> None:
    """Structural check only — real ECDSA verify lands later.

    Raises ``SignatureError`` when the signed-webhook headers are missing.
    """
    sig = headers.get(
        "x-twilio-email-event-webhook-signature"
    ) or headers.get("X-Twilio-Email-Event-Webhook-Signature")
    if not sig:
        raise SignatureError("SendGrid signature header missing")


# ---------- Normalisation --------------------------------------------------


def normalise_resend_event(evt: dict[str, Any]) -> dict[str, Any]:
    """Map a Resend event dict to the EmailEvent column set.

    Resend payloads look like:
        {"type": "email.delivered",
         "created_at": "2026-05-19T12:34:56.789Z",
         "data": {"email_id": "abc", "to": ["alice@x.com"], ...}}
    """
    t = (evt.get("type") or "").removeprefix("email.")
    kind_map = {
        "delivered": EmailEventKind.delivered,
        "opened": EmailEventKind.opened,
        "clicked": EmailEventKind.clicked,
        "bounced": EmailEventKind.bounced,
        "complained": EmailEventKind.complained,
        "unsubscribed": EmailEventKind.unsubscribed,
        "failed": EmailEventKind.failed,
    }
    kind = kind_map.get(t, EmailEventKind.other)
    occurred = _parse_iso(evt.get("created_at"))
    data = evt.get("data") or {}
    tos = data.get("to") or []
    recipient = tos[0] if isinstance(tos, list) and tos else None
    msg_id = data.get("email_id") or data.get("id")
    return {
        "kind": kind,
        "occurred_at": occurred,
        "recipient": recipient,
        "provider_message_id": msg_id,
    }


def normalise_postmark_event(evt: dict[str, Any]) -> dict[str, Any]:
    """Postmark posts one event per request with shape:
        {"RecordType": "Delivery" | "Open" | "Click" | "Bounce" | ...,
         "MessageID": "...", "Recipient": "...",
         "DeliveredAt" / "ReceivedAt": "iso8601", ...}
    """
    t = (evt.get("RecordType") or "").lower()
    kind_map = {
        "delivery": EmailEventKind.delivered,
        "open": EmailEventKind.opened,
        "click": EmailEventKind.clicked,
        "bounce": EmailEventKind.bounced,
        "spamcomplaint": EmailEventKind.complained,
        "subscriptionchange": EmailEventKind.unsubscribed,
    }
    kind = kind_map.get(t, EmailEventKind.other)
    occurred = _parse_iso(
        evt.get("DeliveredAt")
        or evt.get("ReceivedAt")
        or evt.get("BouncedAt")
        or evt.get("ChangedAt")
    )
    return {
        "kind": kind,
        "occurred_at": occurred,
        "recipient": evt.get("Recipient") or evt.get("Email"),
        "provider_message_id": evt.get("MessageID"),
    }


def normalise_sendgrid_event(evt: dict[str, Any]) -> dict[str, Any]:
    """SendGrid posts an array; the caller iterates. Each event has:
        {"event": "delivered" | "open" | "click" | "bounce" | ...,
         "email": "alice@x.com", "timestamp": 1700000000,
         "sg_message_id": "...", ...}
    """
    t = (evt.get("event") or "").lower()
    kind_map = {
        "delivered": EmailEventKind.delivered,
        "open": EmailEventKind.opened,
        "click": EmailEventKind.clicked,
        "bounce": EmailEventKind.bounced,
        "dropped": EmailEventKind.failed,
        "spamreport": EmailEventKind.complained,
        "unsubscribe": EmailEventKind.unsubscribed,
        "group_unsubscribe": EmailEventKind.unsubscribed,
    }
    kind = kind_map.get(t, EmailEventKind.other)
    ts = evt.get("timestamp")
    occurred = (
        datetime.fromtimestamp(ts, tz=timezone.utc) if isinstance(ts, (int, float)) else None
    )
    return {
        "kind": kind,
        "occurred_at": occurred or datetime.now(tz=timezone.utc),
        "recipient": evt.get("email"),
        "provider_message_id": evt.get("sg_message_id"),
    }


def _parse_iso(s: str | None) -> datetime:
    if not s:
        return datetime.now(tz=timezone.utc)
    # Both Resend ("2026-05-19T12:34:56.789Z") and Postmark
    # ("2026-05-19T12:34:56.789-04:00") are RFC3339; fromisoformat handles
    # the latter natively on 3.11+; we strip a trailing Z for the former.
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return datetime.now(tz=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


__all__ = [
    "SignatureError",
    "verify_resend",
    "verify_postmark",
    "verify_sendgrid_present",
    "normalise_resend_event",
    "normalise_postmark_event",
    "normalise_sendgrid_event",
]
