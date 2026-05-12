"""Phase 7 — Email / Ads / Sequence / Segment data layer

Revision ID: 20260515_0003
Revises: 20260515_0001
Create Date: 2026-05-15

Predecessor chain: 20260515_0001 (agent_threads). Phase 8's
20260515_0002 (attribution) is parallel; alembic will merge if
both land out of order.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260515_0003"
down_revision: Union[str, None] = "20260515_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


EMAIL_CAMPAIGN_STATUS = ("draft", "scheduled", "sending", "sent", "failed", "cancelled")
SEQUENCE_STATUS = ("draft", "active", "paused", "archived")
SEQUENCE_STEP_KIND = ("email", "wait", "branch", "linkedin_dm", "webhook")
AD_PLATFORM = ("meta", "google", "linkedin", "tiktok", "x")
AD_STATUS = (
    "draft",
    "pending_review",
    "active",
    "paused",
    "rejected",
    "completed",
)


def upgrade() -> None:
    # email_templates
    op.create_table(
        "email_templates",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("slug", sa.String(128), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("subject", sa.String(998), nullable=False),
        sa.Column("body_html", sa.Text(), nullable=True),
        sa.Column("body_text", sa.Text(), nullable=True),
        sa.Column("merge_fields", sa.JSON(), nullable=True),
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
            "organization_id", "slug", name="uq_email_template_org_slug"
        ),
    )

    # email_campaigns
    op.create_table(
        "email_campaigns",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "template_id",
            sa.Uuid(),
            sa.ForeignKey("email_templates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("segment_id", sa.Uuid(), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("open_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("click_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("bounce_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "status",
            sa.Enum(*EMAIL_CAMPAIGN_STATUS, name="emailcampaignstatus"),
            nullable=False,
            server_default="draft",
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

    # email_sequences + steps
    op.create_table(
        "email_sequences",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(*SEQUENCE_STATUS, name="sequencestatus"),
            nullable=False,
            server_default="draft",
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
    op.create_table(
        "email_sequence_steps",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "sequence_id",
            sa.Uuid(),
            sa.ForeignKey("email_sequences.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            sa.Enum(*SEQUENCE_STEP_KIND, name="sequencestepkind"),
            nullable=False,
        ),
        sa.Column(
            "template_id",
            sa.Uuid(),
            sa.ForeignKey("email_templates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("delay_seconds", sa.Integer(), nullable=True),
        sa.Column("config_json", sa.JSON(), nullable=True),
    )

    # ad_accounts + ad_campaigns + ad_sets
    op.create_table(
        "ad_accounts",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "platform", sa.Enum(*AD_PLATFORM, name="adplatform"), nullable=False
        ),
        sa.Column("platform_account_id", sa.String(255), nullable=False),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("currency", sa.String(8), nullable=True),
        sa.Column("connection_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_table(
        "ad_campaigns",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "ad_account_id",
            sa.Uuid(),
            sa.ForeignKey("ad_accounts.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("objective", sa.String(64), nullable=True),
        sa.Column("daily_budget_usd", sa.Float(), nullable=True),
        sa.Column("total_budget_usd", sa.Float(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(*AD_STATUS, name="adstatus"),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_table(
        "ad_sets",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "ad_campaign_id",
            sa.Uuid(),
            sa.ForeignKey("ad_campaigns.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("targeting_json", sa.JSON(), nullable=True),
        sa.Column("daily_budget_usd", sa.Float(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(*AD_STATUS, name="adstatus"),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("creative_asset_ids", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # segments
    op.create_table(
        "segments",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("slug", sa.String(128), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("filter_dsl_json", sa.JSON(), nullable=False),
        sa.Column("last_evaluated_count", sa.Integer(), nullable=True),
        sa.Column("last_evaluated_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint("organization_id", "slug", name="uq_segment_org_slug"),
    )


def downgrade() -> None:
    op.drop_table("segments")
    op.drop_table("ad_sets")
    op.drop_table("ad_campaigns")
    op.drop_table("ad_accounts")
    op.drop_table("email_sequence_steps")
    op.drop_table("email_sequences")
    op.drop_table("email_campaigns")
    op.drop_table("email_templates")
    for name in (
        "adstatus",
        "adplatform",
        "sequencestepkind",
        "sequencestatus",
        "emailcampaignstatus",
    ):
        sa.Enum(name=name).drop(op.get_bind(), checkfirst=True)
