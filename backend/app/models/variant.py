"""B5 Variant A/B Studio (Sprint 3 / SP3-10).

A `VariantSet` groups N `Variant` rows that share a campaign slot and
a hypothesis. The scheduler reads the active variants' weights to
distribute traffic across them; the winner gets auto-promoted when
the user toggles it.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class VariantSetStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    paused = "paused"
    concluded = "concluded"


class VariantStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    winner = "winner"
    loser = "loser"


class VariantSet(Base):
    __tablename__ = "variant_sets"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    campaign_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True
    )

    slot: Mapped[str] = mapped_column(String(64), nullable=False)
    hypothesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[VariantSetStatus] = mapped_column(
        SQLEnum(VariantSetStatus),
        nullable=False,
        default=VariantSetStatus.draft,
    )
    auto_promote_winner: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="false"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class Variant(Base):
    __tablename__ = "variants"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    set_id: Mapped[UUID] = mapped_column(
        ForeignKey("variant_sets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    asset_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    status: Mapped[VariantStatus] = mapped_column(
        SQLEnum(VariantStatus), nullable=False, default=VariantStatus.active
    )
    # Optional outcome metrics for the auto-promote logic.
    metrics_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    impressions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conversions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


__all__ = ["VariantSet", "VariantSetStatus", "Variant", "VariantStatus"]
