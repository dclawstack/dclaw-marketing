"""EmailEvent — inbound provider webhook events (Phase 7.4).

Every signed webhook from Resend / SendGrid / Postmark / Mailchimp /
ConvertKit / Beehiiv lands as one row in this table. The
event-to-LeadActivity bridge (which writes ``LeadActivity(kind=email_*)``
rows when a Lead can be resolved) is handled in the route, not the
model, so this table stays a pure audit log of provider deliveries.
"""

from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EmailEventProvider(str, enum.Enum):
    resend = "resend"
    sendgrid = "sendgrid"
    postmark = "postmark"
    mailchimp = "mailchimp"
    convertkit = "convertkit"
    beehiiv = "beehiiv"


class EmailEventKind(str, enum.Enum):
    delivered = "delivered"
    opened = "opened"
    clicked = "clicked"
    replied = "replied"
    bounced = "bounced"
    complained = "complained"
    unsubscribed = "unsubscribed"
    failed = "failed"
    other = "other"


class EmailEvent(Base):
    __tablename__ = "email_events"
    __table_args__ = (
        Index("ix_email_events_org_kind_occ", "organization_id", "kind", "occurred_at"),
        Index("ix_email_events_recipient", "recipient"),
        Index("ix_email_events_provider_message_id", "provider", "provider_message_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    provider: Mapped[EmailEventProvider] = mapped_column(
        SQLEnum(EmailEventProvider), nullable=False
    )
    kind: Mapped[EmailEventKind] = mapped_column(
        SQLEnum(EmailEventKind), nullable=False
    )
    provider_message_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    recipient: Mapped[str | None] = mapped_column(String(320), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    lead_activity_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("lead_activities.id", ondelete="SET NULL"),
        nullable=True,
    )
