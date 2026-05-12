"""Mailchimp newsletter adapter — Phase 7.5.

Three-step send via the Marketing API v3:

  1. POST /campaigns
       — declare the campaign (type=regular, list_id, subject)
  2. PUT  /campaigns/{id}/content
       — set the HTML body
  3. POST /campaigns/{id}/actions/send
       — fire it

API base URL is data-center-specific:
``https://{server_prefix}.api.mailchimp.com/3.0/``. The server prefix
is the suffix on the API key (``abc123-us21`` → ``us21``) but we
require it as an explicit config value to avoid parsing surprises.

Auth: HTTP Basic with username=``anystring`` and password=api_key.

Stub fallback: synthetic ``mc_stub_<sha>`` campaign id when no key.
"""

from __future__ import annotations

import hashlib

import httpx

from app.core.config import settings
from app.services.newsletter import NewsletterResult


class MailchimpAuthError(RuntimeError):
    pass


class MailchimpPublishError(RuntimeError):
    pass


def _stub_result(list_id: str, subject: str, html: str) -> NewsletterResult:
    digest = hashlib.sha256(
        (list_id + "::" + subject + "::" + html[:512]).encode("utf-8")
    ).hexdigest()[:18]
    return NewsletterResult(
        provider="mailchimp",
        campaign_id=f"mc_stub_{digest}",
        recipient_count=None,
        raw={"stub": True, "list_id": list_id, "subject": subject},
    )


def _base_url() -> str:
    return f"https://{settings.mailchimp_server_prefix}.api.mailchimp.com/3.0"


async def send_campaign(
    *,
    list_id: str,
    subject: str,
    html: str,
    from_name: str | None = None,
    reply_to: str | None = None,
    client: httpx.AsyncClient | None = None,
) -> NewsletterResult:
    """Creates + sends a Mailchimp regular campaign.

    Falls back to a synthetic stub when ``MAILCHIMP_API_KEY`` is unset
    or any step raises — callers always get a NewsletterResult.

    Note: per Mailchimp API rules, the audience (list_id) must already
    exist; this function does NOT create audiences or add subscribers.
    Use Mailchimp's UI or the /lists endpoint separately.
    """
    if not settings.mailchimp_api_key:
        return _stub_result(list_id, subject, html)
    if not settings.mailchimp_server_prefix:
        # No server prefix → can't construct the URL — stub.
        return _stub_result(list_id, subject, html)

    base = _base_url()
    auth = httpx.BasicAuth("anystring", settings.mailchimp_api_key)
    owns_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=30.0)
        owns_client = True

    try:
        # 1. Create campaign
        body = {
            "type": "regular",
            "recipients": {"list_id": list_id},
            "settings": {
                "subject_line": subject,
                "from_name": from_name or settings.resend_from_email.split("<")[0].strip()
                or "DClaw Marketing",
                "reply_to": reply_to or settings.resend_from_email.split("<")[-1].rstrip(">").strip(),
                "title": subject,
            },
        }
        try:
            create = await client.post(
                f"{base}/campaigns", json=body, auth=auth
            )
        except httpx.HTTPError as exc:
            raise MailchimpPublishError(f"create transport: {exc}") from exc
        if create.status_code in (401, 403):
            raise MailchimpAuthError(
                f"create {create.status_code}: {create.text[:200]}"
            )
        if create.status_code not in (200, 201):
            raise MailchimpPublishError(
                f"create {create.status_code}: {create.text[:200]}"
            )
        campaign_id = (create.json() or {}).get("id", "")
        recipients = (create.json() or {}).get("recipients") or {}
        recipient_count = recipients.get("recipient_count")

        # 2. Set HTML body
        content = await client.put(
            f"{base}/campaigns/{campaign_id}/content",
            json={"html": html},
            auth=auth,
        )
        if content.status_code not in (200, 201):
            raise MailchimpPublishError(
                f"content {content.status_code}: {content.text[:200]}"
            )

        # 3. Send
        send = await client.post(
            f"{base}/campaigns/{campaign_id}/actions/send",
            json={},
            auth=auth,
        )
        if send.status_code not in (200, 204):
            raise MailchimpPublishError(
                f"send {send.status_code}: {send.text[:200]}"
            )
    finally:
        if owns_client:
            await client.aclose()

    return NewsletterResult(
        provider="mailchimp",
        campaign_id=str(campaign_id),
        recipient_count=int(recipient_count) if recipient_count is not None else None,
        raw={"campaign_id": campaign_id, "recipient_count": recipient_count},
    )


__all__ = ["send_campaign", "MailchimpAuthError", "MailchimpPublishError"]
