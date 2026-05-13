"""Rename User.display_code → slug; re-slug all users + orgs.

New format:
- User: `u-{first4(full_name|email)}-{random6hex}`; bootstrap = `s-admn-000000`.
- Org: `o-{first4(name)}-{random6hex}`.

Revision ID: 20260524_0004
Revises: 20260524_0003
Create Date: 2026-05-24
"""

from __future__ import annotations

import re
import secrets
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260524_0004"
down_revision: Union[str, None] = "20260524_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


BOOTSTRAP_EMAIL = "admin@dclaw.io"
BOOTSTRAP_SLUG = "s-admn-000000"
BOOTSTRAP_FULL_NAME = "DClaw SuperAdmin"
_NON_ALNUM_RX = re.compile(r"[^a-z0-9]+")


def _first4(name: str | None) -> str:
    if not name:
        return "user"
    cleaned = _NON_ALNUM_RX.sub("", name.lower())
    if not cleaned:
        return "user"
    return cleaned[:4] if len(cleaned) >= 4 else cleaned + "0" * (4 - len(cleaned))


def _unique_slug(bind, table: str, prefix: str, name: str | None) -> str:
    """Generate a fresh slug, retrying on the (very rare) collision."""
    for _ in range(8):
        candidate = f"{prefix}-{_first4(name)}-{secrets.token_hex(3)}"
        row = bind.execute(
            sa.text(f"SELECT 1 FROM {table} WHERE slug = :s"), {"s": candidate}
        ).first()
        if row is None:
            return candidate
    # 8 collisions in 16M-keyspace is statistically impossible; raise loudly.
    raise RuntimeError(f"Could not allocate slug for {table}/{name}")


def upgrade() -> None:
    bind = op.get_bind()

    # ---- Users ----
    op.add_column(
        "users", sa.Column("slug", sa.String(length=32), nullable=True)
    )

    # Bootstrap first (deterministic).
    bind.execute(
        sa.text(
            "UPDATE users "
            "SET slug = :slug, full_name = :name "
            "WHERE email = :email"
        ),
        {
            "slug": BOOTSTRAP_SLUG,
            "name": BOOTSTRAP_FULL_NAME,
            "email": BOOTSTRAP_EMAIL,
        },
    )

    rows = bind.execute(
        sa.text(
            "SELECT id, full_name, email FROM users "
            "WHERE slug IS NULL ORDER BY created_at ASC, id ASC"
        )
    ).fetchall()
    for uid, full_name, email in rows:
        seed_name = full_name or (email.split("@")[0] if email else None)
        bind.execute(
            sa.text("UPDATE users SET slug = :slug WHERE id = :uid"),
            {"slug": _unique_slug(bind, "users", "u", seed_name), "uid": uid},
        )

    op.alter_column("users", "slug", nullable=False)
    op.create_index("ix_users_slug", "users", ["slug"], unique=True)

    # Drop the old display_code (data is now embedded in slug).
    op.drop_index("ix_users_display_code", table_name="users")
    op.drop_column("users", "display_code")

    # ---- Organizations ----
    org_rows = bind.execute(
        sa.text("SELECT id, name FROM organizations ORDER BY created_at ASC, id ASC")
    ).fetchall()
    for oid, name in org_rows:
        bind.execute(
            sa.text("UPDATE organizations SET slug = :slug WHERE id = :oid"),
            {
                "slug": _unique_slug(bind, "organizations", "o", name),
                "oid": oid,
            },
        )


def downgrade() -> None:
    # Best-effort downgrade. Restores display_code from the hex chunk of
    # the slug; org slugs are left in the new format (irreversible).
    op.add_column(
        "users", sa.Column("display_code", sa.String(length=6), nullable=True)
    )
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "UPDATE users SET display_code = "
            "RIGHT(slug, 6) WHERE slug IS NOT NULL"
        )
    )
    op.create_index(
        "ix_users_display_code", "users", ["display_code"], unique=True
    )
    op.drop_index("ix_users_slug", table_name="users")
    op.drop_column("users", "slug")
