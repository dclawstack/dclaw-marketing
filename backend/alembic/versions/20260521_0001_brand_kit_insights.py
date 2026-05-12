"""Phase 2 / Q3 §6.2 — BrandKitInsight model

Revision ID: 20260521_0001
Revises: 20260520_0002
Create Date: 2026-05-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260521_0001"
down_revision: Union[str, None] = "20260520_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    kind_enum = sa.Enum(
        "performance",
        "voice",
        "audience",
        "hashtag",
        "timing",
        "other",
        name="brandkitinsightkind",
    )
    kind_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "brand_kit_insights",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.UUID(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "brand_kit_id",
            sa.UUID(),
            sa.ForeignKey("brand_kits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", kind_enum, nullable=False),
        sa.Column("summary", sa.String(512), nullable=False),
        sa.Column("detail", sa.Text, nullable=True),
        sa.Column(
            "confidence", sa.Float, nullable=False, server_default="0.7"
        ),
        sa.Column(
            "source_run_id",
            sa.UUID(),
            sa.ForeignKey("workflow_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("generated_by_agent", sa.String(64), nullable=True),
        sa.Column("payload_json", sa.JSON, nullable=True),
        sa.Column(
            "is_human_edited",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "is_archived",
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
        "ix_brand_kit_insights_organization_id",
        "brand_kit_insights",
        ["organization_id"],
    )
    op.create_index(
        "ix_brand_kit_insights_brand_kit_id",
        "brand_kit_insights",
        ["brand_kit_id"],
    )
    op.create_index(
        "ix_brand_kit_insights_brand_kit_kind_confidence",
        "brand_kit_insights",
        ["brand_kit_id", "kind", "confidence"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_brand_kit_insights_brand_kit_kind_confidence",
        table_name="brand_kit_insights",
    )
    op.drop_index(
        "ix_brand_kit_insights_brand_kit_id",
        table_name="brand_kit_insights",
    )
    op.drop_index(
        "ix_brand_kit_insights_organization_id",
        table_name="brand_kit_insights",
    )
    op.drop_table("brand_kit_insights")
    sa.Enum(name="brandkitinsightkind").drop(op.get_bind(), checkfirst=True)
