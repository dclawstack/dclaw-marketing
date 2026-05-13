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
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class LeadStatus(str, enum.Enum):
    new = "new"
    contacted = "contacted"
    qualified = "qualified"
    converted = "converted"
    lost = "lost"


class LeadStage(str, enum.Enum):
    """Marketing-funnel stage — separate from operational LeadStatus."""
    visitor = "visitor"
    new = "new"
    mql = "mql"
    sql = "sql"
    customer = "customer"
    churned = "churned"


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Tenancy (A1). Nullable in v1.0.0 — see Campaign for rationale.
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    first_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[LeadStatus] = mapped_column(
        SQLEnum(LeadStatus), nullable=False, default=LeadStatus.new
    )
    campaign_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True
    )

    # ---------- Phase 8.5 — Lead 2.0 extensions ----------

    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    linkedin_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Marketing-funnel stage (separate from operational `status`)
    stage: Mapped[LeadStage] = mapped_column(
        SQLEnum(LeadStage), nullable=False, default=LeadStage.new, index=True
    )

    # Score: 0–100 product / sales hand-off threshold
    score: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)

    # Enrichment payload (Apollo / Clearbit / PDL response)
    enrichment_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # UTM attribution dims captured at first touch
    utm_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(255), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(255), nullable=True)
    utm_content: Mapped[str | None] = mapped_column(String(255), nullable=True)
    utm_term: Mapped[str | None] = mapped_column(String(255), nullable=True)

    last_activity_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )

    campaign: Mapped["Campaign | None"] = relationship(
        "Campaign", back_populates="leads", lazy="selectin"
    )
    activities: Mapped[list["LeadActivity"]] = relationship(
        "LeadActivity",
        back_populates="lead",
        cascade="all, delete-orphan",
        order_by="LeadActivity.occurred_at.desc()",
        lazy="selectin",
    )
    notes: Mapped[list["LeadNote"]] = relationship(
        "LeadNote",
        back_populates="lead",
        cascade="all, delete-orphan",
        order_by="LeadNote.created_at.desc()",
        lazy="selectin",
    )

    # Email is unique per-Org (not globally). Same email can exist in
    # multiple Orgs — agency-platform case where the same contact is
    # tracked across different clients.
    __table_args__ = (
        UniqueConstraint("organization_id", "email", name="uq_leads_org_email"),
    )


# ---------- Phase 8.5 — LeadActivity + LeadNote ----------


class LeadActivityKind(str, enum.Enum):
    """Type of activity recorded against a lead."""
    email_open = "email_open"
    email_click = "email_click"
    email_reply = "email_reply"
    page_view = "page_view"
    form_submit = "form_submit"
    call = "call"
    meeting = "meeting"
    note = "note"
    enrichment = "enrichment"
    crm_sync = "crm_sync"
    status_change = "status_change"
    stage_change = "stage_change"
    other = "other"


class LeadActivity(Base):
    """Timeline event on a Lead.

    Email opens / clicks / replies, page views, form submits, sales
    calls, meetings, enrichment hits, CRM sync results — anything the
    sales / marketing team or an agent wants to record.
    """

    __tablename__ = "lead_activities"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    lead_id: Mapped[UUID] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    kind: Mapped[LeadActivityKind] = mapped_column(
        SQLEnum(LeadActivityKind), nullable=False, index=True
    )
    summary: Mapped[str | None] = mapped_column(String(512), nullable=True)
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    lead: Mapped["Lead"] = relationship("Lead", back_populates="activities")


class LeadNote(Base):
    """Free-text annotation on a Lead — internal-only, not synced out."""

    __tablename__ = "lead_notes"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    lead_id: Mapped[UUID] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    author_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    body: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    lead: Mapped["Lead"] = relationship("Lead", back_populates="notes")
