"""Phase 8.5 — Lead 2.0 extensions + LeadActivity + LeadNote

Revision ID: 20260517_0002
Revises: 20260517_0001
Create Date: 2026-05-17

Adds:
- New columns on the existing leads table: phone, domain, linkedin_url,
  stage (enum), score, enrichment_json, utm_source/medium/campaign/
  content/term, last_activity_at.
- lead_activities table — typed timeline events with payload_json.
- lead_notes table — free-text internal annotations.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260517_0002"
down_revision: Union[str, None] = "20260517_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LEAD_STAGE = ("visitor", "new", "mql", "sql", "customer", "churned")
LEAD_ACTIVITY_KIND = (
    "email_open", "email_click", "email_reply",
    "page_view", "form_submit", "call", "meeting",
    "note", "enrichment", "crm_sync",
    "status_change", "stage_change", "other",
)


def upgrade() -> None:
    # ----- Lead column additions -----
    op.add_column("leads", sa.Column("phone", sa.String(64), nullable=True))
    op.add_column(
        "leads", sa.Column("domain", sa.String(255), nullable=True)
    )
    op.create_index("ix_leads_domain", "leads", ["domain"])
    op.add_column("leads", sa.Column("linkedin_url", sa.Text(), nullable=True))
    op.add_column(
        "leads",
        sa.Column(
            "stage",
            sa.Enum(*LEAD_STAGE, name="leadstage"),
            nullable=False,
            server_default="new",
        ),
    )
    op.create_index("ix_leads_stage", "leads", ["stage"])
    op.add_column("leads", sa.Column("score", sa.Float(), nullable=True))
    op.create_index("ix_leads_score", "leads", ["score"])
    op.add_column("leads", sa.Column("enrichment_json", sa.JSON(), nullable=True))
    for col in ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"):
        op.add_column("leads", sa.Column(col, sa.String(255), nullable=True))
    op.add_column(
        "leads",
        sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_leads_last_activity_at", "leads", ["last_activity_at"])

    # ----- lead_activities -----
    op.create_table(
        "lead_activities",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "lead_id",
            sa.Uuid(),
            sa.ForeignKey("leads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "kind",
            sa.Enum(*LEAD_ACTIVITY_KIND, name="leadactivitykind"),
            nullable=False,
        ),
        sa.Column("summary", sa.String(512), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_lead_activities_lead_id", "lead_activities", ["lead_id"])
    op.create_index("ix_lead_activities_organization_id", "lead_activities", ["organization_id"])
    op.create_index("ix_lead_activities_kind", "lead_activities", ["kind"])
    op.create_index("ix_lead_activities_occurred_at", "lead_activities", ["occurred_at"])

    # ----- lead_notes -----
    op.create_table(
        "lead_notes",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "lead_id",
            sa.Uuid(),
            sa.ForeignKey("leads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "author_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("body", sa.Text(), nullable=False),
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
    op.create_index("ix_lead_notes_lead_id", "lead_notes", ["lead_id"])
    op.create_index("ix_lead_notes_organization_id", "lead_notes", ["organization_id"])
    op.create_index("ix_lead_notes_author_user_id", "lead_notes", ["author_user_id"])


def downgrade() -> None:
    op.drop_index("ix_lead_notes_author_user_id", table_name="lead_notes")
    op.drop_index("ix_lead_notes_organization_id", table_name="lead_notes")
    op.drop_index("ix_lead_notes_lead_id", table_name="lead_notes")
    op.drop_table("lead_notes")

    op.drop_index("ix_lead_activities_occurred_at", table_name="lead_activities")
    op.drop_index("ix_lead_activities_kind", table_name="lead_activities")
    op.drop_index("ix_lead_activities_organization_id", table_name="lead_activities")
    op.drop_index("ix_lead_activities_lead_id", table_name="lead_activities")
    op.drop_table("lead_activities")
    op.execute("DROP TYPE IF EXISTS leadactivitykind")

    op.drop_index("ix_leads_last_activity_at", table_name="leads")
    op.drop_column("leads", "last_activity_at")
    for col in ("utm_term", "utm_content", "utm_campaign", "utm_medium", "utm_source"):
        op.drop_column("leads", col)
    op.drop_column("leads", "enrichment_json")
    op.drop_index("ix_leads_score", table_name="leads")
    op.drop_column("leads", "score")
    op.drop_index("ix_leads_stage", table_name="leads")
    op.drop_column("leads", "stage")
    op.execute("DROP TYPE IF EXISTS leadstage")
    op.drop_column("leads", "linkedin_url")
    op.drop_index("ix_leads_domain", table_name="leads")
    op.drop_column("leads", "domain")
    op.drop_column("leads", "phone")
