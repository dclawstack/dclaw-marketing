"""AuditEvent — the immutable record of every consequential action.

Every external-facing action (publish, send, spend, grant access,
brand change) writes an AuditEvent row. Agents also write audit
events when they fire any tool that has external side effects.

The audit trail is BOTH the compliance record AND the training
signal for agent learning: a reviewer rejecting a draft is data the
Creatives Agent uses to tune its taste over time.
"""

import enum
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    JSON,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditActorKind(str, enum.Enum):
    """Who initiated the action."""
    user = "user"          # Direct human action via UI/API
    agent = "agent"        # AI agent (Creatives, SMM, …) on its own
    system = "system"      # Internal worker/cron — no human or agent attributed


class AuditResult(str, enum.Enum):
    success = "success"
    failure = "failure"


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    organization_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    actor_kind: Mapped[AuditActorKind] = mapped_column(
        SQLEnum(AuditActorKind), nullable=False, index=True
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Free-form agent identifier — "creatives_agent_v1", "conductor", …
    actor_agent: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    # The action and the resource it acted on.
    action_type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    target_type: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # Frozen JSON of what changed / what was sent / agent reasoning trace.
    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    result: Mapped[AuditResult] = mapped_column(
        SQLEnum(AuditResult), nullable=False, default=AuditResult.success
    )
    error_message: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    # Request metadata when available
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Link back to the approval (if any) that authorized this action.
    approval_request_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("approval_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
