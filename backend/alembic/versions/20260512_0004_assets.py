"""A3 — assets table

Revision ID: 20260512_0004
Revises: 20260512_0003
Create Date: 2026-05-12

Adds the durable metadata row for every object stored in S3/MinIO.
The bytes live in object storage; this table tracks what they are,
who owns them, and their lifecycle status.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260512_0004"
down_revision: Union[str, None] = "20260512_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    asset_kind = sa.Enum(
        "image", "video", "audio", "document", "data", "archive", "other",
        name="assetkind",
    )
    asset_kind.create(op.get_bind(), checkfirst=False)

    asset_status = sa.Enum(
        "uploading", "ready", "failed", "deleted", name="assetstatus"
    )
    asset_status.create(op.get_bind(), checkfirst=False)

    op.create_table(
        "assets",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "organization_id",
            sa.UUID(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "created_by_user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "kind",
            sa.Enum(name="assetkind", create_type=False),
            nullable=False,
        ),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=512), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("bucket", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column(
            "status",
            sa.Enum(name="assetstatus", create_type=False),
            nullable=False,
            server_default="uploading",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("storage_key", name="uq_assets_storage_key"),
    )
    op.create_index("ix_assets_organization_id", "assets", ["organization_id"])
    op.create_index("ix_assets_created_by_user_id", "assets", ["created_by_user_id"])
    op.create_index("ix_assets_kind", "assets", ["kind"])
    op.create_index("ix_assets_sha256", "assets", ["sha256"])


def downgrade() -> None:
    op.drop_index("ix_assets_sha256", table_name="assets")
    op.drop_index("ix_assets_kind", table_name="assets")
    op.drop_index("ix_assets_created_by_user_id", table_name="assets")
    op.drop_index("ix_assets_organization_id", table_name="assets")
    op.drop_table("assets")
    sa.Enum(name="assetstatus").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="assetkind").drop(op.get_bind(), checkfirst=False)
