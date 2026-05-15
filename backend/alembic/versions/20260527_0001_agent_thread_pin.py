"""agent_threads.is_pinned for Conductor pin/rename/delete polish (S5-CDR-F)

Adds a boolean column that controls sidebar ordering — pinned threads
float to the top. Default `false`; backfill is implicit via default.

Revision ID: 20260527_0001
Revises: 20260526_0001
Create Date: 2026-05-15
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260527_0001"
down_revision: Union[str, None] = "20260526_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "agent_threads",
        sa.Column(
            "is_pinned",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("agent_threads", "is_pinned")
