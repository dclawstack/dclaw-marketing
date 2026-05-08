import enum
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Float, ForeignKey, DateTime, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class EventType(str, enum.Enum):
    impression = "impression"
    click = "click"
    conversion = "conversion"
    bounce = "bounce"


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    campaign_id: Mapped[UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[EventType] = mapped_column(SQLEnum(EventType), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    campaign: Mapped["Campaign"] = relationship(
        "Campaign", back_populates="analytics_events", lazy="selectin"
    )
