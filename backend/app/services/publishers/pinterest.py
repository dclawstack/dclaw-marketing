"""Pinterest publisher — Phase 5.7.

Posts an image Pin to a board via the v5 Pinterest API:

  POST https://api.pinterest.com/v5/pins
  Authorization: Bearer <access_token>
  body: {
    "board_id": "...",
    "title": "...",
    "alt_text": "...",
    "media_source": {
      "source_type": "image_url",
      "url": "https://..."
    }
  }

Image is required (no text-only Pins). board_id comes from
``SocialAccount.auth_metadata_json["board_id"]``.

Pinterest title cap 100 chars, description 500. Both truncate.
"""

from __future__ import annotations

import hashlib

import httpx

from app.services.publishers import PublishResult


_BASE = "https://api.pinterest.com/v5"
_TITLE_LIMIT = 100
_DESC_LIMIT = 500


class PinterestAuthError(RuntimeError):
    pass


class PinterestPublishError(RuntimeError):
    pass


class PinterestMissingMediaError(PinterestPublishError):
    """Pinterest pins require an image_url."""


def _stub_result(board_id: str, title: str, image_url: str | None) -> PublishResult:
    digest = hashlib.sha256(
        (board_id + "::" + title[:200] + "::" + (image_url or "")).encode("utf-8")
    ).hexdigest()[:18]
    return PublishResult(
        provider="pinterest",
        remote_id=f"stub-{digest}",
        permalink=None,
        raw={"stub": True, "board_id": board_id, "title": title, "image_url": image_url},
    )


def publish_to_pinterest(
    *,
    access_token: str | None,
    board_id: str,
    image_url: str | None,
    title: str,
    description: str = "",
    client: httpx.Client | None = None,
) -> PublishResult:
    """Posts a single image Pin to a Pinterest board.

    Raises:
        PinterestAuthError: 401/403 from the API.
        PinterestMissingMediaError: image_url required but missing.
        PinterestPublishError: any other non-201.
    """
    if not access_token:
        return _stub_result(board_id, title, image_url)
    if not image_url:
        raise PinterestMissingMediaError(
            "Pinterest pins require image_url — no text-only pins."
        )

    if len(title) > _TITLE_LIMIT:
        title = title[: _TITLE_LIMIT - 1] + "…"
    if len(description) > _DESC_LIMIT:
        description = description[: _DESC_LIMIT - 1] + "…"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    body = {
        "board_id": board_id,
        "title": title,
        "description": description,
        "alt_text": title,
        "media_source": {"source_type": "image_url", "url": image_url},
    }

    owns_client = False
    if client is None:
        client = httpx.Client(timeout=30.0)
        owns_client = True

    try:
        resp = client.post(f"{_BASE}/pins", json=body, headers=headers)
    finally:
        if owns_client:
            client.close()

    if resp.status_code in (401, 403):
        raise PinterestAuthError(
            f"pin {resp.status_code}: {resp.text[:200]}"
        )
    if resp.status_code != 201:
        raise PinterestPublishError(
            f"pin {resp.status_code}: {resp.text[:200]}"
        )

    data = resp.json() or {}
    pin_id = str(data.get("id", ""))
    permalink = (
        f"https://pinterest.com/pin/{pin_id}/" if pin_id else None
    )
    return PublishResult(
        provider="pinterest",
        remote_id=pin_id,
        permalink=permalink,
        raw=data,
    )


__all__ = [
    "publish_to_pinterest",
    "PinterestAuthError",
    "PinterestPublishError",
    "PinterestMissingMediaError",
]
