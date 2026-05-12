"""AgentThread + AgentMessage — conversation memory for the agent fleet
(Theme G / Phase 9).

The Conductor chat surface, role-Agent suggestion threads, and any
future agent-to-agent dispatch all use these two tables. Threads are
org-scoped; messages reference a thread + an actor (user / agent).
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
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AgentKind(str, enum.Enum):
    """Identifies the agent role for a thread / message.

    `conductor` is the Manager-station chat; the role agents have
    their own threads spun off as the Conductor dispatches.
    """

    conductor = "conductor"
    creatives = "creatives"
    smm = "smm"
    seo = "seo"
    paid_media = "paid_media"
    analyst = "analyst"
    inbox = "inbox"


class AgentMessageRole(str, enum.Enum):
    user = "user"
    agent = "agent"
    system = "system"
    tool = "tool"


class AgentThread(Base):
    __tablename__ = "agent_threads"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    parent_thread_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agent_threads.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    kind: Mapped[AgentKind] = mapped_column(SQLEnum(AgentKind), nullable=False)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)

    started_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
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


class AgentMessage(Base):
    __tablename__ = "agent_messages"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    thread_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_threads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role: Mapped[AgentMessageRole] = mapped_column(
        SQLEnum(AgentMessageRole), nullable=False
    )
    # Which agent (if role=agent) — None for user / system messages.
    agent_kind: Mapped[AgentKind | None] = mapped_column(
        SQLEnum(AgentKind), nullable=True
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)

    # For tool calls / tool results
    tool_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tool_arguments: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tool_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Reasoning trace, confidence, alternatives — surfaces in /audit-log
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # If this message resulted in an ApprovalRequest, link it.
    approval_request_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("approval_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
