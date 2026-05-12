"""CRM sync adapters (Phase 8.6+).

Two-way sync between DClaw's internal ``Lead`` (with Phase 8.5 fields)
and the customer's external CRM (HubSpot, Salesforce, Pipedrive, Attio).

All adapters follow the same shape:

  • ``push_lead(lead, ...) -> CRMSyncResult``  outbound
  • ``pull_contact(email, ...) -> CRMSyncResult | None``  inbound

The ``CRMSyncResult`` carries the provider's external id + the
normalised field map so callers can reconcile against ``Lead`` (and
write a ``LeadActivity(kind=crm_sync)`` row to audit the call).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class CRMSyncResult:
    provider: str
    external_id: str
    """Provider's id for the contact (HubSpot id, Salesforce Id, etc.)."""
    email: str | None
    properties: dict = field(default_factory=dict)
    """Normalised key-value map of the contact's CRM fields."""
    raw: dict = field(default_factory=dict)
    """Full provider response for audit."""
    stub: bool = False


__all__ = ["CRMSyncResult"]
