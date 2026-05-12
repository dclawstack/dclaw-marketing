"""Phase 8 — Touchpoint + Conversion + AttributionResult.

Per IMPLEMENTATION-PLAN §Phase 8 / Theme E6. Promotes the analytics
event firehose into a real touchpoint table; a daily Celery job
correlates touchpoints into conversions using a selectable model
(first-touch / last-touch / linear / time-decay / Markov).

In v0 only the data model + endpoints land; the attribution job and
the per-model algorithms are a follow-up.
"""

from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AttributionModel(str, enum.Enum):
    first_touch = "first_touch"
    last_touch = "last_touch"
    linear = "linear"
    time_decay = "time_decay"
    markov = "markov"


class Touchpoint(Base):
    """A single interaction with the brand — page view, click, etc.

    Sourced from analytics_event ingestion or platform webhooks. The
    `lead_id` link is filled lazily by the identity-resolution job
    (Phase 8.x).
    """

    __tablename__ = "touchpoints"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    lead_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Source ingredients — agnostic to the producer (GA4, Mixpanel,
    # our own JS pixel, posthog, etc.).
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    channel: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    campaign_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # UTM-style attribution dims
    utm_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(255), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(255), nullable=True)
    utm_content: Mapped[str | None] = mapped_column(String(255), nullable=True)
    utm_term: Mapped[str | None] = mapped_column(String(255), nullable=True)

    page_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    referrer_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    visitor_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class Conversion(Base):
    """A revenue-bearing or qualifying event — booking, paid, MQL, etc."""

    __tablename__ = "conversions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lead_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    amount_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class AttributionResult(Base):
    """One row per (conversion × touchpoint × model) credit allocation.

    Recomputed daily by the attribution job. UI surfaces a Sankey
    using `weight` to size flows.
    """

    __tablename__ = "attribution_results"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    conversion_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    touchpoint_id: Mapped[UUID] = mapped_column(
        ForeignKey("touchpoints.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model: Mapped[AttributionModel] = mapped_column(
        SQLEnum(AttributionModel), nullable=False
    )
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    credited_amount_usd: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AnalyticsRollup(Base):
    """Daily rollup row — F1 unified analytics dashboard reads from here."""

    __tablename__ = "analytics_rollups"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scope: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )  # "org" | "project" | "campaign" | "channel"
    scope_key: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True
    )
    day: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    metric_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
