"""Phase 5.5 — Add 'mastodon' to ScheduledPostChannel enum

Revision ID: 20260517_0003
Revises: 20260517_0002
Create Date: 2026-05-17
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260517_0003"
down_revision: Union[str, None] = "20260517_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Postgres requires this to run outside a transaction in older
    # versions; modern Postgres handles it inside. We use a literal
    # ADD VALUE — IF NOT EXISTS guard is safe in 12+.
    op.execute(
        "ALTER TYPE scheduledpostchannel ADD VALUE IF NOT EXISTS 'mastodon'"
    )


def downgrade() -> None:
    # Postgres doesn't support removing enum values without rebuilding
    # the type. Down-migration intentionally a no-op.
    pass
