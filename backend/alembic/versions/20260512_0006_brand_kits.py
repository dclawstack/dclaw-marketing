"""Q1 — brand_kits and personas

Revision ID: 20260512_0006
Revises: 20260512_0005
Create Date: 2026-05-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260512_0006"
down_revision: Union[str, None] = "20260512_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "brand_kits",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "organization_id",
            sa.UUID(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column(
            "logo_asset_id",
            sa.UUID(),
            sa.ForeignKey("assets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "logo_dark_asset_id",
            sa.UUID(),
            sa.ForeignKey("assets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("palette_json", sa.JSON(), nullable=True),
        sa.Column("fonts_json", sa.JSON(), nullable=True),
        sa.Column("voice_json", sa.JSON(), nullable=True),
        sa.Column("positioning_json", sa.JSON(), nullable=True),
        sa.Column(
            "created_by_user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
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
    )
    op.create_index("ix_brand_kits_organization_id", "brand_kits", ["organization_id"])
    op.create_index("ix_brand_kits_is_active", "brand_kits", ["is_active"])

    op.create_table(
        "personas",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "brand_kit_id",
            sa.UUID(),
            sa.ForeignKey("brand_kits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("demographics", sa.JSON(), nullable=True),
        sa.Column("jobs_to_be_done", sa.JSON(), nullable=True),
        sa.Column("fears", sa.JSON(), nullable=True),
        sa.Column("desires", sa.JSON(), nullable=True),
        sa.Column("traits", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("brand_kit_id", "name", name="uq_personas_kit_name"),
    )
    op.create_index("ix_personas_brand_kit_id", "personas", ["brand_kit_id"])


def downgrade() -> None:
    op.drop_index("ix_personas_brand_kit_id", table_name="personas")
    op.drop_table("personas")
    op.drop_index("ix_brand_kits_is_active", table_name="brand_kits")
    op.drop_index("ix_brand_kits_organization_id", table_name="brand_kits")
    op.drop_table("brand_kits")
