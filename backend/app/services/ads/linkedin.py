"""LinkedIn Ads adapter — Phase 7.x.

Creates a paused campaign on the configured LinkedIn Ads account.

LinkedIn Marketing Developer Platform v202404 expects:

  POST https://api.linkedin.com/rest/adCampaigns
       Headers:
         Authorization: Bearer <ad-account access token>
         LinkedIn-Version: 202404
         X-Restli-Protocol-Version: 2.0.0
         Content-Type: application/json
       Body: {
         "name": "...",
         "account": "urn:li:sponsoredAccount:<account_id>",
         "campaignGroup": "urn:li:sponsoredCampaignGroup:<group_id>",
         "type": "TEXT_AD",
         "status": "PAUSED",
         "objectiveType": "WEBSITE_VISITS",
         "dailyBudget": {"amount": "10", "currencyCode": "USD"},
         ...
       }
  → 201 Created with the campaign id in the X-LinkedIn-Id header.

Stub fallback when token/account is missing. Campaign-group id is
required by LinkedIn; we treat it as part of the SocialAccount's
metadata (``campaign_group_id``) — without it the adapter falls back
to a placeholder that LinkedIn will reject with a clear error.
"""

from __future__ import annotations

import hashlib

import httpx

from app.core.config import settings
from app.services.ads import AdCreateResult


_API_BASE = "https://api.linkedin.com/rest"
_VERSION_HEADER = "202404"


class LinkedInAdsAuthError(RuntimeError):
    pass


class LinkedInAdsError(RuntimeError):
    pass


def _stub_result(name: str) -> AdCreateResult:
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:18]
    return AdCreateResult(
        provider="linkedin",
        external_id=f"linkedin_stub_{digest}",
        permalink=None,
        raw={"stub": True, "name": name},
        stub=True,
    )


def create_campaign(
    *,
    name: str,
    daily_budget_usd: float,
    objective_type: str = "WEBSITE_VISITS",
    account_id: str | None = None,
    campaign_group_id: str | None = None,
    access_token: str | None = None,
    client: httpx.Client | None = None,
) -> AdCreateResult:
    """Creates a paused LinkedIn Ads campaign.

    Args:
        name: Campaign display name.
        daily_budget_usd: Float USD.
        objective_type: LinkedIn's ``objectiveType`` enum value.
        account_id: Numeric sponsored-account id. Falls back to
            ``settings.linkedin_ads_account_id``.
        campaign_group_id: Numeric sponsored-campaign-group id.
            Required by LinkedIn — without it the call will 400.
        access_token: Falls back to ``settings.linkedin_ads_access_token``.
            Empty/None → stub.

    Raises:
        LinkedInAdsAuthError: 401/403.
        LinkedInAdsError: any other non-200/201.
    """
    token = access_token or settings.linkedin_ads_access_token
    acc = account_id or settings.linkedin_ads_account_id
    if not token or not acc:
        return _stub_result(name)

    body = {
        "name": name,
        "account": f"urn:li:sponsoredAccount:{acc}",
        "type": "TEXT_AD",
        "status": "PAUSED",
        "objectiveType": objective_type,
        "dailyBudget": {
            "amount": f"{daily_budget_usd:.2f}",
            "currencyCode": "USD",
        },
    }
    if campaign_group_id:
        body["campaignGroup"] = (
            f"urn:li:sponsoredCampaignGroup:{campaign_group_id}"
        )

    headers = {
        "Authorization": f"Bearer {token}",
        "LinkedIn-Version": _VERSION_HEADER,
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }

    owns_client = False
    if client is None:
        client = httpx.Client(timeout=30.0)
        owns_client = True
    try:
        resp = client.post(
            f"{_API_BASE}/adCampaigns",
            json=body,
            headers=headers,
        )
    finally:
        if owns_client:
            client.close()

    if resp.status_code in (401, 403):
        raise LinkedInAdsAuthError(
            f"adCampaigns {resp.status_code}: {resp.text[:200]}"
        )
    if resp.status_code not in (200, 201):
        raise LinkedInAdsError(
            f"adCampaigns {resp.status_code}: {resp.text[:200]}"
        )

    # LinkedIn returns the new id in the X-LinkedIn-Id (or x-restli-id) header
    # rather than the body.
    new_id = (
        resp.headers.get("x-restli-id")
        or resp.headers.get("X-LinkedIn-Id")
        or ""
    )
    permalink = (
        f"https://www.linkedin.com/campaignmanager/accounts/{acc}/campaigns/{new_id}"
        if new_id
        else None
    )
    raw_body: dict
    try:
        raw_body = resp.json() or {}
    except Exception:
        raw_body = {}
    return AdCreateResult(
        provider="linkedin",
        external_id=str(new_id),
        permalink=permalink,
        raw={"headers": dict(resp.headers), "body": raw_body},
    )


__all__ = ["create_campaign", "LinkedInAdsAuthError", "LinkedInAdsError"]
