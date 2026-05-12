"""Phase 10+11 — ops + compliance data layer

Revision ID: 20260516_0001
Revises: 20260515_0002
Create Date: 2026-05-16

Adds:
- cost_ledger (Phase 11 / I3)
- quota_counters (Phase 11 / I1)
- time_entries (Phase 10 / L)
- workflows (Phase 10 / P)
- playbooks (Phase 10 / N)
- data_export_requests (Phase 11 / I4)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260516_0001"
down_revision: Union[str, None] = "20260515_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


WORKFLOW_STATUS = ("draft", "active", "paused", "archived")
PLAYBOOK_KIND = ("prompt", "brief", "sop", "playbook")
DATA_EXPORT_STATUS = ("queued", "running", "ready", "failed", "expired")


def upgrade() -> None:
    op.create_table(
        "cost_ledger",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("provider", sa.String(64), nullable=False, index=True),
        sa.Column("provider_resource", sa.String(128), nullable=True),
        sa.Column("kind", sa.String(64), nullable=False, index=True),
        sa.Column("amount_usd", sa.Float(), nullable=False),
        sa.Column("units", sa.Float(), nullable=True),
        sa.Column("units_kind", sa.String(64), nullable=True),
        sa.Column(
            "job_id",
            sa.Uuid(),
            sa.ForeignKey("jobs.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "agent_message_id",
            sa.Uuid(),
            sa.ForeignKey("agent_messages.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            index=True,
        ),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
    )

    op.create_table(
        "quota_counters",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("channel", sa.String(64), nullable=False, index=True),
        sa.Column(
            "window_start",
            sa.DateTime(timezone=True),
            nullable=False,
            index=True,
        ),
        sa.Column("window_seconds", sa.Integer(), nullable=False),
        sa.Column("limit", sa.Integer(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "organization_id",
            "channel",
            "window_start",
            name="uq_quota_window",
        ),
    )

    op.create_table(
        "time_entries",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "campaign_id",
            sa.Uuid(),
            sa.ForeignKey("campaigns.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), nullable=False, index=True
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column(
            "billable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column("rate_usd_per_hour", sa.Float(), nullable=True),
    )

    op.create_table(
        "workflows",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("slug", sa.String(128), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("dsl_json", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(*WORKFLOW_STATUS, name="workflowstatus"),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "created_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "organization_id", "slug", name="uq_workflow_org_slug"
        ),
    )

    op.create_table(
        "playbooks",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("slug", sa.String(128), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(*PLAYBOOK_KIND, name="playbookkind"),
            nullable=False,
        ),
        sa.Column("body_markdown", sa.Text(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column(
            "is_template",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "organization_id", "slug", name="uq_playbook_org_slug"
        ),
    )

    op.create_table(
        "data_export_requests",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "requested_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("scope", sa.String(64), nullable=False),
        sa.Column(
            "status",
            sa.Enum(*DATA_EXPORT_STATUS, name="dataexportstatus"),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("storage_key", sa.String(512), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("data_export_requests")
    op.drop_table("playbooks")
    op.drop_table("workflows")
    op.drop_table("time_entries")
    op.drop_table("quota_counters")
    op.drop_table("cost_ledger")
    for name in ("dataexportstatus", "playbookkind", "workflowstatus"):
        sa.Enum(name=name).drop(op.get_bind(), checkfirst=True)
