"""Phase 10 / §6.6 — workflow template flag.

Adds ``is_template`` (Boolean, default false) + ``cloned_from_workflow_id``
self-FK to ``workflows`` so we can build a per-Org library of reusable
workflow templates and track lineage when an Org clones one.

Revision ID: 20260522_0001
Revises: 20260521_0001
Create Date: 2026-05-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260522_0001"
down_revision: Union[str, None] = "20260521_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workflows",
        sa.Column(
            "is_template",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "workflows",
        sa.Column(
            "cloned_from_workflow_id",
            sa.UUID(),
            sa.ForeignKey("workflows.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_workflows_org_is_template",
        "workflows",
        ["organization_id", "is_template"],
    )


def downgrade() -> None:
    op.drop_index("ix_workflows_org_is_template", table_name="workflows")
    op.drop_column("workflows", "cloned_from_workflow_id")
    op.drop_column("workflows", "is_template")
