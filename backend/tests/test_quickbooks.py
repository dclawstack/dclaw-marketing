"""Phase 10.7 — QuickBooks invoice adapter tests."""

from __future__ import annotations

import json

import httpx
import pytest
import pytest_asyncio

from app.core.config import settings
from app.services.billing.quickbooks import (
    QuickBooksAuthError,
    QuickBooksError,
    send_invoice,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def _set_creds(monkeypatch, *, token="TOK", realm="123456"):
    monkeypatch.setattr(
        settings, "quickbooks_access_token", token, raising=False
    )
    monkeypatch.setattr(
        settings, "quickbooks_realm_id", realm, raising=False
    )


def test_qb_stub_when_no_creds(monkeypatch):
    _set_creds(monkeypatch, token="", realm="")
    res = send_invoice(
        invoice_number="INV-001",
        line_items=[{"description": "x", "quantity": 1, "unit_price_usd": 10}],
        customer_email="a@b.com",
    )
    assert res.provider == "quickbooks"
    assert res.stub is True
    assert res.external_id.startswith("qb_stub_")


def test_qb_search_then_create_customer_then_invoice(monkeypatch):
    _set_creds(monkeypatch)
    calls: list = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        method = request.method
        calls.append((method, url, request.content.decode() if request.content else ""))
        if method == "GET" and "/query" in url:
            return httpx.Response(200, json={"QueryResponse": {}})
        if method == "POST" and url.endswith("/customer?minorversion=65"):
            return httpx.Response(
                201, json={"Customer": {"Id": "C_42", "DisplayName": "Acme"}}
            )
        if method == "POST" and "/invoice?minorversion=65" in url:
            body = json.loads(request.content.decode())
            assert body["DocNumber"] == "INV-001"
            assert body["CustomerRef"] == {"value": "C_42"}
            assert len(body["Line"]) == 2
            return httpx.Response(
                201, json={"Invoice": {"Id": "I_99", "DocNumber": "INV-001"}}
            )
        if method == "POST" and "/invoice/I_99/send" in url:
            return httpx.Response(
                200,
                json={"Invoice": {"Id": "I_99", "EmailStatus": "EmailSent"}},
            )
        return httpx.Response(404, text=f"unexpected {method} {url}")

    res = send_invoice(
        invoice_number="INV-001",
        line_items=[
            {"description": "Audit", "quantity": 1, "unit_price_usd": 100},
            {"description": "Setup fee", "quantity": 2, "unit_price_usd": 50},
        ],
        customer_email="acme@example.com",
        customer_name="Acme",
        client=_client(handler),
    )
    assert res.provider == "quickbooks"
    assert res.external_id == "I_99"
    assert calls[0][0] == "GET"  # search
    assert calls[1][0] == "POST"  # create customer
    assert calls[2][0] == "POST"  # invoice
    assert calls[3][0] == "POST"  # send


def test_qb_reuses_existing_customer(monkeypatch):
    _set_creds(monkeypatch)
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, str(request.url)))
        if request.method == "GET" and "/query" in str(request.url):
            return httpx.Response(
                200,
                json={
                    "QueryResponse": {
                        "Customer": [{"Id": "C_77", "DisplayName": "Existing"}]
                    }
                },
            )
        if request.method == "POST" and "/invoice?minorversion=65" in str(
            request.url
        ):
            return httpx.Response(201, json={"Invoice": {"Id": "I_2"}})
        if request.method == "POST" and "/send" in str(request.url):
            return httpx.Response(200, json={"Invoice": {"Id": "I_2"}})
        return httpx.Response(404)

    send_invoice(
        invoice_number="X",
        line_items=[{"description": "y", "unit_price_usd": 1}],
        customer_email="a@b.com",
        client=_client(handler),
    )
    # No POST /customer call — only the query.
    customer_calls = [c for c in calls if c[1].endswith("/customer?minorversion=65")]
    assert customer_calls == []


def test_qb_send_false_skips_send_call(monkeypatch):
    _set_creds(monkeypatch)
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if request.method == "GET":
            return httpx.Response(200, json={"QueryResponse": {}})
        if "customer?minorversion=65" in str(request.url):
            return httpx.Response(201, json={"Customer": {"Id": "C"}})
        return httpx.Response(201, json={"Invoice": {"Id": "I_5"}})

    res = send_invoice(
        invoice_number="X",
        line_items=[{"description": "y", "unit_price_usd": 1}],
        customer_email="a@b.com",
        send=False,
        client=_client(handler),
    )
    assert res.external_id == "I_5"
    assert not any("/send" in c for c in calls)


def test_qb_401_raises_auth_error(monkeypatch):
    _set_creds(monkeypatch)
    with pytest.raises(QuickBooksAuthError):
        send_invoice(
            invoice_number="X",
            line_items=[{"description": "y", "unit_price_usd": 1}],
            customer_email="a@b.com",
            client=_client(lambda r: httpx.Response(401, text="bad")),
        )


def test_qb_500_raises_error(monkeypatch):
    _set_creds(monkeypatch)
    with pytest.raises(QuickBooksError):
        send_invoice(
            invoice_number="X",
            line_items=[{"description": "y", "unit_price_usd": 1}],
            customer_email="a@b.com",
            client=_client(lambda r: httpx.Response(500, text="oops")),
        )
