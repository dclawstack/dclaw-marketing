"""initial baseline — captures the v1.0 schema (Campaign / Lead / AnalyticsEvent)

Revision ID: 20260512_0001
Revises:
Create Date: 2026-05-12

This is the foundational migration. Every later revision is built on top
of this. It re-creates the schema that already existed on disk (built
via Base.metadata.create_all in conftest.py) so production deployments
have a deterministic upgrade path from an empty database.

Tables created: campaigns, leads, analytics_events.
Enum types created: campaigntype, campaignstatus, leadstatus, eventtype.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers used by Alembic
revision: str = "20260512_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # campaigns
    op.create_table(
        "campaigns",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "type",
            sa.Enum("email", "social", "ppc", "content", name="campaigntype"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "draft",
                "scheduled",
                "active",
                "paused",
                "completed",
                name="campaignstatus",
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("budget", sa.Float(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
    )

    # leads
    op.create_table(
        "leads",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("first_name", sa.String(length=255), nullable=True),
        sa.Column("last_name", sa.String(length=255), nullable=True),
        sa.Column("company", sa.String(length=255), nullable=True),
        sa.Column("source", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "new",
                "contacted",
                "qualified",
                "converted",
                "lost",
                name="leadstatus",
            ),
            nullable=False,
            server_default="new",
        ),
        sa.Column(
            "campaign_id",
            sa.UUID(),
            sa.ForeignKey("campaigns.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.UniqueConstraint("email", name="uq_leads_email"),
    )
    op.create_index("ix_leads_campaign_id", "leads", ["campaign_id"])

    # analytics_events
    op.create_table(
        "analytics_events",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "campaign_id",
            sa.UUID(),
            sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "event_type",
            sa.Enum(
                "impression",
                "click",
                "conversion",
                "bounce",
                name="eventtype",
            ),
            nullable=False,
        ),
        sa.Column("value", sa.Float(), nullable=False, server_default="0"),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_analytics_events_campaign_id", "analytics_events", ["campaign_id"])
    op.create_index("ix_analytics_events_recorded_at", "analytics_events", ["recorded_at"])


def downgrade() -> None:
    op.drop_index("ix_analytics_events_recorded_at", table_name="analytics_events")
    op.drop_index("ix_analytics_events_campaign_id", table_name="analytics_events")
    op.drop_table("analytics_events")

    op.drop_index("ix_leads_campaign_id", table_name="leads")
    op.drop_table("leads")

    op.drop_table("campaigns")

    sa.Enum(name="eventtype").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="leadstatus").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="campaignstatus").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="campaigntype").drop(op.get_bind(), checkfirst=False)
