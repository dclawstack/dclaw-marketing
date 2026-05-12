"""TikTok Business publisher — Phase 5.x.

TikTok's Content Posting API supports a **pull-from-URL** mode where
the platform fetches the video from a publicly-accessible URL on our
side. We rely on that mode exclusively — we never stream raw bytes
through the worker process, which keeps the publisher small and
side-effect-free.

Flow:

  POST https://open.tiktokapis.com/v2/post/publish/inbox/video/init/
       Authorization: Bearer <user_access_token>
       Content-Type: application/json
       {
         "source_info": {
           "source": "PULL_FROM_URL",
           "video_url": "<asset_url>"
         },
         "post_info": {
           "title": "<caption[:150]>",
           "privacy_level": "<...>",
           ...
         }
       }
  → {"data": {"publish_id": "<id>"}}

The video then transitions through TikTok's review states asynchronously.
We treat ``publish_id`` as the remote id; the permalink is unknowable
until TikTok publishes and assigns a video id, which can take minutes.

Field map on SocialAccount.auth_metadata_json:

  • ``privacy_level`` — default ``"SELF_ONLY"`` (the safest dev value).
  • ``disable_comment``, ``disable_duet``, ``disable_stitch`` — booleans.

The actual video URL is read from ``ScheduledPost.publisher_response.video_url``
the same way Instagram/Pinterest read image_url today.
"""

from __future__ import annotations

import hashlib

import httpx

from app.services.publishers import PublishResult


_API_BASE = "https://open.tiktokapis.com/v2"
_CAPTION_MAX = 150


class TikTokAuthError(RuntimeError):
    pass


class TikTokPublishError(RuntimeError):
    pass


class TikTokMissingMediaError(TikTokPublishError):
    """Raised when a real publish is attempted without a video_url."""


def _stub_result(text: str) -> PublishResult:
    digest = hashlib.sha256(text[:512].encode("utf-8")).hexdigest()[:18]
    return PublishResult(
        provider="tiktok",
        remote_id=f"stub-{digest}",
        permalink=None,
        raw={"stub": True, "text": text},
    )


def publish_to_tiktok(
    *,
    access_token: str | None,
    video_url: str | None,
    caption: str,
    privacy_level: str = "SELF_ONLY",
    disable_comment: bool = False,
    disable_duet: bool = False,
    disable_stitch: bool = False,
    client: httpx.Client | None = None,
) -> PublishResult:
    """Initiates a TikTok video publish via PULL_FROM_URL.

    Args:
        access_token: User access token (scope: ``video.publish``).
            Empty/None → stub.
        video_url: Publicly-accessible URL of the video file. Required
            for real publishes; the absence raises ``TikTokMissingMediaError``.
        caption: Post caption. Capped to 150 chars.
        privacy_level: TikTok privacy level (``PUBLIC_TO_EVERYONE`` |
            ``MUTUAL_FOLLOW_FRIENDS`` | ``SELF_ONLY``, etc.). Default
            ``SELF_ONLY`` to avoid accidental public posts in dev.
        disable_comment / _duet / _stitch: per-post toggles.
        client: Optional caller-managed httpx.Client.

    Raises:
        TikTokAuthError: 401/403 — token bad / expired / scope missing.
        TikTokMissingMediaError: real publish attempted without video_url.
        TikTokPublishError: any other non-200.
    """
    if not access_token:
        return _stub_result(caption)
    if not video_url:
        raise TikTokMissingMediaError(
            "TikTok publish requires a video_url (pull-from-URL mode)."
        )

    capped_caption = (caption or "")[:_CAPTION_MAX]
    body = {
        "source_info": {
            "source": "PULL_FROM_URL",
            "video_url": video_url,
        },
        "post_info": {
            "title": capped_caption,
            "privacy_level": privacy_level,
            "disable_comment": disable_comment,
            "disable_duet": disable_duet,
            "disable_stitch": disable_stitch,
        },
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    owns_client = False
    if client is None:
        client = httpx.Client(timeout=30.0)
        owns_client = True

    try:
        resp = client.post(
            f"{_API_BASE}/post/publish/inbox/video/init/",
            json=body,
            headers=headers,
        )
    finally:
        if owns_client:
            client.close()

    if resp.status_code in (401, 403):
        raise TikTokAuthError(
            f"POST inbox init {resp.status_code}: {resp.text[:200]}"
        )
    if resp.status_code != 200:
        raise TikTokPublishError(
            f"POST inbox init {resp.status_code}: {resp.text[:200]}"
        )

    data = (resp.json() or {}).get("data") or {}
    publish_id = str(data.get("publish_id") or "")
    return PublishResult(
        provider="tiktok",
        remote_id=publish_id,
        permalink=None,
        raw={"publish_id": publish_id, "data": data},
    )


__all__ = [
    "publish_to_tiktok",
    "TikTokAuthError",
    "TikTokPublishError",
    "TikTokMissingMediaError",
]
