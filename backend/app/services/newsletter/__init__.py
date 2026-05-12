"""Newsletter adapters — bulk email-list providers (Phase 7.5+).

Distinct from transactional ESPs (Resend / SendGrid / Postmark in
``app.services.email_send``) — newsletter providers manage audience
lists + design campaigns + handle unsubscribes per CAN-SPAM.

Adapters in this package:

  • mailchimp  (Phase 7.5)   — Mailchimp Marketing API v3
  • convertkit (planned)      — ConvertKit v3
  • beehiiv    (planned)      — Beehiiv v2
  • substack   (planned)      — Substack admin endpoints (no public API,
                                  uses RSS + webhooks for now)

All follow the same shape:

  • Single async ``send_campaign(api_key, list_id, subject, html, ...)``
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
    """Provider-issued id for the sent campaign."""
    recipient_count: int | None
    """Number of subscribers the campaign was sent to (None if unknown)."""
    raw: dict


__all__ = ["NewsletterResult"]
