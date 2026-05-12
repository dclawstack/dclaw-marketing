"""Phase 8.6 — HubSpot CRM adapter unit tests."""

from __future__ import annotations

import json

import httpx
import pytest
import pytest_asyncio

from app.services.crm import hubspot
from app.services.crm.hubspot import (
    HubSpotAuthError,
    HubSpotSyncError,
    _lead_to_properties,
    pull_contact,
    push_lead,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


# ---------- pure-function tests --------------------------------------


def test_field_mapping_basic():
    out = _lead_to_properties({
        "email": "alice@example.com",
        "first_name": "Alice",
        "last_name": "Lee",
        "company": "Acme",
        "phone": "+1-555",
        "linkedin_url": "https://linkedin.com/in/alice",
    })
    assert out == {
        "email": "alice@example.com",
        "firstname": "Alice",
        "lastname": "Lee",
        "company": "Acme",
        "phone": "+1-555",
        "linkedinbio": "https://linkedin.com/in/alice",
    }


def test_field_mapping_skips_none_and_empty():
    out = _lead_to_properties({
        "email": "alice@example.com",
        "first_name": "",
        "last_name": None,
        "company": "Acme",
    })
    assert out == {
        "email": "alice@example.com",
        "company": "Acme",
    }


def test_field_mapping_ignores_unknown_keys():
    out = _lead_to_properties({"email": "a@x.io", "weirdfield": "ignored"})
    assert "weirdfield" not in out


# ---------- push_lead — stub + real ----------------------------------


@pytest.mark.asyncio
async def test_push_lead_no_token_returns_stub(monkeypatch):
    monkeypatch.setattr(hubspot.settings, "hubspot_access_token", "")
    res = await push_lead(lead={"email": "alice@example.com"})
    assert res.provider == "hubspot"
    assert res.stub is True
    assert res.external_id.startswith("hs_stub_")


@pytest.mark.asyncio
async def test_push_lead_requires_email(monkeypatch):
    monkeypatch.setattr(hubspot.settings, "hubspot_access_token", "")
    with pytest.raises(HubSpotSyncError, match="email"):
        await push_lead(lead={})


@pytest.mark.asyncio
async def test_push_lead_creates_when_not_found(monkeypatch):
    monkeypatch.setattr(hubspot.settings, "hubspot_access_token", "tok")
    calls = []

    def handler(request):
        path = request.url.path
        calls.append(f"{request.method} {path}")
        assert request.headers["Authorization"] == "Bearer tok"
        if path.endswith("/search"):
            return httpx.Response(200, json={"results": []})
        if path.endswith("/contacts"):
            body = json.loads(request.content.decode("utf-8"))
            assert body["properties"]["email"] == "alice@example.com"
            return httpx.Response(
                201,
                json={
                    "id": "c-1",
                    "properties": {"email": "alice@example.com", "firstname": "Alice"},
                },
            )
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    res = await push_lead(
        lead={"email": "alice@example.com", "first_name": "Alice"},
        client=client,
    )
    await client.aclose()
    assert calls == [
        "POST /crm/v3/objects/contacts/search",
        "POST /crm/v3/objects/contacts",
    ]
    assert res.external_id == "c-1"


@pytest.mark.asyncio
async def test_push_lead_patches_when_found(monkeypatch):
    monkeypatch.setattr(hubspot.settings, "hubspot_access_token", "tok")
    calls = []

    def handler(request):
        path = request.url.path
        calls.append(f"{request.method} {path}")
        if path.endswith("/search"):
            return httpx.Response(200, json={"results": [{"id": "existing-99"}]})
        if path.endswith("/contacts/existing-99"):
            return httpx.Response(
                200,
                json={
                    "id": "existing-99",
                    "properties": {"firstname": "Alice"},
                },
            )
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    res = await push_lead(
        lead={"email": "alice@example.com", "first_name": "Alice"},
        client=client,
    )
    await client.aclose()
    assert calls == [
        "POST /crm/v3/objects/contacts/search",
        "PATCH /crm/v3/objects/contacts/existing-99",
    ]
    assert res.external_id == "existing-99"


@pytest.mark.asyncio
async def test_push_lead_401_raises_auth_error(monkeypatch):
    monkeypatch.setattr(hubspot.settings, "hubspot_access_token", "bad")

    def handler(request):
        return httpx.Response(401, text="invalid token")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with pytest.raises(HubSpotAuthError):
        await push_lead(lead={"email": "alice@example.com"}, client=client)
    await client.aclose()


# ---------- pull_contact ---------------------------------------------


@pytest.mark.asyncio
async def test_pull_contact_no_token_returns_none(monkeypatch):
    monkeypatch.setattr(hubspot.settings, "hubspot_access_token", "")
    res = await pull_contact(email="x@y.io")
    assert res is None


@pytest.mark.asyncio
async def test_pull_contact_found(monkeypatch):
    monkeypatch.setattr(hubspot.settings, "hubspot_access_token", "tok")

    def handler(request):
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "id": "c-42",
                        "properties": {
                            "email": "alice@example.com",
                            "firstname": "Alice",
                            "company": "Acme",
                        },
                    }
                ]
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    res = await pull_contact(email="alice@example.com", client=client)
    await client.aclose()
    assert res is not None
    assert res.external_id == "c-42"
    assert res.properties["firstname"] == "Alice"
    assert res.properties["company"] == "Acme"


@pytest.mark.asyncio
async def test_pull_contact_not_found(monkeypatch):
    monkeypatch.setattr(hubspot.settings, "hubspot_access_token", "tok")

    def handler(request):
        return httpx.Response(200, json={"results": []})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    res = await pull_contact(email="missing@x.io", client=client)
    await client.aclose()
    assert res is None
