"""Phase 7.4 — EmailEvent table for webhook ingest

Revision ID: 20260519_0002
Revises: 20260519_0001
Create Date: 2026-05-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260519_0002"
down_revision: Union[str, None] = "20260519_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    provider_enum = sa.Enum(
        "resend",
        "sendgrid",
        "postmark",
        "mailchimp",
        "convertkit",
        "beehiiv",
        name="emaileventprovider",
    )
    kind_enum = sa.Enum(
        "delivered",
        "opened",
        "clicked",
        "replied",
        "bounced",
        "complained",
        "unsubscribed",
        "failed",
        "other",
        name="emaileventkind",
    )
    provider_enum.create(op.get_bind(), checkfirst=True)
    kind_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "email_events",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.UUID(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("provider", provider_enum, nullable=False),
        sa.Column("kind", kind_enum, nullable=False),
        sa.Column("provider_message_id", sa.String(255), nullable=True),
        sa.Column("recipient", sa.String(320), nullable=True),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("payload_json", sa.JSON, nullable=True),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "lead_activity_id",
            sa.UUID(),
            sa.ForeignKey("lead_activities.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_email_events_organization_id", "email_events", ["organization_id"]
    )
    op.create_index(
        "ix_email_events_occurred_at", "email_events", ["occurred_at"]
    )
    op.create_index(
        "ix_email_events_org_kind_occ",
        "email_events",
        ["organization_id", "kind", "occurred_at"],
    )
    op.create_index(
        "ix_email_events_recipient", "email_events", ["recipient"]
    )
    op.create_index(
        "ix_email_events_provider_message_id",
        "email_events",
        ["provider", "provider_message_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_email_events_provider_message_id", table_name="email_events")
    op.drop_index("ix_email_events_recipient", table_name="email_events")
    op.drop_index("ix_email_events_org_kind_occ", table_name="email_events")
    op.drop_index("ix_email_events_occurred_at", table_name="email_events")
    op.drop_index("ix_email_events_organization_id", table_name="email_events")
    op.drop_table("email_events")
    sa.Enum(name="emaileventkind").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="emaileventprovider").drop(op.get_bind(), checkfirst=True)
