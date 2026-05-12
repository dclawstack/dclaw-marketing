"""Phase 8 — Touchpoint + Conversion + AttributionResult + AnalyticsRollup

Revision ID: 20260515_0002
Revises: 20260515_0001
Create Date: 2026-05-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260515_0002"
down_revision: Union[str, None] = "20260515_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ATTRIBUTION_MODELS = (
    "first_touch",
    "last_touch",
    "linear",
    "time_decay",
    "markov",
)


def upgrade() -> None:
    op.create_table(
        "touchpoints",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "lead_id",
            sa.Uuid(),
            sa.ForeignKey("leads.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("source", sa.String(64), nullable=False, index=True),
        sa.Column("channel", sa.String(64), nullable=True, index=True),
        sa.Column(
            "campaign_id",
            sa.Uuid(),
            sa.ForeignKey("campaigns.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("utm_source", sa.String(255), nullable=True),
        sa.Column("utm_medium", sa.String(255), nullable=True),
        sa.Column("utm_campaign", sa.String(255), nullable=True),
        sa.Column("utm_content", sa.String(255), nullable=True),
        sa.Column("utm_term", sa.String(255), nullable=True),
        sa.Column("page_url", sa.Text(), nullable=True),
        sa.Column("referrer_url", sa.Text(), nullable=True),
        sa.Column("visitor_id", sa.String(128), nullable=True, index=True),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            index=True,
        ),
        sa.Column("payload_json", sa.JSON(), nullable=True),
    )

    op.create_table(
        "conversions",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "lead_id",
            sa.Uuid(),
            sa.ForeignKey("leads.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("amount_usd", sa.Float(), nullable=True),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            index=True,
        ),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
    )

    op.create_table(
        "attribution_results",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "conversion_id",
            sa.Uuid(),
            sa.ForeignKey("conversions.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "touchpoint_id",
            sa.Uuid(),
            sa.ForeignKey("touchpoints.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "model",
            sa.Enum(*ATTRIBUTION_MODELS, name="attributionmodel"),
            nullable=False,
        ),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("credited_amount_usd", sa.Float(), nullable=True),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "analytics_rollups",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("scope", sa.String(64), nullable=False, index=True),
        sa.Column("scope_key", sa.String(128), nullable=False, index=True),
        sa.Column(
            "day",
            sa.DateTime(timezone=True),
            nullable=False,
            index=True,
        ),
        sa.Column("metric_json", sa.JSON(), nullable=False),
        sa.Column(
            "computed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("analytics_rollups")
    op.drop_table("attribution_results")
    op.drop_table("conversions")
    op.drop_table("touchpoints")
    sa.Enum(name="attributionmodel").drop(op.get_bind(), checkfirst=True)
