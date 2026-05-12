"""Meta Threads publisher — Phase 5.x.

Two-step container/publish flow that mirrors the Instagram Graph API:

    POST https://graph.threads.net/v1.0/{threads_user_id}/threads
         media_type=TEXT  (or IMAGE / VIDEO)
         text=<text>
         access_token=<...>
    → {"id": "<container_id>"}

    POST https://graph.threads.net/v1.0/{threads_user_id}/threads_publish
         creation_id=<container_id>
         access_token=<...>
    → {"id": "<media_id>"}

Threads enforces a 500-char limit per post — longer copy is truncated
with an ellipsis. Stub fallback shape matches the other publishers.
"""

from __future__ import annotations

import hashlib

import httpx

from app.services.publishers import PublishResult


_THREADS_GRAPH = "https://graph.threads.net/v1.0"
_LIMIT_CHARS = 500


class ThreadsAuthError(RuntimeError):
    pass


class ThreadsPublishError(RuntimeError):
    pass


def _stub_result(user_id: str, text: str) -> PublishResult:
    digest = hashlib.sha256(
        (user_id + "::" + text[:512]).encode("utf-8")
    ).hexdigest()[:18]
    return PublishResult(
        provider="threads",
        remote_id=f"stub-{digest}",
        permalink=None,
        raw={"stub": True, "threads_user_id": user_id, "text": text},
    )


def publish_to_threads(
    *,
    access_token: str | None,
    threads_user_id: str | None,
    text: str,
    handle: str | None = None,
    client: httpx.Client | None = None,
) -> PublishResult:
    """Creates a Threads post via the two-step container/publish flow.

    Args:
        access_token: Threads user access token. Empty/None → stub.
        threads_user_id: Numeric Threads user id (different from the
            user's IG id). Required for real posts.
        text: Post body. Capped to 500 chars (with ellipsis).
        handle: Optional Threads @handle, used only to build the
            permalink.
        client: Optional caller-managed httpx.Client.

    Raises:
        ThreadsAuthError: 401/403 on either step.
        ThreadsPublishError: any other non-200.
    """
    uid = (threads_user_id or "").strip() or "stub_user"
    if not access_token:
        return _stub_result(uid, text)

    if len(text) > _LIMIT_CHARS:
        text = text[: _LIMIT_CHARS - 1] + "…"

    owns_client = False
    if client is None:
        client = httpx.Client(timeout=30.0)
        owns_client = True

    try:
        # 1. Create container.
        create_resp = client.post(
            f"{_THREADS_GRAPH}/{uid}/threads",
            data={
                "media_type": "TEXT",
                "text": text,
                "access_token": access_token,
            },
        )
        if create_resp.status_code in (401, 403):
            raise ThreadsAuthError(
                f"POST /threads {create_resp.status_code}: {create_resp.text[:200]}"
            )
        if create_resp.status_code != 200:
            raise ThreadsPublishError(
                f"POST /threads {create_resp.status_code}: {create_resp.text[:200]}"
            )
        container_id = (create_resp.json() or {}).get("id")
        if not container_id:
            raise ThreadsPublishError(
                "Container response missing id field"
            )

        # 2. Publish container.
        publish_resp = client.post(
            f"{_THREADS_GRAPH}/{uid}/threads_publish",
            data={
                "creation_id": container_id,
                "access_token": access_token,
            },
        )
    finally:
        if owns_client:
            client.close()

    if publish_resp.status_code in (401, 403):
        raise ThreadsAuthError(
            f"POST /threads_publish {publish_resp.status_code}: "
            f"{publish_resp.text[:200]}"
        )
    if publish_resp.status_code != 200:
        raise ThreadsPublishError(
            f"POST /threads_publish {publish_resp.status_code}: "
            f"{publish_resp.text[:200]}"
        )

    data = publish_resp.json() or {}
    media_id = str(data.get("id") or "")
    permalink: str | None = None
    if handle and media_id:
        permalink = f"https://www.threads.net/@{handle}/post/{media_id}"
    return PublishResult(
        provider="threads",
        remote_id=media_id,
        permalink=permalink,
        raw={"id": media_id, "container_id": container_id},
    )


__all__ = ["publish_to_threads", "ThreadsAuthError", "ThreadsPublishError"]
