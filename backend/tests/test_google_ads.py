"""Phase 7.x — Google Ads adapter unit tests."""

from __future__ import annotations

import json

import httpx
import pytest
import pytest_asyncio

from app.core.config import settings
from app.services.ads.google import (
    GoogleAdsAuthError,
    GoogleAdsError,
    create_campaign,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def _set_creds(monkeypatch, *, access="TOK", dev="DEV", cust="123"):
    monkeypatch.setattr(
        settings, "google_ads_access_token", access, raising=False
    )
    monkeypatch.setattr(
        settings, "google_ads_developer_token", dev, raising=False
    )
    monkeypatch.setattr(
        settings, "google_ads_customer_id", cust, raising=False
    )
    monkeypatch.setattr(
        settings, "google_ads_login_customer_id", "", raising=False
    )


def test_stub_when_any_cred_missing(monkeypatch):
    _set_creds(monkeypatch, access="", dev="DEV", cust="123")
    res = create_campaign(name="Q3", daily_budget_usd=10.0)
    assert res.provider == "google"
    assert res.stub is True


def test_two_step_happy_path_paused_with_micros(monkeypatch):
    _set_creds(monkeypatch)
    calls: list = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((str(request.url), json.loads(request.content.decode())))
        if "campaignBudgets:mutate" in str(request.url):
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "resourceName": "customers/123/campaignBudgets/999"
                        }
                    ]
                },
            )
        if "campaigns:mutate" in str(request.url):
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "resourceName": "customers/123/campaigns/777"
                        }
                    ]
                },
            )
        return httpx.Response(404)

    res = create_campaign(
        name="Q3 launch",
        daily_budget_usd=25.5,
        advertising_channel_type="DISPLAY",
        client=_client(handler),
    )

    # Step 1: budget call
    assert "campaignBudgets:mutate" in calls[0][0]
    op = calls[0][1]["operations"][0]["create"]
    assert op["amountMicros"] == 25500000
    assert op["deliveryMethod"] == "STANDARD"

    # Step 2: campaign call references the budget resource
    assert "campaigns:mutate" in calls[1][0]
    cop = calls[1][1]["operations"][0]["create"]
    assert cop["status"] == "PAUSED"
    assert cop["advertisingChannelType"] == "DISPLAY"
    assert cop["campaignBudget"] == "customers/123/campaignBudgets/999"

    assert res.external_id == "777"
    assert "777" in (res.permalink or "")
    assert res.raw["budget_resource"] == "customers/123/campaignBudgets/999"


def test_developer_token_header_sent(monkeypatch):
    _set_creds(monkeypatch, dev="dev_xyz")
    captured = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request.headers.get("developer-token"))
        if "campaignBudgets:mutate" in str(request.url):
            return httpx.Response(
                200,
                json={"results": [{"resourceName": "customers/123/campaignBudgets/1"}]},
            )
        return httpx.Response(
            200,
            json={"results": [{"resourceName": "customers/123/campaigns/2"}]},
        )

    create_campaign(
        name="x",
        daily_budget_usd=1.0,
        client=_client(handler),
    )
    assert captured == ["dev_xyz", "dev_xyz"]


def test_login_customer_id_header_when_set(monkeypatch):
    _set_creds(monkeypatch)
    monkeypatch.setattr(
        settings, "google_ads_login_customer_id", "MCC_999", raising=False
    )
    captured = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request.headers.get("login-customer-id"))
        if "campaignBudgets:mutate" in str(request.url):
            return httpx.Response(
                200,
                json={"results": [{"resourceName": "customers/123/campaignBudgets/1"}]},
            )
        return httpx.Response(
            200,
            json={"results": [{"resourceName": "customers/123/campaigns/2"}]},
        )

    create_campaign(name="x", daily_budget_usd=1.0, client=_client(handler))
    assert captured == ["MCC_999", "MCC_999"]


def test_401_on_budget_raises_auth(monkeypatch):
    _set_creds(monkeypatch)
    with pytest.raises(GoogleAdsAuthError):
        create_campaign(
            name="x",
            daily_budget_usd=1.0,
            client=_client(lambda r: httpx.Response(401, text="bad")),
        )


def test_500_on_campaigns_raises_error(monkeypatch):
    _set_creds(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        if "campaignBudgets:mutate" in str(request.url):
            return httpx.Response(
                200,
                json={"results": [{"resourceName": "customers/123/campaignBudgets/1"}]},
            )
        return httpx.Response(500, text="oops")

    with pytest.raises(GoogleAdsError):
        create_campaign(
            name="x",
            daily_budget_usd=1.0,
            client=_client(handler),
        )


def test_empty_results_raises_error(monkeypatch):
    _set_creds(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"results": []})

    with pytest.raises(GoogleAdsError):
        create_campaign(
            name="x",
            daily_budget_usd=1.0,
            client=_client(handler),
        )
