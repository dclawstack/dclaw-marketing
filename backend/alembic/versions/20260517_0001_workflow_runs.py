"""Phase 10.4 — workflow_runs table

Revision ID: 20260517_0001
Revises: 20260516_0001
Create Date: 2026-05-17

Adds:
- workflow_runs — one execution of a Workflow's DSL with status,
  inputs, per-node trace, final context.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260517_0001"
down_revision: Union[str, None] = "20260516_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


WORKFLOW_RUN_STATUS = ("pending", "running", "paused", "completed", "failed")


def upgrade() -> None:
    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "workflow_id",
            sa.Uuid(),
            sa.ForeignKey("workflows.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("initial_context", sa.JSON(), nullable=False),
        sa.Column("final_context", sa.JSON(), nullable=True),
        sa.Column("node_results", sa.JSON(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(*WORKFLOW_RUN_STATUS, name="workflowrunstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("deferred_reason", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "started_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "completed_at", sa.DateTime(timezone=True), nullable=True
        ),
    )
    op.create_index(
        "ix_workflow_runs_workflow_id", "workflow_runs", ["workflow_id"]
    )
    op.create_index(
        "ix_workflow_runs_organization_id",
        "workflow_runs",
        ["organization_id"],
    )
    op.create_index(
        "ix_workflow_runs_started_by_user_id",
        "workflow_runs",
        ["started_by_user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_workflow_runs_started_by_user_id", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_organization_id", table_name="workflow_runs")
    op.drop_index("ix_workflow_runs_workflow_id", table_name="workflow_runs")
    op.drop_table("workflow_runs")
    op.execute("DROP TYPE IF EXISTS workflowrunstatus")
