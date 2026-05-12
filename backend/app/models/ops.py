"""Phase 10 + 11 operational data layer — agency ops + compliance.

Scaffolding for the post-v1.2 agency themes (J/K/L/M/N/P) and the
v1.2 compliance/reliability surfaces (I1-I4 + O Client Portal).

Models included:
- CostLedger (Phase 11 / I3)        — per-Org provider spend tracking
- QuotaCounter (Phase 11 / I1)      — sliding-window per-channel quotas
- TimeEntry (Phase 10 / L)          — per-task / per-campaign time logs
- Workflow (Phase 10 / P)           — visual no-code LLM-chain DSL
- Playbook (Phase 10 / N)           — reusable prompts / briefs / SOPs
- DataExportRequest (Phase 11 / I4) — GDPR export jobs
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
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


# ---------- Phase 11 — I3 Cost tracking -------------------------------------


class CostLedger(Base):
    """One row per LLM / image / video / voice / ad-platform charge.

    The daily rollup aggregates these into /admin/costs cards. Soft and
    hard caps live on the Org (autonomy_posture JSON for now).
    """

    __tablename__ = "cost_ledger"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    provider: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    provider_resource: Mapped[str | None] = mapped_column(
        String(128), nullable=True
    )
    kind: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )  # "llm" | "image" | "video" | "voice" | "music" | "ads" | "other"
    amount_usd: Mapped[float] = mapped_column(Float, nullable=False)
    units: Mapped[float | None] = mapped_column(Float, nullable=True)
    units_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Optional links back to what spent this money
    job_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True
    )
    agent_message_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("agent_messages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


# ---------- Phase 11 — I1 Quotas --------------------------------------------


class QuotaCounter(Base):
    """Sliding-window quota state for a (org, channel, window_start) tuple.

    The rate-limit guard updates these atomically before firing any
    outbound call; UI shows "Twitter: 47/300 today" from the live row.
    """

    __tablename__ = "quota_counters"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "channel",
            "window_start",
            name="uq_quota_window",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    window_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    window_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    limit: Mapped[int] = mapped_column(Integer, nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


# ---------- Phase 10 — L Time tracking --------------------------------------


class TimeEntry(Base):
    __tablename__ = "time_entries"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    campaign_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_seconds: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    billable: Mapped[bool] = mapped_column(default=True, nullable=False)
    rate_usd_per_hour: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )


# ---------- Phase 10 — P Workflow Builder -----------------------------------


class WorkflowStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    paused = "paused"
    archived = "archived"


class Workflow(Base):
    """Visual no-code chain of LLM steps + tool calls + approval gates."""

    __tablename__ = "workflows"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "slug", name="uq_workflow_org_slug"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # The DSL — nodes (LLM step / tool call / approval gate / branch /
    # webhook listener), edges, layout positions.
    dsl_json: Mapped[dict] = mapped_column(JSON, nullable=False)

    status: Mapped[WorkflowStatus] = mapped_column(
        SQLEnum(WorkflowStatus),
        nullable=False,
        default=WorkflowStatus.draft,
    )

    # §6.6 — workflow templates. Org-scoped. Clone target chain links
    # back via cloned_from_workflow_id for lineage / dashboards.
    is_template: Mapped[bool] = mapped_column(
        nullable=False, default=False, server_default="false"
    )
    cloned_from_workflow_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("workflows.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_by_user_id: Mapped[UUID | None] = mapped_column(
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


# ---------- Phase 10 — N Knowledge Base + SOPs ------------------------------


class PlaybookKind(str, enum.Enum):
    prompt = "prompt"
    brief = "brief"
    sop = "sop"
    playbook = "playbook"


class Playbook(Base):
    """Reusable prompts / briefs / SOPs / playbooks. Agent-searchable."""

    __tablename__ = "playbooks"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "slug", name="uq_playbook_org_slug"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[PlaybookKind] = mapped_column(
        SQLEnum(PlaybookKind), nullable=False
    )
    body_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    is_template: Mapped[bool] = mapped_column(default=False, nullable=False)

    created_by_user_id: Mapped[UUID | None] = mapped_column(
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


# ---------- Phase 11 — I4 GDPR / data export --------------------------------


class DataExportStatus(str, enum.Enum):
    queued = "queued"
    running = "running"
    ready = "ready"
    failed = "failed"
    expired = "expired"


class DataExportRequest(Base):
    """User-requested or admin-requested GDPR-style export of org data."""

    __tablename__ = "data_export_requests"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_by_user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    scope: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[DataExportStatus] = mapped_column(
        SQLEnum(DataExportStatus),
        nullable=False,
        default=DataExportStatus.queued,
    )
    storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


# ---------- Phase 10.4 — Workflow run state ---------------------------


class WorkflowRunStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    paused = "paused"          # node deferred (approval, branch, wait)
    completed = "completed"
    failed = "failed"


class WorkflowRun(Base):
    """One execution of a Workflow's DSL.

    Records inputs, the per-node trace, the final context, and the
    terminal status. Future: a separate WorkflowRunStep child table for
    finer-grained audit when individual node history matters for
    debugging.
    """

    __tablename__ = "workflow_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    workflow_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    initial_context: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )
    final_context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    node_results: Mapped[list | None] = mapped_column(JSON, nullable=True)

    status: Mapped[WorkflowRunStatus] = mapped_column(
        SQLEnum(WorkflowRunStatus),
        nullable=False,
        default=WorkflowRunStatus.pending,
    )
    deferred_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
