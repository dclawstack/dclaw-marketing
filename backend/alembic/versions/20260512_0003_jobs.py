"""A2 — jobs table

Revision ID: 20260512_0003
Revises: 20260512_0002
Create Date: 2026-05-12

Adds the durable record for Celery background tasks. Every
long-running operation (ingestion, generation, repurposing, scheduled
publish, analytics rollup, agent runs) writes a row to `jobs` and
updates progress / result / error as it executes.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260512_0003"
down_revision: Union[str, None] = "20260512_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    job_status = sa.Enum(
        "queued", "running", "succeeded", "failed", "canceled",
        name="jobstatus",
    )
    job_status.create(op.get_bind(), checkfirst=False)

    op.create_table(
        "jobs",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "organization_id",
            sa.UUID(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "initiated_by_user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("kind", sa.String(length=128), nullable=False),
        sa.Column(
            "status",
            sa.Enum(name="jobstatus", create_type=False),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("progress", sa.Float(), nullable=False, server_default="0"),
        sa.Column("progress_label", sa.String(length=255), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("result_url", sa.String(length=2048), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("celery_task_id", sa.String(length=64), nullable=True),
        sa.Column(
            "queued_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_jobs_organization_id", "jobs", ["organization_id"])
    op.create_index("ix_jobs_initiated_by_user_id", "jobs", ["initiated_by_user_id"])
    op.create_index("ix_jobs_kind", "jobs", ["kind"])
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_celery_task_id", "jobs", ["celery_task_id"])


def downgrade() -> None:
    op.drop_index("ix_jobs_celery_task_id", table_name="jobs")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_index("ix_jobs_kind", table_name="jobs")
    op.drop_index("ix_jobs_initiated_by_user_id", table_name="jobs")
    op.drop_index("ix_jobs_organization_id", table_name="jobs")
    op.drop_table("jobs")
    sa.Enum(name="jobstatus").drop(op.get_bind(), checkfirst=False)
