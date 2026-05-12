"""Phase 5.7 — Add 'pinterest' and 'discord' to ScheduledPostChannel.

Revision ID: 20260518_0002
Revises: 20260518_0001
Create Date: 2026-05-18
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260518_0002"
down_revision: Union[str, None] = "20260518_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "ALTER TYPE scheduledpostchannel ADD VALUE IF NOT EXISTS 'pinterest'"
    )
    op.execute(
        "ALTER TYPE scheduledpostchannel ADD VALUE IF NOT EXISTS 'discord'"
    )


def downgrade() -> None:
    pass
