"""Stripe invoice adapter — Phase 10.6.

Three-step flow:

  1. POST /v1/customers      → ensure a customer for the recipient email
                               (idempotent via email lookup)
  2. POST /v1/invoiceitems   → one per line item
  3. POST /v1/invoices       → create the invoice
  3b. POST /v1/invoices/{id}/finalize  → make it sendable
  3c. POST /v1/invoices/{id}/send      → email the hosted invoice page

Auth: Bearer secret key (``Authorization: Bearer sk_...``).

Stub fallback when no key.
"""

from __future__ import annotations

import hashlib
from urllib.parse import urlencode

import httpx

from app.core.config import settings
from app.services.billing import InvoiceSendResult


_BASE = "https://api.stripe.com"


class StripeAuthError(RuntimeError):
    pass


class StripeError(RuntimeError):
    pass


def _stub_result(invoice_number: str, amount_usd: float) -> InvoiceSendResult:
    digest = hashlib.sha256(
        (invoice_number + "::" + f"{amount_usd:.2f}").encode("utf-8")
    ).hexdigest()[:18]
    return InvoiceSendResult(
        provider="stripe",
        external_id=f"in_stub_{digest}",
        hosted_url=None,
        raw={
            "stub": True,
            "invoice_number": invoice_number,
            "total_usd": amount_usd,
        },
        stub=True,
    )


def _basic_headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.stripe_secret_key}",
        "Content-Type": "application/x-www-form-urlencoded",
    }


async def _ensure_customer(
    client: httpx.AsyncClient, email: str, name: str | None
) -> str:
    """Return a Stripe customer id, creating one if needed."""
    # Search by email
    search = await client.get(
        f"{_BASE}/v1/customers/search",
        headers=_basic_headers(),
        params={"query": f'email:"{email}"', "limit": 1},
    )
    if search.status_code == 200:
        results = (search.json() or {}).get("data") or []
        if results:
            return str(results[0]["id"])

    # Create
    body = {"email": email}
    if name:
        body["name"] = name
    create = await client.post(
        f"{_BASE}/v1/customers",
        headers=_basic_headers(),
        content=urlencode(body),
    )
    if create.status_code in (401, 403):
        raise StripeAuthError(
            f"customers {create.status_code}: {create.text[:200]}"
        )
    if create.status_code not in (200, 201):
        raise StripeError(
            f"customers {create.status_code}: {create.text[:200]}"
        )
    return str(create.json()["id"])


async def send_invoice(
    *,
    invoice_number: str,
    customer_email: str,
    customer_name: str | None,
    line_items: list[dict],
    currency: str = "usd",
    client: httpx.AsyncClient | None = None,
) -> InvoiceSendResult:
    """Pushes an invoice to Stripe and emails the hosted invoice page.

    Args:
        invoice_number: Our internal invoice number (e.g. INV-2026-001).
            Stripe stores it as ``custom_fields`` and we put it in
            ``metadata``.
        customer_email: The recipient.
        customer_name: Display name (optional).
        line_items: List of dicts with keys ``description`` (str),
            ``quantity`` (float), ``unit_price_usd`` (float).
        currency: ISO-4217 lowercase, default "usd".

    Returns:
        InvoiceSendResult with the Stripe invoice id and hosted URL.
    """
    if not settings.stripe_secret_key:
        total = sum(li["quantity"] * li["unit_price_usd"] for li in line_items)
        return _stub_result(invoice_number, total)
    if not line_items:
        raise StripeError("send_invoice requires at least one line item")

    owns_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=30.0)
        owns_client = True

    try:
        customer_id = await _ensure_customer(client, customer_email, customer_name)

        # Create invoice items
        for item in line_items:
            amount_cents = int(round(item["quantity"] * item["unit_price_usd"] * 100))
            body = {
                "customer": customer_id,
                "amount": str(amount_cents),
                "currency": currency,
                "description": item["description"],
            }
            resp = await client.post(
                f"{_BASE}/v1/invoiceitems",
                headers=_basic_headers(),
                content=urlencode(body),
            )
            if resp.status_code not in (200, 201):
                raise StripeError(
                    f"invoiceitems {resp.status_code}: {resp.text[:200]}"
                )

        # Create invoice
        create = await client.post(
            f"{_BASE}/v1/invoices",
            headers=_basic_headers(),
            content=urlencode(
                {
                    "customer": customer_id,
                    "collection_method": "send_invoice",
                    "days_until_due": "30",
                    "metadata[invoice_number]": invoice_number,
                }
            ),
        )
        if create.status_code not in (200, 201):
            raise StripeError(
                f"create {create.status_code}: {create.text[:200]}"
            )
        invoice_obj = create.json()
        stripe_id = invoice_obj["id"]

        # Finalize
        fin = await client.post(
            f"{_BASE}/v1/invoices/{stripe_id}/finalize",
            headers=_basic_headers(),
        )
        if fin.status_code not in (200, 201):
            raise StripeError(
                f"finalize {fin.status_code}: {fin.text[:200]}"
            )

        # Send (emails the customer the hosted invoice page)
        send = await client.post(
            f"{_BASE}/v1/invoices/{stripe_id}/send",
            headers=_basic_headers(),
        )
        if send.status_code not in (200, 201):
            raise StripeError(
                f"send {send.status_code}: {send.text[:200]}"
            )
        sent_obj = send.json()
        hosted_url = sent_obj.get("hosted_invoice_url")
    finally:
        if owns_client:
            await client.aclose()

    return InvoiceSendResult(
        provider="stripe",
        external_id=str(stripe_id),
        hosted_url=hosted_url,
        raw={
            "id": stripe_id,
            "hosted_invoice_url": hosted_url,
            "customer": customer_id,
        },
    )


__all__ = ["send_invoice", "StripeAuthError", "StripeError"]
