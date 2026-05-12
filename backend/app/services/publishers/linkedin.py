"""LinkedIn UGC post publisher — Phase 5.2.

Posts to LinkedIn via the v2 UGC API:

    POST https://api.linkedin.com/v2/ugcPosts
    Authorization: Bearer <access_token>

The author URN (``urn:li:person:<member_id>`` for personal accounts
or ``urn:li:organization:<org_id>`` for Company Pages) must be
stored in ``SocialAccount.auth_metadata_json["author_urn"]`` at OAuth
connect time.

LinkedIn limits posts to ~3000 chars (Plain text + URL share), so
longer copy is truncated with an ellipsis. Same stub-fallback shape
as the Bluesky publisher — no token → deterministic synthetic id.
"""

from __future__ import annotations

import hashlib

import httpx

from app.services.publishers import PublishResult


_BASE = "https://api.linkedin.com/v2"
_LIMIT_CHARS = 3000


class LinkedInAuthError(RuntimeError):
    pass


class LinkedInPublishError(RuntimeError):
    pass


def _stub_result(author_urn: str, text: str) -> PublishResult:
    digest = hashlib.sha256(
        (author_urn + "::" + text[:512]).encode("utf-8")
    ).hexdigest()[:24]
    return PublishResult(
        provider="linkedin",
        remote_id=f"urn:li:share:stub-{digest}",
        permalink=None,
        raw={"stub": True, "author_urn": author_urn, "text": text},
    )


def publish_to_linkedin(
    *,
    access_token: str | None,
    author_urn: str,
    text: str,
    client: httpx.Client | None = None,
) -> PublishResult:
    """Publishes a single text UGC post.

    Args:
        access_token: OAuth bearer token from the connected
            SocialAccount. Empty / None → returns the stub result.
        author_urn: ``urn:li:person:<id>`` or ``urn:li:organization:<id>``
            — taken from auth_metadata_json["author_urn"].
        text: Post body. Truncated to 3000 chars with an ellipsis if
            longer.
        client: Optional caller-managed httpx.Client (kept open by the
            caller) — used by tests with MockTransport.

    Raises:
        LinkedInAuthError: API returned 401/403 — token bad/expired.
        LinkedInPublishError: API returned any other non-201.
    """
    if not access_token:
        return _stub_result(author_urn, text)

    if len(text) > _LIMIT_CHARS:
        text = text[: _LIMIT_CHARS - 1] + "…"

    body = {
        "author": author_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
        },
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    owns_client = False
    if client is None:
        client = httpx.Client(timeout=30.0)
        owns_client = True

    try:
        resp = client.post(
            f"{_BASE}/ugcPosts", json=body, headers=headers
        )
    finally:
        if owns_client:
            client.close()

    if resp.status_code in (401, 403):
        raise LinkedInAuthError(
            f"ugcPosts {resp.status_code}: {resp.text[:200]}"
        )
    if resp.status_code != 201:
        raise LinkedInPublishError(
            f"ugcPosts {resp.status_code}: {resp.text[:200]}"
        )

    # LinkedIn returns the share urn in either the body OR the
    # x-restli-id header — prefer the header (canonical).
    remote_id = resp.headers.get("x-restli-id") or (
        resp.json().get("id") if resp.headers.get("content-type", "").startswith(
            "application/json"
        ) else ""
    )
    return PublishResult(
        provider="linkedin",
        remote_id=remote_id or "",
        permalink=_urn_to_permalink(remote_id) if remote_id else None,
        raw={"id": remote_id, "status_code": resp.status_code},
    )


def _urn_to_permalink(urn: str) -> str | None:
    """``urn:li:share:7012345678901234567`` →
    ``https://www.linkedin.com/feed/update/urn:li:share:7012345678901234567/``.
    """
    if not urn.startswith("urn:li:"):
        return None
    return f"https://www.linkedin.com/feed/update/{urn}/"


__all__ = [
    "publish_to_linkedin",
    "LinkedInAuthError",
    "LinkedInPublishError",
]
