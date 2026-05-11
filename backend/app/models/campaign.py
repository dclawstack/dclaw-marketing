import enum
from datetime import date
from uuid import UUID, uuid4

from sqlalchemy import Date, Enum as SQLEnum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CampaignType(str, enum.Enum):
    email = "email"
    social = "social"
    ppc = "ppc"
    content = "content"


class CampaignStatus(str, enum.Enum):
    draft = "draft"
    scheduled = "scheduled"
    active = "active"
    paused = "paused"
    completed = "completed"


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    # Tenancy (A1). Nullable in v0.1.0 because the legacy v1 routes
    # (POST /api/v1/campaigns/) don't yet require Org/Project context.
    # Will tighten to NOT NULL in v0.2 once all routes are scoped under
    # /orgs/{org_id}/projects/{project_id}/.
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

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[CampaignType] = mapped_column(SQLEnum(CampaignType), nullable=False)
    status: Mapped[CampaignStatus] = mapped_column(
        SQLEnum(CampaignStatus), nullable=False, default=CampaignStatus.draft
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    leads: Mapped[list["Lead"]] = relationship(
        "Lead", back_populates="campaign", lazy="selectin", cascade="all, delete-orphan"
    )
    analytics_events: Mapped[list["AnalyticsEvent"]] = relationship(
        "AnalyticsEvent",
        back_populates="campaign",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
