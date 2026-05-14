"""ModelCallLog — every model invocation, for /admin/models metrics.

Revision ID: 20260525_0002
Revises: 20260525_0001
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260525_0002"
down_revision: Union[str, None] = "20260525_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CALL_STATUSES = ("success", "error", "timeout")


def upgrade() -> None:
    call_status_enum = postgresql.ENUM(
        *CALL_STATUSES, name="model_call_status_enum", create_type=False
    )
    call_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "model_call_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "model_entry_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("model_entries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("caller_component", sa.String(64), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("duration_ms", sa.Integer, nullable=False, server_default="0"),
        sa.Column("input_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float, nullable=False, server_default="0"),
        sa.Column("status", call_status_enum, nullable=False, server_default="success"),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("request_id", sa.String(128), nullable=True),
    )
    op.create_index(
        "ix_model_call_logs_model_entry_id",
        "model_call_logs",
        ["model_entry_id"],
    )
    op.create_index(
        "ix_model_call_logs_organization_id",
        "model_call_logs",
        ["organization_id"],
    )
    op.create_index(
        "ix_model_call_logs_caller_component",
        "model_call_logs",
        ["caller_component"],
    )
    op.create_index(
        "ix_model_call_logs_started_at",
        "model_call_logs",
        ["started_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_model_call_logs_started_at", table_name="model_call_logs")
    op.drop_index("ix_model_call_logs_caller_component", table_name="model_call_logs")
    op.drop_index("ix_model_call_logs_organization_id", table_name="model_call_logs")
    op.drop_index("ix_model_call_logs_model_entry_id", table_name="model_call_logs")
    op.drop_table("model_call_logs")
    sa.Enum(name="model_call_status_enum").drop(op.get_bind(), checkfirst=True)
