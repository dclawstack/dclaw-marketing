"""BrandKit — the workspace's design brain.

Logo + palette + fonts + voice tone sliders + do-say / don't-say lists
+ personas. Versioned: editing a BrandKit creates a new revision so
agents can refer to "the brand kit as of asset X was generated".

Per Theme Q1 in PLAN-v1.2 (the claude.ai/design-style brand setup
flow). Agents pull from the active BrandKit when generating content.
"""

import enum
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class BrandKit(Base):
    __tablename__ = "brand_kits"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Monotonically incrementing per-Org. Updating a kit bumps the
    # version + clones the row; the old version remains for replay
    # / "regenerate with brand v3" semantics.
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Exactly one kit per Org is `is_active=True` at any time; agents
    # default to that one. Switched via an activation endpoint.
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true", index=True
    )

    # Asset references — point at uploaded files
    logo_asset_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    logo_dark_asset_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )

    # Palette: {"primary": "#7660A8", "secondary": "#9384BD",
    #           "accent": "#FFFFFF", "neutrals": {...}, "scales": {...}}
    palette_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Fonts: {"display": "Poppins", "body": "Poppins", "mono": "JetBrains Mono",
    #          "sizes": {"h1": "...", "body": "..."}}
    fonts_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Voice: {"sliders": {"formal_casual": 0.6, ...},
    #          "do_say": [...], "dont_say": [...], "examples_good": [...],
    #          "examples_bad": [...]}
    voice_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Free-form positioning statement, tagline, mission, etc.
    positioning_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
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

    personas: Mapped[list["Persona"]] = relationship(
        "Persona",
        back_populates="brand_kit",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class Persona(Base):
    """ICP / target-audience persona, child of a BrandKit.

    Agents use personas to tune voice + topic + channel selection
    when generating content.
    """
    __tablename__ = "personas"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    brand_kit_id: Mapped[UUID] = mapped_column(
        ForeignKey("brand_kits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Free-form structured fields
    demographics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    jobs_to_be_done: Mapped[list | None] = mapped_column(JSON, nullable=True)
    fears: Mapped[list | None] = mapped_column(JSON, nullable=True)
    desires: Mapped[list | None] = mapped_column(JSON, nullable=True)
    traits: Mapped[list | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    brand_kit: Mapped["BrandKit"] = relationship("BrandKit", back_populates="personas", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("brand_kit_id", "name", name="uq_personas_kit_name"),
    )
