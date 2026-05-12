"""Mastodon publisher — Phase 5.5.

Posts a status (toot) to a Mastodon instance via the v1 statuses API:

    POST {instance_url}/api/v1/statuses
    Authorization: Bearer <access_token>
    Idempotency-Key: <random>  (recommended)

The instance URL is per-SocialAccount (federation — each user is on
their own server). Stored on
``SocialAccount.auth_metadata_json["instance_url"]``; falls back to
``settings.mastodon_default_instance``.

Mastodon limits a toot to 500 chars on most instances. Longer copy is
truncated with an ellipsis. Stub fallback shape matches the other
publishers — no token → deterministic synthetic id.
"""

from __future__ import annotations

import hashlib
import secrets

import httpx

from app.core.config import settings
from app.services.publishers import PublishResult


_LIMIT_CHARS = 500


class MastodonAuthError(RuntimeError):
    pass


class MastodonPublishError(RuntimeError):
    pass


def _stub_result(instance_url: str, text: str) -> PublishResult:
    digest = hashlib.sha256(
        (instance_url + "::" + text[:512]).encode("utf-8")
    ).hexdigest()[:18]
    return PublishResult(
        provider="mastodon",
        remote_id=f"stub-{digest}",
        permalink=None,
        raw={"stub": True, "instance_url": instance_url, "text": text},
    )


def publish_to_mastodon(
    *,
    access_token: str | None,
    instance_url: str | None,
    text: str,
    visibility: str = "public",
    client: httpx.Client | None = None,
) -> PublishResult:
    """Posts a single status to Mastodon.

    Args:
        access_token: OAuth bearer token for the user account. Empty/None
            → returns stub.
        instance_url: Per-account Mastodon server URL, e.g.
            ``https://mastodon.social``. Falls back to
            ``settings.mastodon_default_instance``.
        text: Status body. Truncated to 500 chars with ellipsis.
        visibility: ``public`` | ``unlisted`` | ``private`` | ``direct``.
        client: Optional caller-managed httpx.Client (tests use MockTransport).

    Raises:
        MastodonAuthError: 401/403 — token bad / expired / scope missing.
        MastodonPublishError: any other non-200.
    """
    base = (instance_url or settings.mastodon_default_instance).rstrip("/")
    if not access_token:
        return _stub_result(base, text)

    if len(text) > _LIMIT_CHARS:
        text = text[: _LIMIT_CHARS - 1] + "…"

    body = {"status": text, "visibility": visibility}
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        # Idempotency-Key avoids duplicate posts on retry.
        "Idempotency-Key": secrets.token_urlsafe(16),
    }

    owns_client = False
    if client is None:
        client = httpx.Client(timeout=30.0)
        owns_client = True

    try:
        resp = client.post(
            f"{base}/api/v1/statuses", json=body, headers=headers
        )
    finally:
        if owns_client:
            client.close()

    if resp.status_code in (401, 403):
        raise MastodonAuthError(
            f"POST statuses {resp.status_code}: {resp.text[:200]}"
        )
    if resp.status_code != 200:
        raise MastodonPublishError(
            f"POST statuses {resp.status_code}: {resp.text[:200]}"
        )

    data = resp.json() or {}
    return PublishResult(
        provider="mastodon",
        remote_id=str(data.get("id", "")),
        permalink=data.get("url"),
        raw={"id": data.get("id"), "url": data.get("url")},
    )


__all__ = ["publish_to_mastodon", "MastodonAuthError", "MastodonPublishError"]
