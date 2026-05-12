"""Billing adapters — invoice generation + collection (Phase 10.6+).

Currently:
  • stripe  (Phase 10.6) — invoice creation + finalize + send

Future:
  • quickbooks (Phase 10.7) — invoice creation + sync
  • paypal     (planned)    — payment links
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InvoiceSendResult:
    provider: str
    external_id: str
    """Provider's invoice id (e.g. Stripe ``in_1xxx``)."""
    hosted_url: str | None
    """URL the customer can use to pay / view, if the provider gave us one."""
    raw: dict
    stub: bool = False


__all__ = ["InvoiceSendResult"]
