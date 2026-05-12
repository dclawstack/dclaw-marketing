"""Google Ads adapter — Phase 7.x.

Google's Ads API requires:

  • OAuth 2.0 access token (Bearer header)
  • A developer-token header (provisioned per Google Ads MCC)
  • Optional login-customer-id header when the token is on a manager
    account acting on behalf of a sub-account

Campaign creation is a two-step:

  1. POST /v15/customers/{customer_id}/campaignBudgets:mutate
        {"operations": [{"create": {"name": "...", "amountMicros": N}}]}
     → {"results": [{"resourceName": "customers/.../campaignBudgets/..."}]}

  2. POST /v15/customers/{customer_id}/campaigns:mutate
        {"operations": [{"create": {
            "name": ..., "status": "PAUSED",
            "advertisingChannelType": "SEARCH",
            "campaignBudget": "<resource name from step 1>",
            ...
        }}]}
     → {"results": [{"resourceName": "customers/.../campaigns/..."}]}

The budget amount is in *micros* (currency_minor_units × 1_000_000),
i.e. $25.50 USD = 25_500_000 micros.

Stub fallback when any of (access_token, developer_token, customer_id)
is missing.
"""

from __future__ import annotations

import hashlib

import httpx

from app.core.config import settings
from app.services.ads import AdCreateResult


_API_BASE = "https://googleads.googleapis.com/v15"


class GoogleAdsAuthError(RuntimeError):
    pass


class GoogleAdsError(RuntimeError):
    pass


def _stub_result(name: str) -> AdCreateResult:
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:18]
    return AdCreateResult(
        provider="google",
        external_id=f"google_stub_{digest}",
        permalink=None,
        raw={"stub": True, "name": name},
        stub=True,
    )


def _usd_to_micros(amount_usd: float) -> int:
    return int(round(amount_usd * 1_000_000))


def create_campaign(
    *,
    name: str,
    daily_budget_usd: float,
    advertising_channel_type: str = "SEARCH",
    customer_id: str | None = None,
    access_token: str | None = None,
    developer_token: str | None = None,
    login_customer_id: str | None = None,
    client: httpx.Client | None = None,
) -> AdCreateResult:
    """Creates a paused Google Ads campaign with a fresh daily budget.

    Args:
        name: Campaign display name.
        daily_budget_usd: Float USD, converted to micros.
        advertising_channel_type: ``SEARCH`` | ``DISPLAY`` | ``VIDEO`` | ...
        customer_id: Numeric ad-account id (no hyphens). Falls back to
            ``settings.google_ads_customer_id``.
        access_token: OAuth bearer. Falls back to
            ``settings.google_ads_access_token``.
        developer_token: developer-token header. Falls back to
            ``settings.google_ads_developer_token``.
        login_customer_id: optional manager-account id.

    Raises:
        GoogleAdsAuthError: 401/403 on either step.
        GoogleAdsError: any other non-200.
    """
    tok = access_token or settings.google_ads_access_token
    dev = developer_token or settings.google_ads_developer_token
    cid = customer_id or settings.google_ads_customer_id
    if not (tok and dev and cid):
        return _stub_result(name)

    headers = {
        "Authorization": f"Bearer {tok}",
        "developer-token": dev,
        "Content-Type": "application/json",
    }
    lcid = login_customer_id or settings.google_ads_login_customer_id
    if lcid:
        headers["login-customer-id"] = lcid

    owns_client = False
    if client is None:
        client = httpx.Client(timeout=30.0)
        owns_client = True

    try:
        # 1. Create the daily budget.
        budget_body = {
            "operations": [
                {
                    "create": {
                        "name": f"{name} — budget",
                        "deliveryMethod": "STANDARD",
                        "amountMicros": _usd_to_micros(daily_budget_usd),
                    }
                }
            ]
        }
        b_resp = client.post(
            f"{_API_BASE}/customers/{cid}/campaignBudgets:mutate",
            json=budget_body,
            headers=headers,
        )
        if b_resp.status_code in (401, 403):
            raise GoogleAdsAuthError(
                f"budgets {b_resp.status_code}: {b_resp.text[:200]}"
            )
        if b_resp.status_code != 200:
            raise GoogleAdsError(
                f"budgets {b_resp.status_code}: {b_resp.text[:200]}"
            )
        budget_results = (b_resp.json() or {}).get("results") or []
        if not budget_results:
            raise GoogleAdsError("budgets mutate returned no results")
        budget_resource = budget_results[0].get("resourceName") or ""

        # 2. Create the campaign referencing that budget.
        campaign_body = {
            "operations": [
                {
                    "create": {
                        "name": name,
                        "status": "PAUSED",
                        "advertisingChannelType": advertising_channel_type,
                        "campaignBudget": budget_resource,
                    }
                }
            ]
        }
        c_resp = client.post(
            f"{_API_BASE}/customers/{cid}/campaigns:mutate",
            json=campaign_body,
            headers=headers,
        )
    finally:
        if owns_client:
            client.close()

    if c_resp.status_code in (401, 403):
        raise GoogleAdsAuthError(
            f"campaigns {c_resp.status_code}: {c_resp.text[:200]}"
        )
    if c_resp.status_code != 200:
        raise GoogleAdsError(
            f"campaigns {c_resp.status_code}: {c_resp.text[:200]}"
        )
    campaign_results = (c_resp.json() or {}).get("results") or []
    if not campaign_results:
        raise GoogleAdsError("campaigns mutate returned no results")
    campaign_resource = campaign_results[0].get("resourceName") or ""
    campaign_id = (
        campaign_resource.rsplit("/", 1)[-1] if campaign_resource else ""
    )

    permalink = (
        f"https://ads.google.com/aw/campaigns?ocid=&campaignId={campaign_id}"
        if campaign_id
        else None
    )
    return AdCreateResult(
        provider="google",
        external_id=campaign_id,
        permalink=permalink,
        raw={
            "budget_resource": budget_resource,
            "campaign_resource": campaign_resource,
        },
    )


__all__ = ["create_campaign", "GoogleAdsAuthError", "GoogleAdsError"]
