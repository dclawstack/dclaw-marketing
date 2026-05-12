"""Generic webhook receiver + Automation rules (Theme D4 / Phase 6).

A ``Webhook`` is an inbound endpoint an Org has registered with an
external system (Calendly, HubSpot, Stripe, GitHub, …). Each Webhook
has a unique secret-token suffix in its URL — ``/api/v1/webhooks/generic/{token}`` —
which is the only thing the external system needs to know.

Every POST to that URL writes a ``WebhookEvent`` row. The
``Automation`` model is a rule that subscribes to a Webhook (or to a
specific event-source pattern) and, when matched, dispatches one or
more actions (queue a publish, enrich a lead, push to a CRM, run an
agent). The actions execute via a Celery task that consumes
unprocessed WebhookEvent rows.
"""

from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Webhook(Base):
    """A registered inbound webhook endpoint for an Org.

    ``token`` is the URL-safe identifier the external system POSTs to;
    ``secret`` is the optional HMAC secret used to verify the body
    signature (when the external system supports it).
    """

    __tablename__ = "webhooks"
    __table_args__ = (
        Index("ix_webhooks_token", "token", unique=True),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    """Optional free-form label of the external system (calendly,
    hubspot, stripe, github, …). Automations can filter on it."""

    token: Mapped[str] = mapped_column(String(64), nullable=False)
    secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    last_received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    received_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class WebhookEventStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    processed = "processed"
    failed = "failed"
    ignored = "ignored"


class WebhookEvent(Base):
    """One row per inbound POST. Automation runner reads these."""

    __tablename__ = "webhook_events"
    __table_args__ = (
        Index(
            "ix_webhook_events_status_received_at", "status", "received_at"
        ),
        Index("ix_webhook_events_webhook_id_received_at",
              "webhook_id", "received_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    webhook_id: Mapped[UUID] = mapped_column(
        ForeignKey("webhooks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    status: Mapped[WebhookEventStatus] = mapped_column(
        SQLEnum(WebhookEventStatus),
        default=WebhookEventStatus.pending,
        nullable=False,
    )
    matched_automation_ids: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)


class AutomationAction(str, enum.Enum):
    """Vocabulary of actions an Automation can dispatch when its
    filter matches an incoming event. The handler for each lives in
    the automation runner task — adding a new action means appending
    a value here + a branch in the runner."""

    create_lead = "create_lead"
    enrich_lead = "enrich_lead"
    push_to_crm = "push_to_crm"
    add_to_sequence = "add_to_sequence"
    schedule_post = "schedule_post"
    notify_slack = "notify_slack"
    log_only = "log_only"


class Automation(Base):
    """Rule that subscribes to a Webhook (or to a source pattern) and
    dispatches actions when matched.

    ``filter_json`` is a flat key/value match against the event's
    payload (top-level keys only, exact match). Empty/missing filter
    matches every event from the subscribed webhook(s).

    ``actions_json`` is a list of ``{"action": "...", "params": {...}}``
    objects executed in order.
    """

    __tablename__ = "automations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Either webhook_id (single source) OR source_filter (free-form),
    # OR both, OR neither (matches everything for the Org).
    webhook_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("webhooks.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    source_filter: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )

    filter_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    actions_json: Mapped[list | None] = mapped_column(JSON, nullable=True)

    created_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    last_matched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    match_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


__all__ = [
    "Webhook",
    "WebhookEvent",
    "WebhookEventStatus",
    "Automation",
    "AutomationAction",
]
