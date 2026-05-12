"""B5 Variant A/B Studio — VariantSet + Variant models.

Revision ID: 20260523_0001
Revises: 20260522_0001
Create Date: 2026-05-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260523_0001"
down_revision: Union[str, None] = "20260522_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    set_status = sa.Enum(
        "draft", "active", "paused", "concluded", name="variantsetstatus"
    )
    var_status = sa.Enum(
        "active", "paused", "winner", "loser", name="variantstatus"
    )
    set_status.create(op.get_bind(), checkfirst=True)
    var_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "variant_sets",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.UUID(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "campaign_id",
            sa.UUID(),
            sa.ForeignKey("campaigns.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("slot", sa.String(64), nullable=False),
        sa.Column("hypothesis", sa.Text, nullable=True),
        sa.Column("status", set_status, nullable=False, server_default="draft"),
        sa.Column(
            "auto_promote_winner",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
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
    )
    op.create_index(
        "ix_variant_sets_org", "variant_sets", ["organization_id"]
    )
    op.create_index(
        "ix_variant_sets_campaign", "variant_sets", ["campaign_id"]
    )

    op.create_table(
        "variants",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "set_id",
            sa.UUID(),
            sa.ForeignKey("variant_sets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "asset_id",
            sa.UUID(),
            sa.ForeignKey("assets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("label", sa.String(255), nullable=True),
        sa.Column("body_text", sa.Text, nullable=True),
        sa.Column("weight", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("status", var_status, nullable=False, server_default="active"),
        sa.Column("metrics_json", sa.JSON, nullable=True),
        sa.Column("impressions", sa.Integer, nullable=False, server_default="0"),
        sa.Column("conversions", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_variants_set", "variants", ["set_id"])


def downgrade() -> None:
    op.drop_index("ix_variants_set", table_name="variants")
    op.drop_table("variants")
    op.drop_index("ix_variant_sets_campaign", table_name="variant_sets")
    op.drop_index("ix_variant_sets_org", table_name="variant_sets")
    op.drop_table("variant_sets")
    sa.Enum(name="variantstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="variantsetstatus").drop(op.get_bind(), checkfirst=True)
