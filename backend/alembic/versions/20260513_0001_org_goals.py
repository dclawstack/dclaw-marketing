"""Q5 — org goals + constraints + autonomy posture

Revision ID: 20260513_0001
Revises: 20260512_0008
Create Date: 2026-05-13

Adds three free-form JSON columns to organizations table for the
Theme Q5 setup flow. Shape suggestions live in OpenAPI docs; not
strictly typed at the DB layer so schema can evolve without
migrations.

Note: chain off 0008 (Q3 KG migration). If Q3 lands after this,
update down_revision to the appropriate predecessor on rebase.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260513_0001"
down_revision: Union[str, None] = "20260512_0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("goals_json", sa.JSON(), nullable=True))
    op.add_column("organizations", sa.Column("constraints_json", sa.JSON(), nullable=True))
    op.add_column("organizations", sa.Column("autonomy_posture_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("organizations", "autonomy_posture_json")
    op.drop_column("organizations", "constraints_json")
    op.drop_column("organizations", "goals_json")
