"""Instagram Business publisher — Phase 5.4.

Posts an image + caption to a connected Instagram Business / Creator
account via the Graph API two-step flow:

  1. POST /{ig_user_id}/media         → create media container
  2. POST /{ig_user_id}/media_publish → publish it

The image must be hosted at a public URL — Instagram Business API
does NOT accept binary uploads. Callers (typically the publish
worker) resolve a hosted asset URL from the ScheduledPost's first
asset and pass it in.

Connection requirements (set at OAuth time):
- ``SocialAccount.access_token`` — long-lived user token
  with scopes ``instagram_basic``, ``instagram_content_publish``,
  ``pages_show_list``.
- ``SocialAccount.auth_metadata_json["ig_user_id"]`` — the connected
  IG Business Account id (NOT the Facebook user id).

Without those, falls back to a deterministic stub so the rest of
the pipeline still closes.
"""

from __future__ import annotations

import hashlib

import httpx

from app.services.publishers import PublishResult


_BASE = "https://graph.facebook.com/v19.0"
# Instagram caption hard cap is 2200 chars.
_LIMIT_CHARS = 2200


class InstagramAuthError(RuntimeError):
    pass


class InstagramPublishError(RuntimeError):
    pass


class InstagramMissingMediaError(InstagramPublishError):
    """Raised when no image_url is provided — Instagram requires media."""


def _stub_result(
    ig_user_id: str, caption: str, image_url: str | None
) -> PublishResult:
    digest = hashlib.sha256(
        (ig_user_id + "::" + caption[:512] + "::" + (image_url or "")).encode(
            "utf-8"
        )
    ).hexdigest()[:18]
    return PublishResult(
        provider="instagram",
        remote_id=f"stub-{digest}",
        permalink=None,
        raw={
            "stub": True,
            "ig_user_id": ig_user_id,
            "caption": caption,
            "image_url": image_url,
        },
    )


def publish_to_instagram(
    *,
    access_token: str | None,
    ig_user_id: str,
    image_url: str | None,
    caption: str,
    handle: str | None = None,
    client: httpx.Client | None = None,
) -> PublishResult:
    """Posts an image + caption to Instagram.

    Args:
        access_token: Long-lived user token. None/empty → stub.
        ig_user_id: Connected IG Business Account id.
        image_url: Public HTTPS URL to the image asset. Required for
            real posts; if None and a token IS present, raises
            InstagramMissingMediaError. With no token, returns stub.
        caption: Post caption. Truncated to 2200 chars with ellipsis.
        handle: Optional handle for the permalink display. The Graph
            API also returns a permalink directly when we re-fetch.
        client: Optional caller-managed httpx.Client (tests).

    Raises:
        InstagramAuthError: 401/403 from the Graph API.
        InstagramMissingMediaError: image_url required but missing.
        InstagramPublishError: any other non-200.
    """
    if not access_token:
        return _stub_result(ig_user_id, caption, image_url)

    if not image_url:
        raise InstagramMissingMediaError(
            "Instagram requires image_url — Business API does not "
            "accept text-only posts. Attach an asset to the "
            "ScheduledPost first."
        )

    if len(caption) > _LIMIT_CHARS:
        caption = caption[: _LIMIT_CHARS - 1] + "…"

    params_common = {"access_token": access_token}

    owns_client = False
    if client is None:
        client = httpx.Client(timeout=60.0)
        owns_client = True

    try:
        # Step 1 — create media container
        create = client.post(
            f"{_BASE}/{ig_user_id}/media",
            params={
                **params_common,
                "image_url": image_url,
                "caption": caption,
            },
        )
        if create.status_code in (401, 403):
            raise InstagramAuthError(
                f"media create {create.status_code}: {create.text[:200]}"
            )
        if create.status_code != 200:
            raise InstagramPublishError(
                f"media create {create.status_code}: {create.text[:200]}"
            )
        creation_id = (create.json() or {}).get("id")
        if not creation_id:
            raise InstagramPublishError(
                f"media create response missing 'id': {create.text[:200]}"
            )

        # Step 2 — publish
        publish = client.post(
            f"{_BASE}/{ig_user_id}/media_publish",
            params={**params_common, "creation_id": creation_id},
        )
        if publish.status_code in (401, 403):
            raise InstagramAuthError(
                f"media_publish {publish.status_code}: {publish.text[:200]}"
            )
        if publish.status_code != 200:
            raise InstagramPublishError(
                f"media_publish {publish.status_code}: {publish.text[:200]}"
            )
        published_id = (publish.json() or {}).get("id") or ""
    finally:
        if owns_client:
            client.close()

    permalink = (
        f"https://www.instagram.com/p/{published_id}/"
        if published_id
        else None
    )
    return PublishResult(
        provider="instagram",
        remote_id=str(published_id),
        permalink=permalink,
        raw={
            "creation_id": creation_id,
            "media_id": published_id,
        },
    )


__all__ = [
    "publish_to_instagram",
    "InstagramAuthError",
    "InstagramPublishError",
    "InstagramMissingMediaError",
]
