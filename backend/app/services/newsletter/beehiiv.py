"""Beehiiv newsletter adapter — Phase 7.6.

Two-step send via the Beehiiv v2 API:

  1. POST /v2/publications/{publication_id}/posts
       — create draft (body_html, title, subject_line)
  2. POST /v2/publications/{publication_id}/posts/{post_id}/send
       — fire (immediate)

Auth: Bearer token in Authorization header.

Stub fallback when no key or publication_id.
"""

from __future__ import annotations

import hashlib

import httpx

from app.core.config import settings
from app.services.newsletter import NewsletterResult


_BASE = "https://api.beehiiv.com/v2"


class BeehiivAuthError(RuntimeError):
    pass


class BeehiivPublishError(RuntimeError):
    pass


def _stub_result(subject: str, html: str) -> NewsletterResult:
    digest = hashlib.sha256(
        (subject + "::" + html[:512]).encode("utf-8")
    ).hexdigest()[:18]
    return NewsletterResult(
        provider="beehiiv",
        campaign_id=f"bh_stub_{digest}",
        recipient_count=None,
        raw={"stub": True, "subject": subject},
    )


async def send_campaign(
    *,
    subject: str,
    html: str,
    title: str | None = None,
    client: httpx.AsyncClient | None = None,
) -> NewsletterResult:
    """Creates + sends a Beehiiv post."""
    if not settings.beehiiv_api_key or not settings.beehiiv_publication_id:
        return _stub_result(subject, html)

    headers = {
        "Authorization": f"Bearer {settings.beehiiv_api_key}",
        "Content-Type": "application/json",
    }
    base = f"{_BASE}/publications/{settings.beehiiv_publication_id}"

    owns_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=30.0)
        owns_client = True

    try:
        # 1. Create draft
        body = {
            "title": title or subject,
            "subject_line": subject,
            "body_html": html,
            "status": "draft",
        }
        try:
            create = await client.post(f"{base}/posts", json=body, headers=headers)
        except httpx.HTTPError as exc:
            raise BeehiivPublishError(f"create transport: {exc}") from exc
        if create.status_code in (401, 403):
            raise BeehiivAuthError(
                f"create {create.status_code}: {create.text[:200]}"
            )
        if create.status_code not in (200, 201):
            raise BeehiivPublishError(
                f"create {create.status_code}: {create.text[:200]}"
            )
        post_id = ((create.json() or {}).get("data") or {}).get("id") or (
            create.json() or {}
        ).get("id")

        # 2. Send
        send = await client.post(
            f"{base}/posts/{post_id}/send",
            json={},
            headers=headers,
        )
        if send.status_code not in (200, 201, 204):
            raise BeehiivPublishError(
                f"send {send.status_code}: {send.text[:200]}"
            )
    finally:
        if owns_client:
            await client.aclose()

    return NewsletterResult(
        provider="beehiiv",
        campaign_id=str(post_id),
        recipient_count=None,
        raw={"post_id": post_id},
    )


__all__ = ["send_campaign", "BeehiivAuthError", "BeehiivPublishError"]
