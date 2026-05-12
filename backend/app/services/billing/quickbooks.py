"""QuickBooks Online invoice adapter — Phase 10.7.

Mirrors the Stripe adapter shape so callers can pick a provider with
a single field on the Invoice row. QuickBooks's API is REST + OAuth 2
bearer tokens; a realm_id (the company id) is required on every URL.

Flow (one POST per object, two passes total):

  1. POST /v3/company/{realm_id}/customer
       — ensure a Customer exists for the recipient email (search-then-
         create so it's idempotent on repeat calls).
  2. POST /v3/company/{realm_id}/invoice
       — create the invoice in one shot (QuickBooks doesn't require a
         separate finalize/send step; the SendInvoice endpoint is
         optional and triggers the email if invokes).
  3. POST /v3/company/{realm_id}/invoice?operation=send&sendTo=<email>
       — optional, only when send=True (default).

Auth: ``Authorization: Bearer <access_token>``. Tokens are 1-hour TTL
and rotate via a refresh-token; refresh handling belongs in the
OAuth-flow PR. Stub fallback when access_token or realm_id is missing.
"""

from __future__ import annotations

import hashlib

import httpx

from app.core.config import settings
from app.services.billing import InvoiceSendResult


_BASE = "https://quickbooks.api.intuit.com"
_MINOR_VERSION = "65"


class QuickBooksAuthError(RuntimeError):
    pass


class QuickBooksError(RuntimeError):
    pass


def _stub_result(invoice_number: str, amount_usd: float) -> InvoiceSendResult:
    digest = hashlib.sha256(
        f"{invoice_number}::{amount_usd:.2f}".encode("utf-8")
    ).hexdigest()[:18]
    return InvoiceSendResult(
        provider="quickbooks",
        external_id=f"qb_stub_{digest}",
        hosted_url=None,
        raw={
            "stub": True,
            "invoice_number": invoice_number,
            "amount_usd": amount_usd,
        },
        stub=True,
    )


def _find_or_create_customer(
    *,
    client: httpx.Client,
    realm_id: str,
    headers: dict[str, str],
    customer_name: str,
    email: str,
) -> str:
    """Return the QuickBooks Customer id, creating one if missing."""
    # Search by PrimaryEmailAddr.
    q = (
        f"SELECT Id FROM Customer WHERE PrimaryEmailAddr = '{email}'"
    )
    search_resp = client.get(
        f"{_BASE}/v3/company/{realm_id}/query",
        params={"query": q, "minorversion": _MINOR_VERSION},
        headers={**headers, "Accept": "application/json"},
    )
    if search_resp.status_code in (401, 403):
        raise QuickBooksAuthError(
            f"customer search {search_resp.status_code}: "
            f"{search_resp.text[:200]}"
        )
    if search_resp.status_code != 200:
        raise QuickBooksError(
            f"customer search {search_resp.status_code}: "
            f"{search_resp.text[:200]}"
        )
    rows = (
        (search_resp.json() or {}).get("QueryResponse") or {}
    ).get("Customer") or []
    if rows:
        return str(rows[0].get("Id"))

    # Create a new Customer.
    create_resp = client.post(
        f"{_BASE}/v3/company/{realm_id}/customer",
        params={"minorversion": _MINOR_VERSION},
        json={
            "DisplayName": customer_name or email,
            "PrimaryEmailAddr": {"Address": email},
        },
        headers={**headers, "Content-Type": "application/json"},
    )
    if create_resp.status_code in (401, 403):
        raise QuickBooksAuthError(
            f"customer create {create_resp.status_code}: "
            f"{create_resp.text[:200]}"
        )
    if create_resp.status_code not in (200, 201):
        raise QuickBooksError(
            f"customer create {create_resp.status_code}: "
            f"{create_resp.text[:200]}"
        )
    body = create_resp.json() or {}
    customer = body.get("Customer") or {}
    return str(customer.get("Id") or "")


