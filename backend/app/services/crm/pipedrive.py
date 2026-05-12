"""Pipedrive CRM sync adapter — Phase 8.x.

Two-way sync between our ``Lead`` and Pipedrive's Person object.

Endpoints (Pipedrive uses ``api_token`` query-param auth, not OAuth):

  GET    /v1/persons/search?term={email}&fields=email&exact_match=true
  POST   /v1/persons         — create
  PUT    /v1/persons/{id}    — update

Pipedrive doesn't model email/phone as flat strings — they are arrays
of objects (``[{"value": "...", "primary": true}]``). The mapping
helper handles that.
"""

from __future__ import annotations

import hashlib
from typing import Any

import httpx

from app.core.config import settings
from app.services.crm import CRMSyncResult


_BASE = "https://api.pipedrive.com"


class PipedriveAuthError(RuntimeError):
    pass


class PipedriveSyncError(RuntimeError):
    pass


def _stub_result(email: str | None) -> CRMSyncResult:
    digest = hashlib.sha256(
        (email or "").encode("utf-8")
    ).hexdigest()[:18]
    return CRMSyncResult(
        provider="pipedrive",
        external_id=f"pd_stub_{digest}",
        email=email,
        properties={"email": email} if email else {},
        raw={"stub": True},
        stub=True,
    )


def _lead_to_pd_payload(lead: dict) -> dict[str, Any]:
    """Map our Lead dict to a Pipedrive person payload.

    Pipedrive wraps email + phone as arrays of {value, primary, label}.
    """
    first = (lead.get("first_name") or "").strip()
    last = (lead.get("last_name") or "").strip()
    name = " ".join(p for p in (first, last) if p) or (lead.get("email") or "Unknown")
    payload: dict[str, Any] = {"name": name}
    if email := lead.get("email"):
        payload["email"] = [{"value": email, "primary": True, "label": "work"}]
    if phone := lead.get("phone"):
        payload["phone"] = [{"value": phone, "primary": True, "label": "work"}]
    if company := lead.get("company"):
        payload["org_id"] = None  # caller would resolve to org id later
        payload["org_name"] = company  # informational; Pipedrive ignores on create
    return payload


async def push_lead(
    *,
    lead: dict,
    client: httpx.AsyncClient | None = None,
) -> CRMSyncResult:
    """Create or update a Pipedrive person, keyed by email."""
    email = lead.get("email")
    if not email:
        raise PipedriveSyncError("push_lead requires lead.email")
    if not settings.pipedrive_api_token:
        return _stub_result(email)

    token = settings.pipedrive_api_token
    payload = _lead_to_pd_payload(lead)

    owns_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=30.0)
        owns_client = True

    try:
        # 1. Search for existing person by email
        search = await client.get(
            f"{_BASE}/v1/persons/search",
            params={
                "term": email,
                "fields": "email",
                "exact_match": "true",
                "api_token": token,
            },
        )
        if search.status_code in (401, 403):
            raise PipedriveAuthError(
                f"search {search.status_code}: {search.text[:200]}"
            )
        if search.status_code != 200:
            raise PipedriveSyncError(
                f"search {search.status_code}: {search.text[:200]}"
            )
        items = ((search.json() or {}).get("data") or {}).get("items") or []
        existing_id: int | None = None
        if items:
            item_payload = items[0].get("item") or {}
            existing_id = item_payload.get("id")

        if existing_id:
            resp = await client.put(
                f"{_BASE}/v1/persons/{existing_id}",
                params={"api_token": token},
                json=payload,
            )
        else:
            resp = await client.post(
                f"{_BASE}/v1/persons",
                params={"api_token": token},
                json=payload,
            )

        if resp.status_code in (401, 403):
            raise PipedriveAuthError(
                f"upsert {resp.status_code}: {resp.text[:200]}"
            )
        if resp.status_code not in (200, 201):
            raise PipedriveSyncError(
                f"upsert {resp.status_code}: {resp.text[:200]}"
            )
        body = resp.json() or {}
        data = body.get("data") or {}
    finally:
        if owns_client:
            await client.aclose()

    return CRMSyncResult(
        provider="pipedrive",
        external_id=str(data.get("id", "")),
        email=email,
        properties={
            "name": data.get("name"),
            "email": email,
            "phone": lead.get("phone"),
            "company": lead.get("company"),
        },
        raw=data,
    )


async def pull_contact(
    *,
    email: str,
    client: httpx.AsyncClient | None = None,
) -> CRMSyncResult | None:
    """Looks up a Pipedrive person by email. Returns None when missing."""
    if not settings.pipedrive_api_token:
        return None

    token = settings.pipedrive_api_token
    owns_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=30.0)
        owns_client = True

    try:
        resp = await client.get(
            f"{_BASE}/v1/persons/search",
            params={
                "term": email,
                "fields": "email",
                "exact_match": "true",
                "api_token": token,
            },
        )
        if resp.status_code in (401, 403):
            raise PipedriveAuthError(
                f"search {resp.status_code}: {resp.text[:200]}"
            )
        if resp.status_code != 200:
            raise PipedriveSyncError(
                f"search {resp.status_code}: {resp.text[:200]}"
            )
        items = ((resp.json() or {}).get("data") or {}).get("items") or []
    finally:
        if owns_client:
            await client.aclose()

    if not items:
        return None
    row = items[0].get("item") or {}
    return CRMSyncResult(
        provider="pipedrive",
        external_id=str(row.get("id", "")),
        email=email,
        properties={"name": row.get("name"), "email": email},
        raw=row,
    )


__all__ = [
    "push_lead",
    "pull_contact",
    "PipedriveAuthError",
    "PipedriveSyncError",
]
