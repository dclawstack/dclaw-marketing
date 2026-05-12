"""Reddit publisher — Phase 5.6.

Posts a self-text submission to a subreddit via the OAuth API:

    POST https://oauth.reddit.com/api/submit
    Authorization: Bearer <access_token>
    User-Agent: <required>

Subreddit comes from ``SocialAccount.auth_metadata_json["subreddit"]``;
title comes from the first line of the post copy (or the explicit
``title=`` kwarg). Body is the rest.

Reddit titles are capped at 300 chars; self-text at 40,000. Both
truncate gracefully.
"""

from __future__ import annotations

import hashlib

import httpx

from app.services.publishers import PublishResult


_BASE = "https://oauth.reddit.com"
_TITLE_LIMIT = 300
_BODY_LIMIT = 40000


class RedditAuthError(RuntimeError):
    pass


class RedditPublishError(RuntimeError):
    pass


def _stub_result(subreddit: str, title: str) -> PublishResult:
    digest = hashlib.sha256(
        (subreddit + "::" + title[:512]).encode("utf-8")
    ).hexdigest()[:18]
    return PublishResult(
        provider="reddit",
        remote_id=f"stub-{digest}",
        permalink=None,
        raw={"stub": True, "subreddit": subreddit, "title": title},
    )


def _split_title_body(text: str, explicit_title: str | None) -> tuple[str, str]:
    """If caller supplied an explicit title, use it. Otherwise take
    the first line of text as title and the rest as body.
    """
    if explicit_title:
        return explicit_title.strip(), text.strip()
    lines = text.strip().split("\n", 1)
    title = lines[0].strip()
    body = lines[1].strip() if len(lines) > 1 else ""
    return title, body


def publish_to_reddit(
    *,
    access_token: str | None,
    subreddit: str,
    text: str,
    title: str | None = None,
    user_agent: str = "DClawMarketing/1.0 (+https://dclaw.io)",
    client: httpx.Client | None = None,
) -> PublishResult:
    """Posts a single self-text submission.

    Args:
        access_token: OAuth bearer token. None/empty → stub.
        subreddit: Name of the subreddit (no "r/" prefix).
        text: Combined title + body, or just body if ``title`` supplied.
        title: Explicit title override. If absent, first line of text
            is treated as title.
        user_agent: Required by Reddit's API ToS.
        client: Optional caller-managed httpx.Client (tests).
    """
    if not access_token:
        return _stub_result(subreddit, title or text[:_TITLE_LIMIT])

    title_str, body_str = _split_title_body(text, title)
    if not title_str:
        raise RedditPublishError("Reddit submission requires a non-empty title")

    if len(title_str) > _TITLE_LIMIT:
        title_str = title_str[: _TITLE_LIMIT - 1] + "…"
    if len(body_str) > _BODY_LIMIT:
        body_str = body_str[: _BODY_LIMIT - 1] + "…"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "User-Agent": user_agent,
    }
    data = {
        "sr": subreddit,
        "kind": "self",
        "title": title_str,
        "text": body_str,
        "api_type": "json",
    }

    owns_client = False
    if client is None:
        client = httpx.Client(timeout=30.0)
        owns_client = True

    try:
        resp = client.post(f"{_BASE}/api/submit", data=data, headers=headers)
    finally:
        if owns_client:
            client.close()

    if resp.status_code in (401, 403):
        raise RedditAuthError(
            f"submit {resp.status_code}: {resp.text[:200]}"
        )
    if resp.status_code != 200:
        raise RedditPublishError(
            f"submit {resp.status_code}: {resp.text[:200]}"
        )

    # Reddit returns JSON with a nested data structure when api_type=json
    try:
        payload = resp.json()
    except Exception as exc:
        raise RedditPublishError(f"non-JSON response: {exc}") from exc

    errors = (payload.get("json") or {}).get("errors") or []
    if errors:
        raise RedditPublishError(f"errors: {errors[:3]}")

    data_block = (payload.get("json") or {}).get("data") or {}
    # `name` is the fullname like t3_abc123; `url` is the permalink
    name = str(data_block.get("name", ""))
    url = data_block.get("url")
    return PublishResult(
        provider="reddit",
        remote_id=name,
        permalink=url,
        raw={"name": name, "url": url},
    )


__all__ = ["publish_to_reddit", "RedditAuthError", "RedditPublishError"]
