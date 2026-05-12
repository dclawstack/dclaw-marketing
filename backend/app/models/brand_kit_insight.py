"""BrandKitInsight — KG write-back loop (Theme Q3 / §6.2).

After a campaign or agent run completes, the platform observes what
worked (high engagement, conversion lift) and what didn't, and writes
the lesson back to a BrandKitInsight row. The next agent run pulls
the top-K insights for the brand into its system prompt — so the
agents *learn* from outcomes instead of starting cold each time.

Insights are scoped to a BrandKit so different brands can carry
different lessons. ``kind`` identifies the lesson type
(``performance`` | ``voice`` | ``audience`` | ``hashtag`` |
``timing`` | ``other``). ``confidence`` is the system's stated
certainty in the lesson 0-1; the agent's system prompt only includes
insights above a per-Org floor (default 0.6).

Lifecycle:
  • Auto-written by Analyst Agent on weekly report (#174).
  • Editable / deletable by humans via the /orgs/[id]/brand/insights UI.
  • Pulled into BrandStyle composition (app.agents.brand_style) on
    every run.
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
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BrandKitInsightKind(str, enum.Enum):
    performance = "performance"
    voice = "voice"
    audience = "audience"
    hashtag = "hashtag"
    timing = "timing"
    other = "other"


class BrandKitInsight(Base):
    __tablename__ = "brand_kit_insights"
    __table_args__ = (
        Index(
            "ix_brand_kit_insights_brand_kit_kind_confidence",
            "brand_kit_id",
            "kind",
            "confidence",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    brand_kit_id: Mapped[UUID] = mapped_column(
        ForeignKey("brand_kits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    kind: Mapped[BrandKitInsightKind] = mapped_column(
        SQLEnum(BrandKitInsightKind),
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(String(512), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.7)

    source_run_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("workflow_runs.id", ondelete="SET NULL"),
        nullable=True,
    )
    generated_by_agent: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    is_human_edited: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_archived: Mapped[bool] = mapped_column(default=False, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


__all__ = ["BrandKitInsight", "BrandKitInsightKind"]
