"""Phase 7 — Email + Ads + Sequences data layer (Themes C3, C4, E4).

Scaffolding only — provider adapters (Resend / SendGrid / Mailchimp /
Meta Ads / Google Ads / LinkedIn Ads / TikTok Ads) and the sequence-
runner Celery task ship in follow-ups.
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
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


# ---------- Email ----------------------------------------------------------


class EmailTemplate(Base):
    __tablename__ = "email_templates"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "slug", name="uq_email_template_org_slug"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(998), nullable=False)
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    merge_fields: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    created_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
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


class EmailCampaignStatus(str, enum.Enum):
    draft = "draft"
    scheduled = "scheduled"
    sending = "sending"
    sent = "sent"
    failed = "failed"
    cancelled = "cancelled"


class EmailCampaign(Base):
    """A one-shot broadcast email (vs. an EmailSequence which is multi-step)."""

    __tablename__ = "email_campaigns"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    template_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("email_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    segment_id: Mapped[UUID | None] = mapped_column(
        nullable=True
    )  # FK added when Segment model lands

    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sent_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    open_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    click_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    bounce_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )

    status: Mapped[EmailCampaignStatus] = mapped_column(
        SQLEnum(EmailCampaignStatus),
        nullable=False,
        default=EmailCampaignStatus.draft,
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


class SequenceStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    paused = "paused"
    archived = "archived"


class EmailSequence(Base):
    """Multi-step automation. Steps are EmailSequenceStep rows."""

    __tablename__ = "email_sequences"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[SequenceStatus] = mapped_column(
        SQLEnum(SequenceStatus),
        nullable=False,
        default=SequenceStatus.draft,
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


class SequenceStepKind(str, enum.Enum):
    email = "email"
    wait = "wait"
    branch = "branch"
    linkedin_dm = "linkedin_dm"
    webhook = "webhook"


class EmailSequenceStep(Base):
    __tablename__ = "email_sequence_steps"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    sequence_id: Mapped[UUID] = mapped_column(
        ForeignKey("email_sequences.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    position: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[SequenceStepKind] = mapped_column(
        SQLEnum(SequenceStepKind), nullable=False
    )
    template_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("email_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    delay_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    config_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


# ---------- Ads ----------------------------------------------------------


class AdPlatform(str, enum.Enum):
    meta = "meta"
    google = "google"
    linkedin = "linkedin"
    tiktok = "tiktok"
    x = "x"


class AdStatus(str, enum.Enum):
    draft = "draft"
    pending_review = "pending_review"
    active = "active"
    paused = "paused"
    rejected = "rejected"
    completed = "completed"


class AdAccount(Base):
    """A connected ad-platform account (separate from SocialAccount)."""

    __tablename__ = "ad_accounts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform: Mapped[AdPlatform] = mapped_column(
        SQLEnum(AdPlatform), nullable=False
    )
    platform_account_id: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    connection_id: Mapped[UUID | None] = mapped_column(
        nullable=True
    )  # FK to Connection added once Phase 6 merges

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AdCampaign(Base):
    __tablename__ = "ad_campaigns"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ad_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("ad_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    objective: Mapped[str | None] = mapped_column(String(64), nullable=True)
    daily_budget_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_budget_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[AdStatus] = mapped_column(
        SQLEnum(AdStatus),
        nullable=False,
        default=AdStatus.draft,
    )
    start_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    end_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
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


class AdSet(Base):
    """An ad set — targeting + budget within a campaign."""

    __tablename__ = "ad_sets"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    ad_campaign_id: Mapped[UUID] = mapped_column(
        ForeignKey("ad_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    targeting_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    daily_budget_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[AdStatus] = mapped_column(
        SQLEnum(AdStatus),
        nullable=False,
        default=AdStatus.draft,
    )
    creative_asset_ids: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


# ---------- Segment ---------------------------------------------------------


class Segment(Base):
    """Saved filter — used by both EmailCampaign targeting and Ads
    Custom Audience syncs.
    """

    __tablename__ = "segments"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "slug", name="uq_segment_org_slug"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    filter_dsl_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    last_evaluated_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    last_evaluated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
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
