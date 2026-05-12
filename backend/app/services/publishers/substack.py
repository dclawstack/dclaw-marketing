"""Substack publisher — Phase 5.x.

Substack has no documented public posting API; the official surface is
the editor UI plus an email/RSS firehose for subscribers. We expose two
real modes plus the standard stub fallback:

  • **Draft mode** (default when ``api_key`` is set): POST a draft via
    the unofficial endpoint
    ``https://{publication}.substack.com/api/v1/drafts``. The publication
    owner can finalise/publish from the Substack UI. Most reliable mode
    short of the user manually pasting copy.
  • **Stub mode** (no api_key): deterministic synthetic id, no network
    call. Used in dev / sandbox / when the user hasn't connected.

Field map on ``SocialAccount.auth_metadata_json``:

  • ``publication``  — required, the Substack publication subdomain
    (e.g. ``"acmenews"`` for ``acmenews.substack.com``).
  • ``api_key``      — Substack session cookie value or admin token
    (the unofficial endpoint uses the same auth as the dashboard).

Because the endpoint is undocumented and Substack can change it without
notice, transport failures are caught and surfaced as
``SubstackPublishError``; the dispatcher in ``publishing.py`` will mark
the scheduled post as failed but not block the rest of the queue.
"""

from __future__ import annotations

import hashlib

import httpx

from app.services.publishers import PublishResult


_TITLE_MAX = 280


class SubstackAuthError(RuntimeError):
    pass


class SubstackPublishError(RuntimeError):
    pass


def _stub_result(publication: str, text: str) -> PublishResult:
    digest = hashlib.sha256(
        (publication + "::" + text[:512]).encode("utf-8")
    ).hexdigest()[:18]
    return PublishResult(
        provider="substack",
        remote_id=f"stub-{digest}",
        permalink=None,
        raw={"stub": True, "publication": publication, "text": text},
    )


def _split_title_body(text: str) -> tuple[str, str]:
    """First non-empty line becomes the post title, the rest is body.

    Substack posts have a separate title — without one the editor renders
    "Untitled". We take the first line and cap it to 280 chars.
    """
    lines = (text or "").splitlines()
    title = ""
    rest_start = 0
    for i, line in enumerate(lines):
        if line.strip():
            title = line.strip()[:_TITLE_MAX]
            rest_start = i + 1
            break
    body = "\n".join(lines[rest_start:]).strip()
    if not title:
        title = "Untitled"
    return title, body


def publish_to_substack(
    *,
    api_key: str | None,
    publication: str | None,
    text: str,
    client: httpx.Client | None = None,
) -> PublishResult:
    """Creates a Substack draft (or returns a stub when uncredentialed).

    Args:
        api_key: Substack admin session/api token. Empty/None → stub.
        publication: Substack publication subdomain. Required when posting
            for real; stub mode tolerates None and substitutes
            ``"stub-publication"``.
        text: Markdown copy. First non-empty line becomes the draft title,
            the remainder becomes the body.
        client: Optional caller-managed httpx.Client (tests inject
            ``MockTransport``).

    Raises:
        SubstackAuthError: 401/403 — session cookie expired or scope wrong.
        SubstackPublishError: any other non-2xx response.
    """
    pub_slug = (publication or "").strip().lower() or "stub-publication"
    if not api_key:
        return _stub_result(pub_slug, text)

    title, body = _split_title_body(text)
    payload = {
        "title": title,
        "subtitle": "",
        "body": body,
        "type": "newsletter",
        "audience": "everyone",
    }
    headers = {
        "Cookie": f"substack.sid={api_key}",
        "Content-Type": "application/json",
        "User-Agent": "DClawMarketing/1.2 (publishers)",
    }
    url = f"https://{pub_slug}.substack.com/api/v1/drafts"

    owns_client = False
    if client is None:
        client = httpx.Client(timeout=30.0)
        owns_client = True

    try:
        resp = client.post(url, json=payload, headers=headers)
    finally:
        if owns_client:
            client.close()

    if resp.status_code in (401, 403):
        raise SubstackAuthError(
            f"POST drafts {resp.status_code}: {resp.text[:200]}"
        )
    if resp.status_code >= 400:
        raise SubstackPublishError(
            f"POST drafts {resp.status_code}: {resp.text[:200]}"
        )

    data: dict
    try:
        data = resp.json() or {}
    except Exception:  # pragma: no cover — Substack occasionally returns text
        data = {}
    remote_id = str(data.get("id") or data.get("draft_id") or "")
    edit_url: str | None = None
    if remote_id:
        edit_url = f"https://{pub_slug}.substack.com/publish/post/{remote_id}"
    return PublishResult(
        provider="substack",
        remote_id=remote_id,
        permalink=edit_url,
        raw={
            "id": data.get("id"),
            "draft_id": data.get("draft_id"),
            "publication": pub_slug,
            "title": title,
        },
    )


__all__ = ["publish_to_substack", "SubstackAuthError", "SubstackPublishError"]
