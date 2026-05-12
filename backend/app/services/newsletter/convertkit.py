"""ConvertKit newsletter adapter — Phase 7.6.

Two-step broadcast send via ConvertKit v3:

  1. POST /v3/broadcasts        → create the broadcast
  2. POST /v3/broadcasts/{id}/send_at  → schedule send

Auth: api_secret as query param or in the body.

Stub fallback when ``CONVERTKIT_API_SECRET`` is unset.
"""

from __future__ import annotations

import hashlib

import httpx

from app.core.config import settings
from app.services.newsletter import NewsletterResult


_BASE = "https://api.convertkit.com/v3"


class ConvertKitAuthError(RuntimeError):
    pass


class ConvertKitPublishError(RuntimeError):
    pass


def _stub_result(subject: str, html: str) -> NewsletterResult:
    digest = hashlib.sha256(
        (subject + "::" + html[:512]).encode("utf-8")
    ).hexdigest()[:18]
    return NewsletterResult(
        provider="convertkit",
        campaign_id=f"ck_stub_{digest}",
        recipient_count=None,
        raw={"stub": True, "subject": subject},
    )


async def send_campaign(
    *,
    subject: str,
    html: str,
    description: str | None = None,
    client: httpx.AsyncClient | None = None,
) -> NewsletterResult:
    """Creates + schedules a ConvertKit broadcast for immediate send.

    Note: ConvertKit broadcasts target the publication's full subscriber
    list — no per-broadcast list_id is needed.
    """
    if not settings.convertkit_api_secret:
        return _stub_result(subject, html)

    owns_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=30.0)
        owns_client = True

    try:
        # 1. Create broadcast
        try:
            create = await client.post(
                f"{_BASE}/broadcasts",
                json={
                    "api_secret": settings.convertkit_api_secret,
                    "subject": subject,
                    "content": html,
                    "description": description or subject,
                },
            )
        except httpx.HTTPError as exc:
            raise ConvertKitPublishError(f"create transport: {exc}") from exc
        if create.status_code in (401, 403):
            raise ConvertKitAuthError(
                f"create {create.status_code}: {create.text[:200]}"
            )
        if create.status_code not in (200, 201):
            raise ConvertKitPublishError(
                f"create {create.status_code}: {create.text[:200]}"
            )
        data = create.json() or {}
        broadcast = data.get("broadcast") or data
        broadcast_id = broadcast.get("id")

        # 2. Schedule send (immediate — server interprets missing
        # send_at as "now").
        send = await client.post(
            f"{_BASE}/broadcasts/{broadcast_id}/send_at",
            json={"api_secret": settings.convertkit_api_secret},
        )
        if send.status_code not in (200, 201, 204):
            raise ConvertKitPublishError(
                f"send {send.status_code}: {send.text[:200]}"
            )
    finally:
        if owns_client:
            await client.aclose()

    return NewsletterResult(
        provider="convertkit",
        campaign_id=str(broadcast_id),
        recipient_count=None,
        raw={"broadcast_id": broadcast_id},
    )


__all__ = ["send_campaign", "ConvertKitAuthError", "ConvertKitPublishError"]
