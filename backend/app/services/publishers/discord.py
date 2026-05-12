"""Discord webhook publisher — Phase 5.7.

Sends a message to a Discord channel via the channel's webhook URL.
No OAuth — the webhook URL itself is the secret.

  POST {webhook_url}
  body: {"content": "<text>"}
  → 204 No Content

The webhook URL is stored on
``SocialAccount.auth_metadata_json["webhook_url"]``. Discord limits
message content to 2000 chars; longer copy is truncated with an
ellipsis.

Stub fallback when the webhook URL is missing.
"""

from __future__ import annotations

import hashlib

import httpx

from app.services.publishers import PublishResult


_LIMIT_CHARS = 2000


class DiscordPublishError(RuntimeError):
    pass


def _stub_result(text: str) -> PublishResult:
    digest = hashlib.sha256(text[:512].encode("utf-8")).hexdigest()[:18]
    return PublishResult(
        provider="discord",
        remote_id=f"stub-{digest}",
        permalink=None,
        raw={"stub": True, "text": text},
    )


def publish_to_discord(
    *,
    webhook_url: str | None,
    text: str,
    username: str | None = None,
    client: httpx.Client | None = None,
) -> PublishResult:
    """Posts a single message to a Discord channel webhook.

    Args:
        webhook_url: The full Discord webhook URL. Empty/None → stub.
        text: Message body. Truncated to 2000 chars.
        username: Optional override of the webhook's display name.
        client: Optional caller-managed httpx.Client (tests).
    """
    if not webhook_url:
        return _stub_result(text)

    if len(text) > _LIMIT_CHARS:
        text = text[: _LIMIT_CHARS - 1] + "…"

    body: dict = {"content": text}
    if username:
        body["username"] = username

    owns_client = False
    if client is None:
        client = httpx.Client(timeout=30.0)
        owns_client = True

    try:
        # ?wait=true makes Discord return the created message in the
        # response body — gives us a message id we can store.
        resp = client.post(
            webhook_url,
            params={"wait": "true"},
            json=body,
        )
    finally:
        if owns_client:
            client.close()

    if resp.status_code not in (200, 204):
        raise DiscordPublishError(
            f"webhook {resp.status_code}: {resp.text[:200]}"
        )

    if resp.status_code == 200 and resp.content:
        data = resp.json() or {}
        msg_id = str(data.get("id", ""))
    else:
        msg_id = ""

    return PublishResult(
        provider="discord",
        remote_id=msg_id,
        permalink=None,  # Discord webhook messages have no public URL
        raw={"id": msg_id},
    )


__all__ = ["publish_to_discord", "DiscordPublishError"]
