"""Meta (Facebook + Instagram) Ads adapter — Phase 7.x.

Creates a paused Marketing API campaign on the configured ad account:

  POST https://graph.facebook.com/v18.0/act_{account_id}/campaigns
       Form-encoded:
         name            = <campaign name>
         objective       = OUTCOME_TRAFFIC | OUTCOME_LEADS | ...
         status          = PAUSED   (Hard-gate default — explicit unpause later)
         special_ad_categories = []
         daily_budget    = <cents>
         access_token    = <ad-account access token>
  → {"id": "<campaign_id>"}

The daily_budget value is in the ad account's currency *minor units*
(cents). We convert from a Pythonic USD float for ergonomics.

Stub fallback when ``settings.meta_ads_access_token`` is empty.
"""

from __future__ import annotations

import hashlib
import json

import httpx

from app.core.config import settings
from app.services.ads import AdCreateResult


_GRAPH_VERSION = "v18.0"
_DEFAULT_OBJECTIVE = "OUTCOME_TRAFFIC"


class MetaAdsAuthError(RuntimeError):
    pass


class MetaAdsError(RuntimeError):
    pass


def _stub_result(name: str) -> AdCreateResult:
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:18]
    return AdCreateResult(
        provider="meta",
        external_id=f"meta_stub_{digest}",
        permalink=None,
        raw={"stub": True, "name": name},
        stub=True,
    )


def create_campaign(
    *,
    name: str,
    daily_budget_usd: float,
    objective: str = _DEFAULT_OBJECTIVE,
    account_id: str | None = None,
    access_token: str | None = None,
    client: httpx.Client | None = None,
) -> AdCreateResult:
    """Creates a paused Meta Ads campaign.

    Args:
        name: Campaign display name.
        daily_budget_usd: Float USD, converted to cents server-side.
        objective: One of Meta's OUTCOME_* values. Default
            ``OUTCOME_TRAFFIC`` because it's the broadest.
        account_id: Numeric Meta ad-account id (no ``act_`` prefix).
            Falls back to ``settings.meta_ads_account_id``.
        access_token: Account access token. Falls back to
            ``settings.meta_ads_access_token``. Empty/None → stub.

    Raises:
        MetaAdsAuthError: 401/403.
        MetaAdsError: any other non-200.
    """
    token = access_token or settings.meta_ads_access_token
    acc = account_id or settings.meta_ads_account_id
    if not token or not acc:
        return _stub_result(name)

    url = (
        f"https://graph.facebook.com/{_GRAPH_VERSION}/act_{acc}/campaigns"
    )
    body = {
        "name": name,
        "objective": objective,
        "status": "PAUSED",
        # Marketing API requires special_ad_categories to be a JSON
        # array literal even when empty.
        "special_ad_categories": json.dumps([]),
        "daily_budget": str(int(round(daily_budget_usd * 100))),
        "access_token": token,
    }

    owns_client = False
    if client is None:
        client = httpx.Client(timeout=30.0)
        owns_client = True
    try:
        resp = client.post(url, data=body)
    finally:
        if owns_client:
            client.close()

    if resp.status_code in (401, 403):
        raise MetaAdsAuthError(
            f"campaigns {resp.status_code}: {resp.text[:200]}"
        )
    if resp.status_code != 200:
        raise MetaAdsError(f"campaigns {resp.status_code}: {resp.text[:200]}")

    data = resp.json() or {}
    campaign_id = str(data.get("id") or "")
    permalink = (
        f"https://business.facebook.com/adsmanager/manage/campaigns?act={acc}"
        f"&selected_campaign_ids={campaign_id}"
        if campaign_id
        else None
    )
    return AdCreateResult(
        provider="meta",
        external_id=campaign_id,
        permalink=permalink,
        raw=data,
    )


__all__ = ["create_campaign", "MetaAdsAuthError", "MetaAdsError"]
