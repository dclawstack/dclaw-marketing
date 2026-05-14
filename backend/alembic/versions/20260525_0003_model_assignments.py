"""OrgModelAssignment + UserModelPreference tables.

Revision ID: 20260525_0003
Revises: 20260525_0002
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260525_0003"
down_revision: Union[str, None] = "20260525_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "org_model_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("capability", sa.String(64), nullable=False),
        sa.Column(
            "model_entry_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("model_entries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "set_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
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
            "organization_id", "capability", name="uq_org_assignment_org_capability"
        ),
    )
    op.create_index(
        "ix_org_model_assignments_organization_id",
        "org_model_assignments",
        ["organization_id"],
    )
    op.create_index(
        "ix_org_model_assignments_capability",
        "org_model_assignments",
        ["capability"],
    )

    op.create_table(
        "user_model_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("capability", sa.String(64), nullable=False),
        sa.Column(
            "model_entry_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("model_entries.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "user_id", "organization_id", "capability",
            name="uq_user_pref_user_org_capability",
        ),
    )
    op.create_index(
        "ix_user_model_preferences_user_id",
        "user_model_preferences",
        ["user_id"],
    )
    op.create_index(
        "ix_user_model_preferences_organization_id",
        "user_model_preferences",
        ["organization_id"],
    )
    op.create_index(
        "ix_user_model_preferences_capability",
        "user_model_preferences",
        ["capability"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_model_preferences_capability", "user_model_preferences")
    op.drop_index("ix_user_model_preferences_organization_id", "user_model_preferences")
    op.drop_index("ix_user_model_preferences_user_id", "user_model_preferences")
    op.drop_table("user_model_preferences")
    op.drop_index("ix_org_model_assignments_capability", "org_model_assignments")
    op.drop_index("ix_org_model_assignments_organization_id", "org_model_assignments")
    op.drop_table("org_model_assignments")
