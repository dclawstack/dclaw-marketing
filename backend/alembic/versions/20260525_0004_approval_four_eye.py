"""ApprovalRequest 4-eye fields + AgentRun trace key.

S4-A5: approval_requests gets `approvers_required` (default 1) and
`approvers_user_ids_json` (list of user UUIDs who have signed off).
status flips to `approved` only when len(approvers) >= approvers_required.

S4-A6: reasoning trace replay reuses ModelCallLog rows tagged with a
shared `request_id` per agent run — no new table needed.

Revision ID: 20260525_0004
Revises: 20260525_0003
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260525_0004"
down_revision: Union[str, None] = "20260525_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "approval_requests",
        sa.Column(
            "approvers_required",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )
    op.add_column(
        "approval_requests",
        sa.Column(
            "approvers_user_ids_json",
            postgresql.JSON,
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("approval_requests", "approvers_user_ids_json")
    op.drop_column("approval_requests", "approvers_required")
