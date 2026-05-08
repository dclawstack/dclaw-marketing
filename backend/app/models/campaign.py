import enum
from datetime import date
from uuid import UUID, uuid4

from sqlalchemy import String, Date, Float, Text, ForeignKey, Enum as SQLEnum
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
        "AnalyticsEvent", back_populates="campaign", lazy="selectin", cascade="all, delete-orphan"
    )
