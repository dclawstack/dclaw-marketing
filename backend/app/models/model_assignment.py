"""OrgModelAssignment + UserModelPreference (S4-M12).

Two tables that resolve to "which model should we use for this
(org, user, capability) tuple". `model_resolver.py` (M11) reads both
plus the catalog to produce the final answer.

Per spec:
  OrgModelAssignment(id, org_id, capability, model_entry_id, set_by_user_id)
  UserModelPreference(id, user_id, org_id, capability, model_entry_id)
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class OrgModelAssignment(Base):
    """Org-level default model for a given capability slot."""

    __tablename__ = "org_model_assignments"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "capability", name="uq_org_assignment_org_capability"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    capability: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    model_entry_id: Mapped[UUID] = mapped_column(
        ForeignKey("model_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    set_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
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


class UserModelPreference(Base):
    """Per-user override beating the org default for a capability slot."""

    __tablename__ = "user_model_preferences"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "organization_id",
            "capability",
            name="uq_user_pref_user_org_capability",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    capability: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    model_entry_id: Mapped[UUID] = mapped_column(
        ForeignKey("model_entries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
