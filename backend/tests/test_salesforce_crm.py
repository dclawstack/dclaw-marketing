"""Phase 8.7 — Salesforce CRM adapter unit tests."""

from __future__ import annotations

import json

import httpx
import pytest
import pytest_asyncio

from app.services.crm import salesforce
from app.services.crm.salesforce import (
    SalesforceAuthError,
    SalesforceSyncError,
    _lead_to_properties,
    pull_contact,
    push_lead,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


# ---------- field mapping --------------------------------------------


def test_field_mapping_basic():
    out = _lead_to_properties({
        "email": "alice@example.com",
        "first_name": "Alice",
        "last_name": "Lee",
        "company": "Acme",
        "phone": "+1-555",
    })
    assert out == {
        "Email": "alice@example.com",
        "FirstName": "Alice",
        "LastName": "Lee",
        "Company": "Acme",
        "Phone": "+1-555",
    }


def test_field_mapping_injects_required_defaults():
    """Salesforce requires LastName + Company on a Lead — we inject."""
    out = _lead_to_properties({"email": "x@y.io"})
    assert out["LastName"] == "(unknown)"
    assert out["Company"] == "(unknown)"


def test_field_mapping_keeps_provided_required_values():
    out = _lead_to_properties({
        "email": "x@y.io",
        "last_name": "Real",
        "company": "RealCo",
    })
    assert out["LastName"] == "Real"
    assert out["Company"] == "RealCo"


# ---------- push_lead -------------------------------------------------


@pytest.mark.asyncio
async def test_push_no_token_returns_stub(monkeypatch):
    monkeypatch.setattr(salesforce.settings, "salesforce_access_token", "")
    monkeypatch.setattr(salesforce.settings, "salesforce_instance_url", "https://x.my.salesforce.com")
    res = await push_lead(lead={"email": "alice@x.io"})
    assert res.provider == "salesforce"
    assert res.stub is True


@pytest.mark.asyncio
async def test_push_no_instance_returns_stub(monkeypatch):
    monkeypatch.setattr(salesforce.settings, "salesforce_access_token", "tok")
    monkeypatch.setattr(salesforce.settings, "salesforce_instance_url", "")
    res = await push_lead(lead={"email": "alice@x.io"})
    assert res.stub is True


@pytest.mark.asyncio
async def test_push_requires_email():
    with pytest.raises(SalesforceSyncError, match="email"):
        await push_lead(lead={})


@pytest.mark.asyncio
async def test_push_creates_when_not_found(monkeypatch):
    monkeypatch.setattr(salesforce.settings, "salesforce_access_token", "tok")
    monkeypatch.setattr(salesforce.settings, "salesforce_instance_url", "https://x.salesforce.com")
    calls = []

    def handler(request):
        path = request.url.path
        calls.append(f"{request.method} {path}")
        assert request.headers["Authorization"] == "Bearer tok"
        if "/query/" in path:
            return httpx.Response(200, json={"records": [], "totalSize": 0})
        if "/sobjects/Lead/" in path and request.method == "POST":
            body = json.loads(request.content.decode("utf-8"))
            assert body["Email"] == "alice@example.com"
            assert body["FirstName"] == "Alice"
            return httpx.Response(
                201,
                json={"id": "00Q123", "success": True, "errors": []},
            )
        return httpx.Response(404, text=path)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    res = await push_lead(
        lead={"email": "alice@example.com", "first_name": "Alice", "last_name": "Lee"},
        client=client,
    )
    await client.aclose()
    assert calls == [
        "GET /services/data/v60.0/query/",
        "POST /services/data/v60.0/sobjects/Lead/",
    ]
    assert res.external_id == "00Q123"


@pytest.mark.asyncio
async def test_push_patches_when_found(monkeypatch):
    monkeypatch.setattr(salesforce.settings, "salesforce_access_token", "tok")
    monkeypatch.setattr(salesforce.settings, "salesforce_instance_url", "https://x.salesforce.com")
    calls = []

    def handler(request):
        path = request.url.path
        calls.append(f"{request.method} {path}")
        if "/query/" in path:
            return httpx.Response(
                200,
                json={
                    "records": [
                        {"Id": "00Q-existing", "Email": "alice@example.com"}
                    ],
                    "totalSize": 1,
                },
            )
        if path.endswith("/sobjects/Lead/00Q-existing"):
            return httpx.Response(204)
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    res = await push_lead(
        lead={"email": "alice@example.com", "first_name": "A", "last_name": "B"},
        client=client,
    )
    await client.aclose()
    assert "PATCH /services/data/v60.0/sobjects/Lead/00Q-existing" in calls
    assert res.external_id == "00Q-existing"


@pytest.mark.asyncio
async def test_push_401_raises_auth_error(monkeypatch):
    monkeypatch.setattr(salesforce.settings, "salesforce_access_token", "bad")
    monkeypatch.setattr(salesforce.settings, "salesforce_instance_url", "https://x.salesforce.com")

    def handler(request):
        return httpx.Response(401, text="INVALID_SESSION_ID")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with pytest.raises(SalesforceAuthError):
        await push_lead(lead={"email": "a@x.io"}, client=client)
    await client.aclose()


# ---------- pull_contact ---------------------------------------------


@pytest.mark.asyncio
async def test_pull_no_token_returns_none(monkeypatch):
    monkeypatch.setattr(salesforce.settings, "salesforce_access_token", "")
    monkeypatch.setattr(salesforce.settings, "salesforce_instance_url", "https://x")
    res = await pull_contact(email="x@y.io")
    assert res is None


@pytest.mark.asyncio
async def test_pull_found(monkeypatch):
    monkeypatch.setattr(salesforce.settings, "salesforce_access_token", "tok")
    monkeypatch.setattr(salesforce.settings, "salesforce_instance_url", "https://x.salesforce.com")

    def handler(request):
        return httpx.Response(
            200,
            json={
                "records": [
                    {
                        "Id": "00Q42",
                        "Email": "alice@example.com",
                        "FirstName": "Alice",
                        "LastName": "Lee",
                        "Company": "Acme",
                    }
                ],
                "totalSize": 1,
            },
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    res = await pull_contact(email="alice@example.com", client=client)
    await client.aclose()
    assert res is not None
    assert res.external_id == "00Q42"
    assert res.properties["FirstName"] == "Alice"


@pytest.mark.asyncio
async def test_pull_not_found(monkeypatch):
    monkeypatch.setattr(salesforce.settings, "salesforce_access_token", "tok")
    monkeypatch.setattr(salesforce.settings, "salesforce_instance_url", "https://x.salesforce.com")

    def handler(request):
        return httpx.Response(200, json={"records": [], "totalSize": 0})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    res = await pull_contact(email="missing@x.io", client=client)
    await client.aclose()
    assert res is None
