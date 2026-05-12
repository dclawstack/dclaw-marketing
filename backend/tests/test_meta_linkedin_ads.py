"""Phase 7.x — Meta + LinkedIn Ads adapter unit tests."""

from __future__ import annotations

import json

import httpx
import pytest
import pytest_asyncio

from app.core.config import settings
from app.services.ads.linkedin import (
    LinkedInAdsAuthError,
    LinkedInAdsError,
    create_campaign as linkedin_create_campaign,
)
from app.services.ads.meta import (
    MetaAdsAuthError,
    MetaAdsError,
    create_campaign as meta_create_campaign,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


# ---------- Meta -----------------------------------------------------------


def test_meta_stub_when_no_token(monkeypatch):
    monkeypatch.setattr(settings, "meta_ads_access_token", "", raising=False)
    monkeypatch.setattr(settings, "meta_ads_account_id", "", raising=False)
    res = meta_create_campaign(name="Launch Q3", daily_budget_usd=10.0)
    assert res.provider == "meta"
    assert res.stub is True
    assert res.external_id.startswith("meta_stub_")


def test_meta_uses_form_encoded_paused_status_and_cents(monkeypatch):
    monkeypatch.setattr(settings, "meta_ads_access_token", "TOK", raising=False)
    monkeypatch.setattr(settings, "meta_ads_account_id", "999", raising=False)
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = dict(
            [p.split("=", 1) for p in request.content.decode().split("&")]
        )
        return httpx.Response(200, json={"id": "1234567890"})

    res = meta_create_campaign(
        name="Launch Q3",
        daily_budget_usd=25.50,
        objective="OUTCOME_LEADS",
        client=_client(handler),
    )
    assert captured["url"] == (
        "https://graph.facebook.com/v18.0/act_999/campaigns"
    )
    assert captured["body"]["status"] == "PAUSED"
    assert captured["body"]["objective"] == "OUTCOME_LEADS"
    assert captured["body"]["daily_budget"] == "2550"  # cents
    assert captured["body"]["access_token"] == "TOK"
    # special_ad_categories is url-encoded JSON []
    assert captured["body"]["special_ad_categories"].replace("%5B", "[").replace(
        "%5D", "]"
    ) == "[]"
    assert res.external_id == "1234567890"
    assert "1234567890" in (res.permalink or "")


def test_meta_401_raises_auth(monkeypatch):
    monkeypatch.setattr(settings, "meta_ads_access_token", "BAD", raising=False)
    monkeypatch.setattr(settings, "meta_ads_account_id", "1", raising=False)
    with pytest.raises(MetaAdsAuthError):
        meta_create_campaign(
            name="x",
            daily_budget_usd=1.0,
            client=_client(lambda r: httpx.Response(401, text="bad")),
        )


def test_meta_500_raises_error(monkeypatch):
    monkeypatch.setattr(settings, "meta_ads_access_token", "TOK", raising=False)
    monkeypatch.setattr(settings, "meta_ads_account_id", "1", raising=False)
    with pytest.raises(MetaAdsError):
        meta_create_campaign(
            name="x",
            daily_budget_usd=1.0,
            client=_client(lambda r: httpx.Response(500, text="oops")),
        )


# ---------- LinkedIn -------------------------------------------------------


def test_linkedin_stub_when_no_token(monkeypatch):
    monkeypatch.setattr(
        settings, "linkedin_ads_access_token", "", raising=False
    )
    monkeypatch.setattr(
        settings, "linkedin_ads_account_id", "", raising=False
    )
    res = linkedin_create_campaign(name="Q3", daily_budget_usd=20.0)
    assert res.provider == "linkedin"
    assert res.stub is True
    assert res.external_id.startswith("linkedin_stub_")


def test_linkedin_real_creates_paused_campaign_with_urns(monkeypatch):
    monkeypatch.setattr(
        settings, "linkedin_ads_access_token", "TOK", raising=False
    )
    monkeypatch.setattr(
        settings, "linkedin_ads_account_id", "555", raising=False
    )
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization")
        captured["version"] = request.headers.get("LinkedIn-Version")
        captured["body"] = json.loads(request.content.decode("utf-8"))
        return httpx.Response(
            201,
            headers={"x-restli-id": "1000222333"},
            content=b"",
        )

    res = linkedin_create_campaign(
        name="Q3 launch",
        daily_budget_usd=25.0,
        objective_type="LEAD_GENERATION",
        campaign_group_id="777",
        client=_client(handler),
    )
    assert captured["url"] == "https://api.linkedin.com/rest/adCampaigns"
    assert captured["auth"] == "Bearer TOK"
    assert captured["version"] == "202404"
    assert captured["body"]["status"] == "PAUSED"
    assert captured["body"]["objectiveType"] == "LEAD_GENERATION"
    assert (
        captured["body"]["account"] == "urn:li:sponsoredAccount:555"
    )
    assert (
        captured["body"]["campaignGroup"]
        == "urn:li:sponsoredCampaignGroup:777"
    )
    assert captured["body"]["dailyBudget"] == {
        "amount": "25.00",
        "currencyCode": "USD",
    }
    assert res.external_id == "1000222333"
    assert "555/campaigns/1000222333" in (res.permalink or "")


def test_linkedin_401_raises_auth(monkeypatch):
    monkeypatch.setattr(
        settings, "linkedin_ads_access_token", "BAD", raising=False
    )
    monkeypatch.setattr(
        settings, "linkedin_ads_account_id", "1", raising=False
    )
    with pytest.raises(LinkedInAdsAuthError):
        linkedin_create_campaign(
            name="x",
            daily_budget_usd=1.0,
            client=_client(lambda r: httpx.Response(401, text="bad")),
        )


def test_linkedin_500_raises_error(monkeypatch):
    monkeypatch.setattr(
        settings, "linkedin_ads_access_token", "TOK", raising=False
    )
    monkeypatch.setattr(
        settings, "linkedin_ads_account_id", "1", raising=False
    )
    with pytest.raises(LinkedInAdsError):
        linkedin_create_campaign(
            name="x",
            daily_budget_usd=1.0,
            client=_client(lambda r: httpx.Response(500, text="oops")),
        )
