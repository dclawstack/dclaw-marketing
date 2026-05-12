"""Phase 8.x — Pipedrive + Attio CRM sync unit tests."""

from __future__ import annotations

import json

import httpx
import pytest
import pytest_asyncio

from app.core.config import settings
from app.services.crm import attio as attio_mod
from app.services.crm import pipedrive as pipedrive_mod
from app.services.crm.attio import AttioAuthError, AttioSyncError
from app.services.crm.pipedrive import PipedriveAuthError, PipedriveSyncError


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


def _client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


# ---------- Pipedrive -------------------------------------------------------


@pytest.mark.asyncio
async def test_pd_stub_when_no_token(monkeypatch):
    monkeypatch.setattr(settings, "pipedrive_api_token", "", raising=False)
    res = await pipedrive_mod.push_lead(lead={"email": "a@b.com"})
    assert res.provider == "pipedrive"
    assert res.stub is True
    assert res.external_id.startswith("pd_stub_")


@pytest.mark.asyncio
async def test_pd_missing_email_raises():
    with pytest.raises(PipedriveSyncError):
        await pipedrive_mod.push_lead(lead={"first_name": "x"})


@pytest.mark.asyncio
async def test_pd_search_then_create_when_no_match(monkeypatch):
    monkeypatch.setattr(settings, "pipedrive_api_token", "TOK", raising=False)
    calls: list = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path, str(request.url)))
        if request.method == "GET" and request.url.path.endswith("/search"):
            return httpx.Response(200, json={"data": {"items": []}})
        if request.method == "POST" and request.url.path.endswith("/persons"):
            payload = json.loads(request.content.decode())
            assert payload["name"] == "Alice Smith"
            assert payload["email"] == [
                {"value": "a@b.com", "primary": True, "label": "work"}
            ]
            return httpx.Response(201, json={"data": {"id": 42, "name": "Alice Smith"}})
        return httpx.Response(404)

    res = await pipedrive_mod.push_lead(
        lead={
            "email": "a@b.com",
            "first_name": "Alice",
            "last_name": "Smith",
            "phone": "+1-555",
            "company": "Acme",
        },
        client=_client(handler),
    )
    assert res.external_id == "42"
    assert "TOK" in calls[0][2]
    assert calls[0][0] == "GET"
    assert calls[1][0] == "POST"


@pytest.mark.asyncio
async def test_pd_update_when_match(monkeypatch):
    monkeypatch.setattr(settings, "pipedrive_api_token", "TOK", raising=False)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(
                200,
                json={"data": {"items": [{"item": {"id": 7, "name": "Existing"}}]}},
            )
        # Must be PUT now.
        assert request.method == "PUT"
        assert request.url.path == "/v1/persons/7"
        return httpx.Response(200, json={"data": {"id": 7, "name": "Alice"}})

    res = await pipedrive_mod.push_lead(
        lead={"email": "a@b.com", "first_name": "Alice"},
        client=_client(handler),
    )
    assert res.external_id == "7"


@pytest.mark.asyncio
async def test_pd_401_raises_auth(monkeypatch):
    monkeypatch.setattr(settings, "pipedrive_api_token", "BAD", raising=False)

    def handler(request):
        return httpx.Response(401, text="bad")

    with pytest.raises(PipedriveAuthError):
        await pipedrive_mod.push_lead(
            lead={"email": "a@b.com"}, client=_client(handler)
        )


@pytest.mark.asyncio
async def test_pd_pull_contact_returns_none_when_no_token(monkeypatch):
    monkeypatch.setattr(settings, "pipedrive_api_token", "", raising=False)
    res = await pipedrive_mod.pull_contact(email="x@y.com")
    assert res is None


# ---------- Attio -----------------------------------------------------------


@pytest.mark.asyncio
async def test_at_stub_when_no_token(monkeypatch):
    monkeypatch.setattr(settings, "attio_access_token", "", raising=False)
    res = await attio_mod.push_lead(lead={"email": "a@b.com"})
    assert res.provider == "attio"
    assert res.stub is True
    assert res.external_id.startswith("attio_stub_")


@pytest.mark.asyncio
async def test_at_upsert_uses_put_with_matching_attribute(monkeypatch):
    monkeypatch.setattr(settings, "attio_access_token", "TOK", raising=False)
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization")
        captured["body"] = json.loads(request.content.decode())
        return httpx.Response(
            200,
            json={
                "data": {
                    "id": {"record_id": "rec_abc"},
                    "values": {
                        "email_addresses": [{"email_address": "a@b.com"}]
                    },
                }
            },
        )

    res = await attio_mod.push_lead(
        lead={
            "email": "a@b.com",
            "first_name": "Alice",
            "last_name": "Smith",
            "linkedin_url": "https://linkedin.com/in/alice",
        },
        client=_client(handler),
    )
    assert captured["method"] == "PUT"
    assert "matching_attribute=email_addresses" in captured["url"]
    assert captured["auth"] == "Bearer TOK"
    assert (
        captured["body"]["data"]["values"]["email_addresses"]
        == [{"email_address": "a@b.com"}]
    )
    assert captured["body"]["data"]["values"]["name"] == [
        {
            "first_name": "Alice",
            "last_name": "Smith",
            "full_name": "Alice Smith",
        }
    ]
    assert captured["body"]["data"]["values"]["linkedin"] == [
        {"value": "https://linkedin.com/in/alice"}
    ]
    assert res.external_id == "rec_abc"


@pytest.mark.asyncio
async def test_at_401_raises_auth(monkeypatch):
    monkeypatch.setattr(settings, "attio_access_token", "BAD", raising=False)
    with pytest.raises(AttioAuthError):
        await attio_mod.push_lead(
            lead={"email": "x@y.com"},
            client=_client(lambda r: httpx.Response(403, text="forbidden")),
        )


@pytest.mark.asyncio
async def test_at_500_raises_sync_error(monkeypatch):
    monkeypatch.setattr(settings, "attio_access_token", "TOK", raising=False)
    with pytest.raises(AttioSyncError):
        await attio_mod.push_lead(
            lead={"email": "x@y.com"},
            client=_client(lambda r: httpx.Response(500, text="oops")),
        )


@pytest.mark.asyncio
async def test_at_pull_contact_returns_record(monkeypatch):
    monkeypatch.setattr(settings, "attio_access_token", "TOK", raising=False)

    def handler(request):
        return httpx.Response(
            200,
            json={"data": [{"id": {"record_id": "r1"}, "values": {}}]},
        )

    res = await attio_mod.pull_contact(email="a@b.com", client=_client(handler))
    assert res is not None
    assert res.external_id == "r1"


@pytest.mark.asyncio
async def test_at_pull_contact_none_when_empty(monkeypatch):
    monkeypatch.setattr(settings, "attio_access_token", "TOK", raising=False)

    def handler(request):
        return httpx.Response(200, json={"data": []})

    res = await attio_mod.pull_contact(email="x@y.com", client=_client(handler))
    assert res is None