def send_invoice(
    *,
    invoice_number: str,
    line_items: list[dict],
    customer_email: str,
    customer_name: str = "",
    realm_id: str | None = None,
    access_token: str | None = None,
    send: bool = True,
    client: httpx.Client | None = None,
) -> InvoiceSendResult:
    """Create + (optionally) send a QuickBooks invoice.

    Args:
        invoice_number: Our internal invoice number — copied to
            DocNumber on the QB invoice.
        line_items: List of dicts with keys:
            description: str
            quantity: float (optional, default 1)
            unit_price_usd: float
        customer_email: Required to look up / create the Customer.
        customer_name: DisplayName when creating a new customer.
        realm_id: QuickBooks company id. Falls back to
            ``settings.quickbooks_realm_id``.
        access_token: OAuth 2 bearer. Falls back to
            ``settings.quickbooks_access_token``.
        send: When True (default) also POST to the SendInvoice
            endpoint so QuickBooks emails the customer.

    Raises:
        QuickBooksAuthError: 401/403 on any sub-call.
        QuickBooksError: any other non-2xx.
    """
    token = access_token or settings.quickbooks_access_token
    realm = realm_id or settings.quickbooks_realm_id
    amount_total = sum(
        (item.get("quantity") or 1) * float(item.get("unit_price_usd") or 0)
        for item in line_items
    )
    if not (token and realm):
        return _stub_result(invoice_number, amount_total)

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }

    owns_client = False
    if client is None:
        client = httpx.Client(timeout=30.0)
        owns_client = True

    try:
        customer_id = _find_or_create_customer(
            client=client,
            realm_id=realm,
            headers=headers,
            customer_name=customer_name,
            email=customer_email,
        )

        # Build invoice body
        lines = []
        for item in line_items:
            qty = float(item.get("quantity") or 1)
            unit = float(item.get("unit_price_usd") or 0)
            lines.append(
                {
                    "DetailType": "SalesItemLineDetail",
                    "Amount": round(qty * unit, 2),
                    "Description": item.get("description") or "",
                    "SalesItemLineDetail": {
                        "Qty": qty,
                        "UnitPrice": unit,
                        "ItemRef": {"value": "1"},  # default item; agency edits in UI
                    },
                }
            )

        invoice_body = {
            "DocNumber": invoice_number,
            "CustomerRef": {"value": customer_id},
            "BillEmail": {"Address": customer_email},
            "Line": lines,
        }
        create = client.post(
            f"{_BASE}/v3/company/{realm}/invoice",
            params={"minorversion": _MINOR_VERSION},
            json=invoice_body,
            headers={**headers, "Content-Type": "application/json"},
        )
        if create.status_code in (401, 403):
            raise QuickBooksAuthError(
                f"invoice create {create.status_code}: "
                f"{create.text[:200]}"
            )
        if create.status_code not in (200, 201):
            raise QuickBooksError(
                f"invoice create {create.status_code}: "
                f"{create.text[:200]}"
            )
        invoice = (create.json() or {}).get("Invoice") or {}
        invoice_id = str(invoice.get("Id") or "")

        if send and invoice_id:
            send_resp = client.post(
                f"{_BASE}/v3/company/{realm}/invoice/{invoice_id}/send",
                params={
                    "sendTo": customer_email,
                    "minorversion": _MINOR_VERSION,
                },
                headers=headers,
            )
            if send_resp.status_code in (401, 403):
                raise QuickBooksAuthError(
                    f"invoice send {send_resp.status_code}: "
                    f"{send_resp.text[:200]}"
                )
            if send_resp.status_code not in (200, 201):
                raise QuickBooksError(
                    f"invoice send {send_resp.status_code}: "
                    f"{send_resp.text[:200]}"
                )
            invoice = (send_resp.json() or {}).get("Invoice") or invoice
    finally:
        if owns_client:
            client.close()

    return InvoiceSendResult(
        provider="quickbooks",
        external_id=invoice_id,
        hosted_url=None,  # QB doesn't surface a hosted-pay URL by default
        raw=invoice,
    )


__all__ = [
    "send_invoice",
    "QuickBooksAuthError",
    "QuickBooksError",
]
