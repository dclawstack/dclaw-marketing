"""Add display_code (6-hex unique handle) to users.

Bootstrap admin → '000000'. Other existing users backfilled sequentially
by created_at order starting at '000001'. Future inserts compute the
next value at the application layer.

Revision ID: 20260524_0002
Revises: 20260524_0001
Create Date: 2026-05-24
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260524_0002"
down_revision: Union[str, None] = "20260524_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


BOOTSTRAP_EMAIL = "admin@dclaw.io"


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("display_code", sa.String(length=6), nullable=True),
    )
    op.create_index(
        "ix_users_display_code", "users", ["display_code"], unique=True
    )

    # Backfill. Bootstrap admin first, then everyone else by created_at.
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE users SET display_code = '000000' WHERE email = :email"
        ),
        {"email": BOOTSTRAP_EMAIL},
    )
    rows = bind.execute(
        sa.text(
            "SELECT id FROM users WHERE display_code IS NULL "
            "ORDER BY created_at ASC, id ASC"
        )
    ).fetchall()
    for i, (uid,) in enumerate(rows, start=1):
        bind.execute(
            sa.text(
                "UPDATE users SET display_code = :code WHERE id = :uid"
            ),
            {"code": f"{i:06x}", "uid": uid},
        )

    op.alter_column("users", "display_code", nullable=False)


def downgrade() -> None:
    op.drop_index("ix_users_display_code", table_name="users")
    op.drop_column("users", "display_code")
