"""model_entries.pricing_json for cost display on /admin/models (S5 #365)

Adds a JSON column carrying per-token rates (or {is_free: true}). Null
when the upstream provider didn't supply pricing data.

Revision ID: 20260528_0001
Revises: 20260527_0001
Create Date: 2026-05-15
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260528_0001"
down_revision: Union[str, None] = "20260527_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "model_entries",
        sa.Column("pricing_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("model_entries", "pricing_json")
