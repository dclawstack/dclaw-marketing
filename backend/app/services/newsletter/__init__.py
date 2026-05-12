"""Newsletter adapters — bulk email-list providers (Phase 7.5+).

Distinct from transactional ESPs (Resend / SendGrid / Postmark in
``app.services.email_send``) — newsletter providers manage audience
lists + design campaigns + handle unsubscribes per CAN-SPAM.

Adapters in this package:

  • mailchimp  (Phase 7.5)   — Mailchimp Marketing API v3
  • convertkit (Phase 7.6)   — ConvertKit v3
  • beehiiv    (Phase 7.6)   — Beehiiv v2

All follow the same shape:

  • Single async ``send_campaign(...)``
  • Returns a normalised ``NewsletterResult`` dataclass
  • Stub fallback when no key — emits a synthetic id so the rest of
    the pipeline (campaign status, cost ledger, audit) still works.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NewsletterResult:
    provider: str
    campaign_id: str
    recipient_count: int | None
    raw: dict


__all__ = ["NewsletterResult"]
