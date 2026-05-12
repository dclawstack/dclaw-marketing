"""Phase 5.x — Add 'substack' to ScheduledPostChannel enum

Revision ID: 20260519_0001
Revises: 20260518_0003
Create Date: 2026-05-19
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260519_0001"
down_revision: Union[str, None] = "20260518_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE scheduledpostchannel ADD VALUE IF NOT EXISTS 'substack'"
    )


def downgrade() -> None:
    # Postgres can't remove enum values without rebuilding the type.
    pass
