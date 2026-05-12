"""SequenceMembership — tracks a Lead's progress through an EmailSequence
(Phase 7.x).

One row per (lead, sequence) enrolment. The runner reads ``next_run_at``
to decide when to advance the membership to its next step.
"""

from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SequenceMembershipStatus(str, enum.Enum):
    enrolled = "enrolled"
    paused = "paused"
    completed = "completed"
    failed = "failed"
    unsubscribed = "unsubscribed"


class SequenceMembership(Base):
    __tablename__ = "sequence_memberships"
    __table_args__ = (
        UniqueConstraint(
            "sequence_id", "lead_id", name="uq_seq_membership"
        ),
        Index(
            "ix_seq_memberships_status_next_run",
            "status",
            "next_run_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence_id: Mapped[UUID] = mapped_column(
        ForeignKey("email_sequences.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lead_id: Mapped[UUID] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    current_step_position: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    status: Mapped[SequenceMembershipStatus] = mapped_column(
        SQLEnum(SequenceMembershipStatus),
        default=SequenceMembershipStatus.enrolled,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(nullable=True)
    history_json: Mapped[list | None] = mapped_column(JSON, nullable=True)

    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_advanced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


__all__ = ["SequenceMembership", "SequenceMembershipStatus"]
