"""Salesforce CRM sync adapter — Phase 8.7.

Two-way sync between our ``Lead`` and Salesforce's Lead object via
the REST v60 API:

  GET  /services/data/v60.0/query/?q=SELECT … WHERE Email='…'   — search
  POST /services/data/v60.0/sobjects/Lead/                       — create
  PATCH /services/data/v60.0/sobjects/Lead/{id}                  — update

Auth: Bearer access_token from Salesforce OAuth (username + password
or refresh-token flow). The Org's authenticated instance URL is
required (each Salesforce instance is on its own subdomain, e.g.
``mycompany.my.salesforce.com``).

Stub fallback when token / instance_url missing.
"""

from __future__ import annotations

import hashlib

import httpx

from app.core.config import settings
from app.services.crm import CRMSyncResult


_API_VERSION = "v60.0"


class SalesforceAuthError(RuntimeError):
    pass


class SalesforceSyncError(RuntimeError):
    pass


# Lead → Salesforce Lead object field map.
LEAD_TO_SALESFORCE: dict[str, str] = {
    "email": "Email",
    "first_name": "FirstName",
    "last_name": "LastName",
    "company": "Company",
    "phone": "Phone",
    "linkedin_url": "LinkedIn_URL__c",  # custom field; can be overridden
}


def _stub_result(email: str | None) -> CRMSyncResult:
    digest = hashlib.sha256(
        (email or "").encode("utf-8")
    ).hexdigest()[:18]
    return CRMSyncResult(
        provider="salesforce",
        external_id=f"sf_stub_{digest}",
        email=email,
        properties={"Email": email} if email else {},
        raw={"stub": True},
        stub=True,
    )


def _lead_to_properties(lead_dict: dict) -> dict:
    """Map our Lead fields to Salesforce Lead object fields.

    Salesforce requires LastName on every Lead — we fall back to
    "(unknown)" if it's missing so the call still succeeds (matches
    Salesforce's own validation behaviour).
    """
    out: dict = {}
    for lead_key, sf_field in LEAD_TO_SALESFORCE.items():
        v = lead_dict.get(lead_key)
        if v is not None and v != "":
            out[sf_field] = v
    # Salesforce requires LastName + Company on a Lead. Inject sensible
    # defaults so the API call doesn't 400.
    if "LastName" not in out:
        out["LastName"] = "(unknown)"
    if "Company" not in out:
        out["Company"] = "(unknown)"
    return out


def _base_url() -> str:
    base = (settings.salesforce_instance_url or "").rstrip("/")
    return f"{base}/services/data/{_API_VERSION}"


def _auth_headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.salesforce_access_token}",
        "Content-Type": "application/json",
    }


async def push_lead(
    *,
    lead: dict,
    client: httpx.AsyncClient | None = None,
) -> CRMSyncResult:
    """Creates or updates a Salesforce Lead from our Lead dict.

    Idempotency: SOQL-search by email; if found patch, else create.
    """
    email = lead.get("email")
    if not email:
        raise SalesforceSyncError("push_lead requires lead.email")
    if not settings.salesforce_access_token or not settings.salesforce_instance_url:
        return _stub_result(email)

    base = _base_url()
    headers = _auth_headers()
    props = _lead_to_properties(lead)

    owns_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=30.0)
        owns_client = True

    try:
        # 1. Search by email via SOQL.
        soql = f"SELECT Id, Email FROM Lead WHERE Email = '{email}' LIMIT 1"
        search = await client.get(
            f"{base}/query/", headers=headers, params={"q": soql}
        )
        if search.status_code in (401, 403):
            raise SalesforceAuthError(
                f"query {search.status_code}: {search.text[:200]}"
            )
        if search.status_code != 200:
            raise SalesforceSyncError(
                f"query {search.status_code}: {search.text[:200]}"
            )
        records = (search.json() or {}).get("records") or []

        if records:
            existing_id = records[0]["Id"]
            patch = await client.patch(
                f"{base}/sobjects/Lead/{existing_id}",
                json=props,
                headers=headers,
            )
            if patch.status_code in (401, 403):
                raise SalesforceAuthError(
                    f"patch {patch.status_code}: {patch.text[:200]}"
                )
            if patch.status_code not in (200, 204):
                raise SalesforceSyncError(
                    f"patch {patch.status_code}: {patch.text[:200]}"
                )
            sf_id = existing_id
            data = {"id": existing_id, "patched": True, "properties": props}
        else:
            create = await client.post(
                f"{base}/sobjects/Lead/", json=props, headers=headers
            )
            if create.status_code in (401, 403):
                raise SalesforceAuthError(
                    f"create {create.status_code}: {create.text[:200]}"
                )
            if create.status_code not in (200, 201):
                raise SalesforceSyncError(
                    f"create {create.status_code}: {create.text[:200]}"
                )
            data = create.json() or {}
            sf_id = data.get("id", "")
    finally:
        if owns_client:
            await client.aclose()

    return CRMSyncResult(
        provider="salesforce",
        external_id=str(sf_id),
        email=email,
        properties=props,
        raw=data,
    )


async def pull_contact(
    *,
    email: str,
    client: httpx.AsyncClient | None = None,
) -> CRMSyncResult | None:
    """Returns None when not found."""
    if not settings.salesforce_access_token or not settings.salesforce_instance_url:
        return None

    base = _base_url()
    headers = _auth_headers()
    fields = ", ".join(sorted(set(LEAD_TO_SALESFORCE.values()) | {"Id"}))
    soql = f"SELECT {fields} FROM Lead WHERE Email = '{email}' LIMIT 1"

    owns_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=30.0)
        owns_client = True

    try:
        resp = await client.get(
            f"{base}/query/", headers=headers, params={"q": soql}
        )
        if resp.status_code in (401, 403):
            raise SalesforceAuthError(
                f"query {resp.status_code}: {resp.text[:200]}"
            )
        if resp.status_code != 200:
            raise SalesforceSyncError(
                f"query {resp.status_code}: {resp.text[:200]}"
            )
        records = (resp.json() or {}).get("records") or []
    finally:
        if owns_client:
            await client.aclose()

    if not records:
        return None
    row = records[0]
    return CRMSyncResult(
        provider="salesforce",
        external_id=str(row.get("Id", "")),
        email=email,
        properties={k: row.get(k) for k in LEAD_TO_SALESFORCE.values() if k in row},
        raw=row,
    )


__all__ = [
    "push_lead",
    "pull_contact",
    "SalesforceAuthError",
    "SalesforceSyncError",
    "LEAD_TO_SALESFORCE",
]
