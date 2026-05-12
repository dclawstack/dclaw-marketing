"""HubSpot CRM sync adapter — Phase 8.6.

Two-way sync between our ``Lead`` and HubSpot's Contact object.

Endpoints:
  POST   /crm/v3/objects/contacts                — create
  PATCH  /crm/v3/objects/contacts/{id}           — update
  GET    /crm/v3/objects/contacts/{id}           — read
  GET    /crm/v3/objects/contacts/search         — find by email

Auth: Bearer private-app token in Authorization header.

Stub fallback when no token. Field mapping is intentionally minimal —
agencies can extend by editing ``LEAD_TO_HUBSPOT`` below.
"""

from __future__ import annotations

import hashlib
from typing import Any

import httpx

from app.core.config import settings
from app.services.crm import CRMSyncResult


_BASE = "https://api.hubapi.com"


class HubSpotAuthError(RuntimeError):
    pass


class HubSpotSyncError(RuntimeError):
    pass


# Lead → HubSpot property mapping. HubSpot uses snake_case internal
# names; "firstname"/"lastname" (not first_name) are the defaults.
LEAD_TO_HUBSPOT: dict[str, str] = {
    "email": "email",
    "first_name": "firstname",
    "last_name": "lastname",
    "company": "company",
    "phone": "phone",
    "linkedin_url": "linkedinbio",
}


def _stub_result(email: str | None) -> CRMSyncResult:
    digest = hashlib.sha256(
        (email or "").encode("utf-8")
    ).hexdigest()[:18]
    return CRMSyncResult(
        provider="hubspot",
        external_id=f"hs_stub_{digest}",
        email=email,
        properties={"email": email} if email else {},
        raw={"stub": True},
        stub=True,
    )


def _lead_to_properties(lead_dict: dict) -> dict[str, Any]:
    """Map our Lead fields to HubSpot property names. Caller passes
    a plain dict (not the ORM object) so this is unit-testable.
    """
    out: dict[str, Any] = {}
    for lead_key, hs_key in LEAD_TO_HUBSPOT.items():
        v = lead_dict.get(lead_key)
        if v is not None and v != "":
            out[hs_key] = v
    return out


async def push_lead(
    *,
    lead: dict,
    client: httpx.AsyncClient | None = None,
) -> CRMSyncResult:
    """Creates or updates a HubSpot contact from our Lead dict.

    Uses email as the idempotency key — searches first; if found,
    patches; if not, creates.
    """
    email = lead.get("email")
    if not email:
        raise HubSpotSyncError("push_lead requires lead.email")
    if not settings.hubspot_access_token:
        return _stub_result(email)

    headers = {
        "Authorization": f"Bearer {settings.hubspot_access_token}",
        "Content-Type": "application/json",
    }
    props = _lead_to_properties(lead)

    owns_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=30.0)
        owns_client = True

    try:
        # 1. Search for existing by email
        search = await client.post(
            f"{_BASE}/crm/v3/objects/contacts/search",
            json={
                "filterGroups": [
                    {
                        "filters": [
                            {
                                "propertyName": "email",
                                "operator": "EQ",
                                "value": email,
                            }
                        ]
                    }
                ],
                "limit": 1,
            },
            headers=headers,
        )
        if search.status_code in (401, 403):
            raise HubSpotAuthError(
                f"search {search.status_code}: {search.text[:200]}"
            )
        if search.status_code != 200:
            raise HubSpotSyncError(
                f"search {search.status_code}: {search.text[:200]}"
            )
        results = (search.json() or {}).get("results") or []

        if results:
            # Patch existing
            existing_id = results[0]["id"]
            resp = await client.patch(
                f"{_BASE}/crm/v3/objects/contacts/{existing_id}",
                json={"properties": props},
                headers=headers,
            )
            if resp.status_code in (401, 403):
                raise HubSpotAuthError(
                    f"patch {resp.status_code}: {resp.text[:200]}"
                )
            if resp.status_code != 200:
                raise HubSpotSyncError(
                    f"patch {resp.status_code}: {resp.text[:200]}"
                )
            data = resp.json()
        else:
            # Create
            resp = await client.post(
                f"{_BASE}/crm/v3/objects/contacts",
                json={"properties": props},
                headers=headers,
            )
            if resp.status_code in (401, 403):
                raise HubSpotAuthError(
                    f"create {resp.status_code}: {resp.text[:200]}"
                )
            if resp.status_code not in (200, 201):
                raise HubSpotSyncError(
                    f"create {resp.status_code}: {resp.text[:200]}"
                )
            data = resp.json()
    finally:
        if owns_client:
            await client.aclose()

    return CRMSyncResult(
        provider="hubspot",
        external_id=str(data.get("id", "")),
        email=email,
        properties=data.get("properties", {}),
        raw=data,
    )


async def pull_contact(
    *,
    email: str,
    client: httpx.AsyncClient | None = None,
) -> CRMSyncResult | None:
    """Looks up a HubSpot contact by email. Returns None if not found.

    Useful for the inbound side of two-way sync — pulling fresh
    HubSpot data into our LeadActivity timeline.
    """
    if not settings.hubspot_access_token:
        return None

    headers = {
        "Authorization": f"Bearer {settings.hubspot_access_token}",
        "Content-Type": "application/json",
    }

    owns_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=30.0)
        owns_client = True

    try:
        resp = await client.post(
            f"{_BASE}/crm/v3/objects/contacts/search",
            json={
                "filterGroups": [
                    {
                        "filters": [
                            {
                                "propertyName": "email",
                                "operator": "EQ",
                                "value": email,
                            }
                        ]
                    }
                ],
                "properties": list(LEAD_TO_HUBSPOT.values()),
                "limit": 1,
            },
            headers=headers,
        )
        if resp.status_code in (401, 403):
            raise HubSpotAuthError(
                f"search {resp.status_code}: {resp.text[:200]}"
            )
        if resp.status_code != 200:
            raise HubSpotSyncError(
                f"search {resp.status_code}: {resp.text[:200]}"
            )
        results = (resp.json() or {}).get("results") or []
    finally:
        if owns_client:
            await client.aclose()

    if not results:
        return None
    row = results[0]
    return CRMSyncResult(
        provider="hubspot",
        external_id=str(row.get("id", "")),
        email=email,
        properties=row.get("properties", {}),
        raw=row,
    )


__all__ = [
    "push_lead",
    "pull_contact",
    "HubSpotAuthError",
    "HubSpotSyncError",
    "LEAD_TO_HUBSPOT",
]
