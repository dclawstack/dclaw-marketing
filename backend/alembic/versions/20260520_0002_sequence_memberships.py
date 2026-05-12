"""Phase 7.x — SequenceMembership table

Revision ID: 20260520_0002
Revises: 20260520_0001
Create Date: 2026-05-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260520_0002"
down_revision: Union[str, None] = "20260520_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    status_enum = sa.Enum(
        "enrolled",
        "paused",
        "completed",
        "failed",
        "unsubscribed",
        name="sequencemembershipstatus",
    )
    status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "sequence_memberships",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.UUID(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "sequence_id",
            sa.UUID(),
            sa.ForeignKey("email_sequences.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "lead_id",
            sa.UUID(),
            sa.ForeignKey("leads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "current_step_position",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            status_enum,
            nullable=False,
            server_default="enrolled",
        ),
        sa.Column("error_message", sa.String, nullable=True),
        sa.Column("history_json", sa.JSON, nullable=True),
        sa.Column(
            "enrolled_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("last_advanced_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint(
        "uq_seq_membership",
        "sequence_memberships",
        ["sequence_id", "lead_id"],
    )
    op.create_index(
        "ix_seq_memberships_organization_id",
        "sequence_memberships",
        ["organization_id"],
    )
    op.create_index(
        "ix_seq_memberships_sequence_id",
        "sequence_memberships",
        ["sequence_id"],
    )
    op.create_index(
        "ix_seq_memberships_lead_id",
        "sequence_memberships",
        ["lead_id"],
    )
    op.create_index(
        "ix_seq_memberships_next_run_at",
        "sequence_memberships",
        ["next_run_at"],
    )
    op.create_index(
        "ix_seq_memberships_status_next_run",
        "sequence_memberships",
        ["status", "next_run_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_seq_memberships_status_next_run",
        table_name="sequence_memberships",
    )
    op.drop_index(
        "ix_seq_memberships_next_run_at",
        table_name="sequence_memberships",
    )
    op.drop_index(
        "ix_seq_memberships_lead_id",
        table_name="sequence_memberships",
    )
    op.drop_index(
        "ix_seq_memberships_sequence_id",
        table_name="sequence_memberships",
    )
    op.drop_index(
        "ix_seq_memberships_organization_id",
        table_name="sequence_memberships",
    )
    op.drop_table("sequence_memberships")
    sa.Enum(name="sequencemembershipstatus").drop(
        op.get_bind(), checkfirst=True
    )
