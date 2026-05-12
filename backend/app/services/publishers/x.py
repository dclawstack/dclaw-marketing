"""X (Twitter) publisher — Phase 5.3.

Posts to X via the v2 API:

    POST https://api.twitter.com/2/tweets
    Authorization: Bearer <user_oauth_2_access_token>

The user identifier (account handle) is on SocialAccount.handle; the
OAuth 2.0 user-context access token in SocialAccount.access_token.

X v2 limits a tweet to 280 chars (without paid Premium). Longer copy
is truncated with an ellipsis. Stub fallback matches the Bluesky /
LinkedIn shape.
"""

from __future__ import annotations

import hashlib

import httpx

from app.services.publishers import PublishResult


_BASE = "https://api.twitter.com/2"
_LIMIT_CHARS = 280


class XAuthError(RuntimeError):
    pass


class XPublishError(RuntimeError):
    pass


def _stub_result(handle: str, text: str) -> PublishResult:
    digest = hashlib.sha256(
        (handle + "::" + text[:512]).encode("utf-8")
    ).hexdigest()[:18]
    return PublishResult(
        provider="x",
        remote_id=f"stub-{digest}",
        permalink=None,
        raw={"stub": True, "handle": handle, "text": text},
    )


def publish_to_x(
    *,
    access_token: str | None,
    handle: str,
    text: str,
    client: httpx.Client | None = None,
) -> PublishResult:
    """Publishes a single tweet.

    Args:
        access_token: OAuth 2.0 user-context bearer token from the
            SocialAccount. Empty/None → returns stub.
        handle: The user's @handle (used to build the permalink).
        text: Tweet body. Truncated to 280 chars with an ellipsis.
        client: Optional caller-managed httpx.Client (kept open by the
            caller) — tests use MockTransport.

    Raises:
        XAuthError: 401/403 — bad / expired token, or write-perm
            scope missing.
        XPublishError: any other non-201.
    """
    if not access_token:
        return _stub_result(handle, text)

    if len(text) > _LIMIT_CHARS:
        text = text[: _LIMIT_CHARS - 1] + "…"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    body = {"text": text}

    owns_client = False
    if client is None:
        client = httpx.Client(timeout=30.0)
        owns_client = True

    try:
        resp = client.post(
            f"{_BASE}/tweets", json=body, headers=headers
        )
    finally:
        if owns_client:
            client.close()

    if resp.status_code in (401, 403):
        raise XAuthError(
            f"POST /tweets {resp.status_code}: {resp.text[:200]}"
        )
    if resp.status_code != 201:
        raise XPublishError(
            f"POST /tweets {resp.status_code}: {resp.text[:200]}"
        )

    data = resp.json().get("data") or {}
    tweet_id = str(data.get("id") or "")
    return PublishResult(
        provider="x",
        remote_id=tweet_id,
        permalink=(
            f"https://x.com/{handle}/status/{tweet_id}" if tweet_id else None
        ),
        raw=resp.json(),
    )


__all__ = ["publish_to_x", "XAuthError", "XPublishError"]
