"""YouTube Data API v3 publisher — Phase 5.x.

YouTube uploads do not accept URL-pull (unlike TikTok/Instagram). The
binary has to be streamed to ``upload.googleapis.com`` directly. To
keep the adapter testable + side-effect-free we expose two ways to
supply the video bytes:

  • ``video_data`` — raw bytes (used by tests + callers that already
    have the bytes in hand).
  • ``video_url`` — the adapter fetches the bytes itself via the same
    httpx.Client. The video is buffered in memory; for short-form
    content (<200 MB) that's the simplest and safe in our worker.

We use the *multipart* upload endpoint, not resumable — multipart is
single-request and dramatically simpler. YouTube allows multipart for
files up to 256 GiB.

Endpoint:
    POST https://www.googleapis.com/upload/youtube/v3/videos
         ?uploadType=multipart&part=snippet,status
    Authorization: Bearer <oauth2>
    Body: multipart/related with one JSON part + one binary part
"""

from __future__ import annotations

import hashlib
import json
import secrets

import httpx

from app.services.publishers import PublishResult


_API_BASE = "https://www.googleapis.com"
_UPLOAD_PATH = "/upload/youtube/v3/videos"


class YouTubeAuthError(RuntimeError):
    pass


class YouTubePublishError(RuntimeError):
    pass


class YouTubeMissingMediaError(YouTubePublishError):
    """Raised when a real publish is attempted without video bytes/URL."""


def _stub_result(title: str) -> PublishResult:
    digest = hashlib.sha256(title[:512].encode("utf-8")).hexdigest()[:18]
    return PublishResult(
        provider="youtube",
        remote_id=f"stub-{digest}",
        permalink=None,
        raw={"stub": True, "title": title},
    )


def _build_multipart(snippet: dict, status: dict, video_bytes: bytes) -> tuple[str, bytes]:
    """Construct a ``multipart/related`` body for the YouTube upload.

    Returns (content_type, body_bytes).
    """
    boundary = "DCLAW-YT-" + secrets.token_hex(12)
    metadata = json.dumps({"snippet": snippet, "status": status}).encode("utf-8")
    crlf = b"\r\n"
    body = (
        b"--" + boundary.encode() + crlf
        + b"Content-Type: application/json; charset=UTF-8" + crlf + crlf
        + metadata + crlf
        + b"--" + boundary.encode() + crlf
        + b"Content-Type: video/*" + crlf + crlf
        + video_bytes + crlf
        + b"--" + boundary.encode() + b"--" + crlf
    )
    return f"multipart/related; boundary={boundary}", body


def publish_to_youtube(
    *,
    access_token: str | None,
    title: str,
    description: str = "",
    tags: list[str] | None = None,
    privacy_status: str = "private",
    category_id: str = "22",  # "People & Blogs" — safe default
    video_data: bytes | None = None,
    video_url: str | None = None,
    client: httpx.Client | None = None,
) -> PublishResult:
    """Uploads a video to YouTube via the multipart endpoint.

    Args:
        access_token: OAuth 2.0 access token with ``youtube.upload``
            scope. Empty/None → stub.
        title: Video title (capped 100 chars by YouTube).
        description: Long-form description (5000 char cap server-side).
        tags: Free-form tag list.
        privacy_status: ``private`` | ``public`` | ``unlisted``.
            Default ``private`` to avoid accidental public uploads.
        category_id: YouTube category id string.
        video_data: Raw bytes of the video. Mutually-exclusive with
            ``video_url``; if both supplied, ``video_data`` wins.
        video_url: HTTP(S) URL the adapter will GET to fetch the
            bytes. Used when the worker doesn't already have them.
        client: Optional caller-managed httpx.Client.

    Raises:
        YouTubeAuthError: 401/403 on upload step.
        YouTubeMissingMediaError: real publish without bytes or URL.
        YouTubePublishError: any other non-200.
    """
    if not access_token:
        return _stub_result(title)
    if video_data is None and not video_url:
        raise YouTubeMissingMediaError(
            "YouTube publish requires video_data or video_url."
        )

    owns_client = False
    if client is None:
        client = httpx.Client(timeout=60.0)
        owns_client = True

    try:
        if video_data is None:
            fetch_resp = client.get(video_url)  # type: ignore[arg-type]
            if fetch_resp.status_code != 200:
                raise YouTubePublishError(
                    f"GET video_url {fetch_resp.status_code}: "
                    f"{fetch_resp.text[:200]}"
                )
            video_data = fetch_resp.content

        snippet = {
            "title": (title or "")[:100],
            "description": description,
            "tags": tags or [],
            "categoryId": category_id,
        }
        status_part = {"privacyStatus": privacy_status, "selfDeclaredMadeForKids": False}
        content_type, body = _build_multipart(snippet, status_part, video_data)
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": content_type,
        }
        upload_resp = client.post(
            f"{_API_BASE}{_UPLOAD_PATH}"
            "?uploadType=multipart&part=snippet,status",
            content=body,
            headers=headers,
        )
    finally:
        if owns_client:
            client.close()

    if upload_resp.status_code in (401, 403):
        raise YouTubeAuthError(
            f"POST videos {upload_resp.status_code}: {upload_resp.text[:200]}"
        )
    if upload_resp.status_code != 200:
        raise YouTubePublishError(
            f"POST videos {upload_resp.status_code}: {upload_resp.text[:200]}"
        )

    data = upload_resp.json() or {}
    video_id = str(data.get("id") or "")
    permalink = (
        f"https://www.youtube.com/watch?v={video_id}" if video_id else None
    )
    return PublishResult(
        provider="youtube",
        remote_id=video_id,
        permalink=permalink,
        raw={"id": video_id, "snippet": data.get("snippet")},
    )


__all__ = [
    "publish_to_youtube",
    "YouTubeAuthError",
    "YouTubePublishError",
    "YouTubeMissingMediaError",
]
