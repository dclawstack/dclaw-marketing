"""agent_messages.attachment_asset_ids for Conductor file/image attachments (S5-CDR-B)

Adds a JSON array column carrying Asset UUIDs the user attached when
sending a chat message. Backwards-compatible: existing rows have NULL.

Revision ID: 20260526_0001
Revises: 20260525_0004
Create Date: 2026-05-15
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260526_0001"
down_revision: Union[str, None] = "20260525_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "agent_messages",
        sa.Column("attachment_asset_ids", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agent_messages", "attachment_asset_ids")
