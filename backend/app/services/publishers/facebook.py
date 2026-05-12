"""Facebook Pages publisher — Phase 5.x.

Posts to a Facebook Page wall via the Graph API:

    POST https://graph.facebook.com/v18.0/{page_id}/feed
    Body: message=<text>&access_token=<page_access_token>

The token must be a **Page access token**, not a user token — Page
tokens have the ``pages_manage_posts`` scope and never expire (until
the user revokes them). Stored on
``SocialAccount.access_token``; page id on
``auth_metadata_json["page_id"]``.

Long copy is allowed (no per-post hard limit on Facebook), but we cap
defensively at 63206 chars (Facebook's documented max) to avoid a
silent truncation that would corrupt links.
"""

from __future__ import annotations

import hashlib

import httpx

from app.services.publishers import PublishResult


_FB_GRAPH_VERSION = "v18.0"
_MESSAGE_MAX = 63206


class FacebookAuthError(RuntimeError):
    pass


class FacebookPublishError(RuntimeError):
    pass


def _stub_result(page_id: str, text: str) -> PublishResult:
    digest = hashlib.sha256(
        (page_id + "::" + text[:512]).encode("utf-8")
    ).hexdigest()[:18]
    return PublishResult(
        provider="facebook",
        remote_id=f"stub-{digest}",
        permalink=None,
        raw={"stub": True, "page_id": page_id, "text": text},
    )


def publish_to_facebook(
    *,
    access_token: str | None,
    page_id: str | None,
    text: str,
    client: httpx.Client | None = None,
) -> PublishResult:
    """Posts a status to a Facebook Page.

    Args:
        access_token: Page access token. Empty/None → stub.
        page_id: Numeric Facebook Page id. Required for real posts;
            stub mode tolerates None.
        text: Status text. Capped to 63206 chars (Graph API documented
            maximum); longer copy is truncated with an ellipsis.
        client: Optional caller-managed httpx.Client (tests use
            MockTransport).

    Raises:
        FacebookAuthError: 401/403 — token bad / expired / scope wrong.
        FacebookPublishError: any other non-200.
    """
    pid = (page_id or "").strip() or "stub_page"
    if not access_token:
        return _stub_result(pid, text)

    if len(text) > _MESSAGE_MAX:
        text = text[: _MESSAGE_MAX - 1] + "…"

    url = f"https://graph.facebook.com/{_FB_GRAPH_VERSION}/{pid}/feed"
    body = {"message": text, "access_token": access_token}

    owns_client = False
    if client is None:
        client = httpx.Client(timeout=30.0)
        owns_client = True

    try:
        resp = client.post(url, data=body)
    finally:
        if owns_client:
            client.close()

    if resp.status_code in (401, 403):
        raise FacebookAuthError(
            f"POST /feed {resp.status_code}: {resp.text[:200]}"
        )
    if resp.status_code != 200:
        raise FacebookPublishError(
            f"POST /feed {resp.status_code}: {resp.text[:200]}"
        )

    data = resp.json() or {}
    remote_id = str(data.get("id") or "")
    # Graph returns "{page_id}_{post_id}" — the canonical permalink is
    # facebook.com/{post_id}.
    permalink: str | None = None
    if "_" in remote_id:
        post_part = remote_id.split("_", 1)[1]
        permalink = f"https://www.facebook.com/{pid}/posts/{post_part}"
    return PublishResult(
        provider="facebook",
        remote_id=remote_id,
        permalink=permalink,
        raw={"id": remote_id, "page_id": pid},
    )


__all__ = ["publish_to_facebook", "FacebookAuthError", "FacebookPublishError"]
