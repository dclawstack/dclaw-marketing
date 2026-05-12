"""Bluesky (atproto) publisher — Phase 5.1.

Two-step flow:
1. ``com.atproto.server.createSession`` — exchange the user's handle
   + app password for an access JWT + DID.
2. ``com.atproto.repo.createRecord`` — write a ``app.bsky.feed.post``
   record under the user's repo.

App-password auth lets us skip the full OAuth dance (which Bluesky
doesn't fully support yet anyway). Users issue an app password from
their Bluesky settings and paste it into the Channels page.

When BSKY credentials are missing we return a deterministic stub so
the rest of the pipeline (ScheduledPost status update, audit log)
continues to work in dev / CI.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import httpx

from app.services.publishers import PublishResult


_BSKY_BASE = "https://bsky.social"


class BlueskyAuthError(RuntimeError):
    pass


class BlueskyPublishError(RuntimeError):
    pass


def _stub_result(handle: str, text: str) -> PublishResult:
    """Used when no credentials are present — same shape as the real
    response, so callers can't tell the difference at runtime.
    """
    digest = hashlib.sha256(
        (handle + "::" + text[:512]).encode("utf-8")
    ).hexdigest()[:24]
    return PublishResult(
        provider="bluesky",
        remote_id=f"at://stub/{handle}/app.bsky.feed.post/{digest}",
        permalink=None,
        raw={"stub": True, "handle": handle, "text": text},
    )


def publish_to_bluesky(
    *,
    handle: str,
    app_password: str | None,
    text: str,
    client: httpx.Client | None = None,
) -> PublishResult:
    """Publishes a single text post.

    Args:
        handle: The user's @handle (e.g. "alice.bsky.social"). Used as
            the identifier in ``createSession``.
        app_password: App password issued via Bluesky settings. If
            empty/None, returns the stub result.
        text: Post body. The platform limits to 300 graphemes; longer
            text is truncated with an ellipsis.
        client: Optional ``httpx.Client`` for tests — caller-supplied
            clients are NOT closed by this function.

    Raises:
        BlueskyAuthError: createSession failed (bad creds).
        BlueskyPublishError: createRecord failed.
    """
    if not app_password:
        return _stub_result(handle, text)

    # Bluesky limit is 300 graphemes; treat chars as a safe upper bound.
    if len(text) > 300:
        text = text[:299] + "…"

    owns_client = False
    if client is None:
        client = httpx.Client(timeout=30.0)
        owns_client = True

    try:
        session_resp = client.post(
            f"{_BSKY_BASE}/xrpc/com.atproto.server.createSession",
            json={"identifier": handle, "password": app_password},
            headers={"Content-Type": "application/json"},
        )
        if session_resp.status_code != 200:
            raise BlueskyAuthError(
                f"createSession {session_resp.status_code}: "
                f"{session_resp.text[:200]}"
            )
        session = session_resp.json()
        access_jwt = session.get("accessJwt")
        did = session.get("did")
        if not access_jwt or not did:
            raise BlueskyAuthError("createSession response missing accessJwt/did")

        record = {
            "$type": "app.bsky.feed.post",
            "text": text,
            "createdAt": datetime.now(tz=timezone.utc).isoformat().replace(
                "+00:00", "Z"
            ),
            "langs": ["en"],
        }
        post_resp = client.post(
            f"{_BSKY_BASE}/xrpc/com.atproto.repo.createRecord",
            json={
                "repo": did,
                "collection": "app.bsky.feed.post",
                "record": record,
            },
            headers={
                "Authorization": f"Bearer {access_jwt}",
                "Content-Type": "application/json",
            },
        )
        if post_resp.status_code != 200:
            raise BlueskyPublishError(
                f"createRecord {post_resp.status_code}: "
                f"{post_resp.text[:200]}"
            )

        data = post_resp.json()
        uri = str(data.get("uri", ""))
        permalink = _uri_to_permalink(uri, handle)
        return PublishResult(
            provider="bluesky",
            remote_id=uri,
            permalink=permalink,
            raw=data,
        )
    finally:
        if owns_client:
            client.close()


def _uri_to_permalink(uri: str, handle: str) -> str | None:
    """``at://did:plc:xxx/app.bsky.feed.post/<rkey>`` →
    ``https://bsky.app/profile/<handle>/post/<rkey>``.
    """
    if not uri.startswith("at://"):
        return None
    rkey = uri.rsplit("/", 1)[-1]
    if not rkey:
        return None
    return f"https://bsky.app/profile/{handle}/post/{rkey}"


__all__ = [
    "publish_to_bluesky",
    "BlueskyAuthError",
    "BlueskyPublishError",
]
