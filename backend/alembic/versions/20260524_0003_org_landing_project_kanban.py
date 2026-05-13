"""Add organizations.landing_pages_json + projects.kanban_json.

Mirrors the model state landed in PR #234 (landing pages) and PR #233
(kanban) that shipped without migrations. The same class of bug as #251
(TOTP columns).

Revision ID: 20260524_0003
Revises: 20260524_0002
Create Date: 2026-05-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260524_0003"
down_revision: Union[str, None] = "20260524_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column("landing_pages_json", sa.JSON(), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column("kanban_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("projects", "kanban_json")
    op.drop_column("organizations", "landing_pages_json")
