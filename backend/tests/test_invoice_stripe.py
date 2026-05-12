"""Phase 10.6 — Invoice model + Stripe adapter unit tests."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from uuid import uuid4
from urllib.parse import parse_qs

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.invoice import Invoice, InvoiceLineItem, InvoiceStatus
from app.models.organization import Organization
from app.services.billing import stripe as stripe_svc
from app.services.billing.stripe import (
    StripeAuthError,
    StripeError,
    send_invoice,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


# ===== Model tests =====


@pytest.fixture()
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _org(s: Session) -> Organization:
    o = Organization(slug=f"o-{uuid4().hex[:8]}", name="Agency", is_external=False)
    s.add(o)
    s.commit()
    s.refresh(o)
    return o


def test_invoice_defaults(session: Session):
    org = _org(session)
    inv = Invoice(
        organization_id=org.id,
        invoice_number="INV-2026-001",
    )
    session.add(inv)
    session.commit()
    session.refresh(inv)
    assert inv.status == InvoiceStatus.draft
    assert inv.currency == "USD"
    assert inv.subtotal_usd == 0.0
    assert inv.total_usd == 0.0
    assert inv.stripe_invoice_id is None
    assert inv.line_items == []


def test_invoice_with_line_items(session: Session):
    org = _org(session)
    inv = Invoice(
        organization_id=org.id,
        invoice_number="INV-2026-002",
        subtotal_usd=2000.0,
        tax_usd=200.0,
        total_usd=2200.0,
    )
    inv.line_items = [
        InvoiceLineItem(
            position=1,
            description="Strategy retainer",
            quantity=10.0,
            unit_price_usd=200.0,
            amount_usd=2000.0,
        )
    ]
    session.add(inv)
    session.commit()
    session.refresh(inv)
    assert len(inv.line_items) == 1
    assert inv.line_items[0].description == "Strategy retainer"
    assert inv.line_items[0].amount_usd == 2000.0


def test_invoice_status_transitions(session: Session):
    org = _org(session)
    inv = Invoice(organization_id=org.id, invoice_number="INV-001")
    session.add(inv)
    session.commit()

    inv.status = InvoiceStatus.open
    inv.due_at = datetime.now(tz=timezone.utc) + timedelta(days=30)
    session.commit()

    inv.status = InvoiceStatus.paid
    inv.paid_at = datetime.now(tz=timezone.utc)
    session.commit()

    fetched = session.get(Invoice, inv.id)
    assert fetched.status == InvoiceStatus.paid
    assert fetched.paid_at is not None


def test_unique_invoice_number_per_org(session: Session):
    org = _org(session)
    inv1 = Invoice(organization_id=org.id, invoice_number="INV-001")
    inv2 = Invoice(organization_id=org.id, invoice_number="INV-001")
    session.add_all([inv1, inv2])
    with pytest.raises(Exception):
        session.commit()


# ===== Stripe adapter tests =====


@pytest.mark.asyncio
async def test_stripe_stub_when_no_key(monkeypatch):
    monkeypatch.setattr(stripe_svc.settings, "stripe_secret_key", "")
    res = await send_invoice(
        invoice_number="INV-2026-001",
        customer_email="alice@example.com",
        customer_name="Alice",
        line_items=[
            {"description": "Retainer", "quantity": 10, "unit_price_usd": 200},
        ],
    )
    assert res.provider == "stripe"
    assert res.stub is True
    assert res.external_id.startswith("in_stub_")


@pytest.mark.asyncio
async def test_stripe_full_flow(monkeypatch):
    monkeypatch.setattr(stripe_svc.settings, "stripe_secret_key", "sk_test_x")
    calls = []

    def handler(request):
        path = request.url.path
        method = request.method
        calls.append(f"{method} {path}")
        if "/customers/search" in path:
            return httpx.Response(200, json={"data": []})
        if path == "/v1/customers":
            return httpx.Response(200, json={"id": "cus_1"})
        if path == "/v1/invoiceitems":
            return httpx.Response(200, json={"id": "ii_1"})
        if path == "/v1/invoices":
            return httpx.Response(200, json={"id": "in_1"})
        if path.endswith("/finalize"):
            return httpx.Response(200, json={"id": "in_1"})
        if path.endswith("/send"):
            return httpx.Response(
                200,
                json={
                    "id": "in_1",
                    "hosted_invoice_url": "https://invoice.stripe.com/i/abc",
                },
            )
        return httpx.Response(404, text=f"unexpected {path}")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    res = await send_invoice(
        invoice_number="INV-2026-001",
        customer_email="alice@example.com",
        customer_name="Alice",
        line_items=[
            {"description": "Retainer", "quantity": 10, "unit_price_usd": 200},
            {"description": "Ad spend", "quantity": 1, "unit_price_usd": 500},
        ],
        client=client,
    )
    await client.aclose()

    # 1 search + 1 customer + 2 invoiceitems + 1 invoice + finalize + send = 7
    assert "GET /v1/customers/search" in calls
    assert "POST /v1/customers" in calls
    assert calls.count("POST /v1/invoiceitems") == 2
    assert "POST /v1/invoices" in calls
    assert calls[-2].endswith("/finalize")
    assert calls[-1].endswith("/send")
    assert res.external_id == "in_1"
    assert res.hosted_url == "https://invoice.stripe.com/i/abc"


@pytest.mark.asyncio
async def test_stripe_reuses_existing_customer(monkeypatch):
    monkeypatch.setattr(stripe_svc.settings, "stripe_secret_key", "sk_x")
    calls = []

    def handler(request):
        path = request.url.path
        calls.append(f"{request.method} {path}")
        if "/customers/search" in path:
            return httpx.Response(
                200, json={"data": [{"id": "cus_existing"}]}
            )
        if path == "/v1/invoiceitems":
            return httpx.Response(200, json={"id": "ii_1"})
        if path == "/v1/invoices":
            return httpx.Response(200, json={"id": "in_x"})
        if path.endswith("/finalize") or path.endswith("/send"):
            return httpx.Response(200, json={"id": "in_x"})
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    await send_invoice(
        invoice_number="INV-002",
        customer_email="existing@example.com",
        customer_name=None,
        line_items=[{"description": "x", "quantity": 1, "unit_price_usd": 10}],
        client=client,
    )
    await client.aclose()
    # Customer create endpoint should NOT have been called
    assert "POST /v1/customers" not in calls


@pytest.mark.asyncio
async def test_stripe_401_raises_auth_error(monkeypatch):
    monkeypatch.setattr(stripe_svc.settings, "stripe_secret_key", "bad")

    def handler(request):
        if "/customers/search" in request.url.path:
            # search returns empty
            return httpx.Response(200, json={"data": []})
        return httpx.Response(401, text="invalid api key")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with pytest.raises(StripeAuthError):
        await send_invoice(
            invoice_number="INV-X",
            customer_email="a@x.io",
            customer_name=None,
            line_items=[{"description": "x", "quantity": 1, "unit_price_usd": 10}],
            client=client,
        )
    await client.aclose()


@pytest.mark.asyncio
async def test_stripe_requires_line_items(monkeypatch):
    monkeypatch.setattr(stripe_svc.settings, "stripe_secret_key", "k")
    with pytest.raises(StripeError, match="line item"):
        await send_invoice(
            invoice_number="X",
            customer_email="a@x.io",
            customer_name=None,
            line_items=[],
        )


@pytest.mark.asyncio
async def test_stripe_invoiceitem_amount_in_cents(monkeypatch):
    monkeypatch.setattr(stripe_svc.settings, "stripe_secret_key", "k")
    captured = []

    def handler(request):
        path = request.url.path
        if "/customers/search" in path:
            return httpx.Response(200, json={"data": [{"id": "cus_1"}]})
        if path == "/v1/invoiceitems":
            captured.append(request.content.decode("utf-8"))
            return httpx.Response(200, json={"id": "ii"})
        if path == "/v1/invoices":
            return httpx.Response(200, json={"id": "in_1"})
        if path.endswith("/finalize") or path.endswith("/send"):
            return httpx.Response(200, json={"id": "in_1"})
        return httpx.Response(404)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    await send_invoice(
        invoice_number="X",
        customer_email="a@x.io",
        customer_name=None,
        line_items=[{"description": "x", "quantity": 2, "unit_price_usd": 199.99}],
        client=client,
    )
    await client.aclose()

    # 2 * 199.99 = $399.98 = 39998 cents
    parsed = parse_qs(captured[0])
    assert parsed["amount"] == ["39998"]
