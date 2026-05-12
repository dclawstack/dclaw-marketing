"""Attio CRM sync adapter — Phase 8.x.

Two-way sync between our ``Lead`` and Attio's People records.

Endpoints (Attio is OAuth2 bearer + an explicit ``assert_match`` upsert
mode that keys on a chosen attribute — we use the canonical
email_addresses attribute):

  PUT  /v2/objects/people/records?matching_attribute=email_addresses
       Body: {"data": {"values": {...}}}
       → 200 with upserted record
  POST /v2/objects/people/records/query
       Body: {"filter": {"email_addresses": {"$contains": "alice@x"}}}
       → 200 with {"data": [records]}

Attio attribute values are arrays of typed objects, e.g.:
  email_addresses: [{"email_address": "alice@x"}]
  name: [{"first_name": "Alice", "last_name": "Smith", "full_name": "Alice Smith"}]
"""

from __future__ import annotations

import hashlib
from typing import Any

import httpx

from app.core.config import settings
from app.services.crm import CRMSyncResult


_BASE = "https://api.attio.com"


class AttioAuthError(RuntimeError):
    pass


class AttioSyncError(RuntimeError):
    pass


def _stub_result(email: str | None) -> CRMSyncResult:
    digest = hashlib.sha256(
        (email or "").encode("utf-8")
    ).hexdigest()[:18]
    return CRMSyncResult(
        provider="attio",
        external_id=f"attio_stub_{digest}",
        email=email,
        properties={"email": email} if email else {},
        raw={"stub": True},
        stub=True,
    )


def _lead_to_attio_values(lead: dict) -> dict[str, Any]:
    """Map our Lead dict to Attio's array-of-typed-objects shape."""
    values: dict[str, Any] = {}
    if email := lead.get("email"):
        values["email_addresses"] = [{"email_address": email}]
    first = (lead.get("first_name") or "").strip()
    last = (lead.get("last_name") or "").strip()
    if first or last:
        full = " ".join(p for p in (first, last) if p)
        values["name"] = [
            {"first_name": first, "last_name": last, "full_name": full}
        ]
    if phone := lead.get("phone"):
        values["phone_numbers"] = [{"original_phone_number": phone}]
    if company := lead.get("company"):
        values["company_name"] = [{"value": company}]
    if linkedin := lead.get("linkedin_url"):
        values["linkedin"] = [{"value": linkedin}]
    return values


async def push_lead(
    *,
    lead: dict,
    client: httpx.AsyncClient | None = None,
) -> CRMSyncResult:
    """Upsert an Attio People record by email."""
    email = lead.get("email")
    if not email:
        raise AttioSyncError("push_lead requires lead.email")
    if not settings.attio_access_token:
        return _stub_result(email)

    headers = {
        "Authorization": f"Bearer {settings.attio_access_token}",
        "Content-Type": "application/json",
    }
    body = {"data": {"values": _lead_to_attio_values(lead)}}

    owns_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=30.0)
        owns_client = True

    try:
        resp = await client.put(
            f"{_BASE}/v2/objects/people/records",
            params={"matching_attribute": "email_addresses"},
            json=body,
            headers=headers,
        )
    finally:
        if owns_client:
            await client.aclose()

    if resp.status_code in (401, 403):
        raise AttioAuthError(f"upsert {resp.status_code}: {resp.text[:200]}")
    if resp.status_code not in (200, 201):
        raise AttioSyncError(f"upsert {resp.status_code}: {resp.text[:200]}")

    raw = resp.json() or {}
    data = raw.get("data") or {}
    record_id = ((data.get("id") or {}).get("record_id")) or ""
    return CRMSyncResult(
        provider="attio",
        external_id=str(record_id),
        email=email,
        properties=data.get("values") or {},
        raw=data,
    )


async def pull_contact(
    *,
    email: str,
    client: httpx.AsyncClient | None = None,
) -> CRMSyncResult | None:
    """Look up an Attio People record by email. Returns None if missing."""
    if not settings.attio_access_token:
        return None

    headers = {
        "Authorization": f"Bearer {settings.attio_access_token}",
        "Content-Type": "application/json",
    }
    body = {
        "filter": {"email_addresses": {"$contains": email}},
        "limit": 1,
    }

    owns_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=30.0)
        owns_client = True

    try:
        resp = await client.post(
            f"{_BASE}/v2/objects/people/records/query",
            json=body,
            headers=headers,
        )
    finally:
        if owns_client:
            await client.aclose()

    if resp.status_code in (401, 403):
        raise AttioAuthError(f"query {resp.status_code}: {resp.text[:200]}")
    if resp.status_code != 200:
        raise AttioSyncError(f"query {resp.status_code}: {resp.text[:200]}")
    rows = (resp.json() or {}).get("data") or []
    if not rows:
        return None
    row = rows[0]
    record_id = ((row.get("id") or {}).get("record_id")) or ""
    return CRMSyncResult(
        provider="attio",
        external_id=str(record_id),
        email=email,
        properties=row.get("values") or {},
        raw=row,
    )


__all__ = [
    "push_lead",
    "pull_contact",
    "AttioAuthError",
    "AttioSyncError",
]
