"""ApprovalRequest — the queue of agent-prepared actions awaiting a
human decision.

The Hard-gate trust mode for outbound posting and other high-stakes
actions (per PLAN-v1.2 §v2.0 §5.2) creates one of these rows. A
human reviewer in the Approval Inbox decides approve / reject /
regenerate.

The action fires only AFTER status flips to `approved`. The link to
the resulting AuditEvent closes the loop.
"""

import enum
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ApprovalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    expired = "expired"
    auto_approved = "auto_approved"     # Soft-gate timeout fired
    canceled = "canceled"               # The requestor pulled it back


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

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

    # Who/what requested approval — one of these will be set.
    requested_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    requested_by_agent: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # What's being asked.
    action_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    target_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Full proposed action body — what would fire if approved.
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    # Human-readable summary surfaced in the Inbox (e.g.,
    # "Publish post to @acme_official: \"Today we're launching...\"").
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[ApprovalStatus] = mapped_column(
        SQLEnum(ApprovalStatus), nullable=False, default=ApprovalStatus.pending, index=True
    )

    # Decision
    decided_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Hard-deadline. After this, expiry sweep flips status to `expired`
    # (or auto_approved for Soft-gate items).
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # S4-A5 — 4-eye / N-of-M approval. `approvers_required` is the
    # threshold of distinct users who must sign off; for legacy single-
    # approver rows it stays at 1. `approvers_user_ids_json` tracks who
    # has signed off so far (list of UUID strings).
    approvers_required: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1
    )
    approvers_user_ids_json: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True
    )
