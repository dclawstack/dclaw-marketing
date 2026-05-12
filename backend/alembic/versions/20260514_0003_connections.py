"""Phase 6 — Connection table (encrypted MCP credentials)

Revision ID: 20260514_0003
Revises: 20260514_0002
Create Date: 2026-05-14

Per Theme D / Phase 6 of IMPLEMENTATION-PLAN. Adds the connections
table that holds Fernet-encrypted access material for the platform's
MCP integrations.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260514_0003"
down_revision: Union[str, None] = "20260514_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CONNECTION_STATUS_VALUES = ("active", "reauth_required", "revoked", "error")


def upgrade() -> None:
    op.create_table(
        "connections",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("server_id", sa.String(128), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("auth_kind", sa.String(32), nullable=False),
        sa.Column("encrypted_secret_blob", sa.LargeBinary(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("scopes", sa.JSON(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(*CONNECTION_STATUS_VALUES, name="connectionstatus"),
            nullable=False,
            server_default="active",
        ),
        sa.Column("last_health_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_by_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "organization_id",
            "server_id",
            "name",
            name="uq_connection_org_server_name",
        ),
    )


def downgrade() -> None:
    op.drop_table("connections")
    sa.Enum(name="connectionstatus").drop(op.get_bind(), checkfirst=True)
