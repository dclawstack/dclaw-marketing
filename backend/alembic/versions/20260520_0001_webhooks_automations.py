"""Theme D4 — generic webhook receiver + Automation rules

Revision ID: 20260520_0001
Revises: 20260519_0002
Create Date: 2026-05-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260520_0001"
down_revision: Union[str, None] = "20260519_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    status_enum = sa.Enum(
        "pending",
        "processing",
        "processed",
        "failed",
        "ignored",
        name="webhookeventstatus",
    )
    status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "webhooks",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.UUID(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("source", sa.String(64), nullable=True),
        sa.Column("token", sa.String(64), nullable=False, unique=True),
        sa.Column("secret", sa.String(255), nullable=True),
        sa.Column(
            "enabled", sa.Boolean, server_default=sa.text("true"), nullable=False
        ),
        sa.Column("last_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "received_count", sa.Integer, server_default="0", nullable=False
        ),
        sa.Column(
            "created_by_user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_webhooks_organization_id", "webhooks", ["organization_id"]
    )
    op.create_index("ix_webhooks_token", "webhooks", ["token"], unique=True)

    op.create_table(
        "webhook_events",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "webhook_id",
            sa.UUID(),
            sa.ForeignKey("webhooks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            sa.UUID(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("payload_json", sa.JSON, nullable=True),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("status", status_enum, server_default="pending", nullable=False),
        sa.Column("matched_automation_ids", sa.JSON, nullable=True),
        sa.Column("error_message", sa.String(1024), nullable=True),
    )
    op.create_index(
        "ix_webhook_events_webhook_id", "webhook_events", ["webhook_id"]
    )
    op.create_index(
        "ix_webhook_events_organization_id", "webhook_events", ["organization_id"]
    )
    op.create_index(
        "ix_webhook_events_status_received_at",
        "webhook_events",
        ["status", "received_at"],
    )
    op.create_index(
        "ix_webhook_events_webhook_id_received_at",
        "webhook_events",
        ["webhook_id", "received_at"],
    )

    op.create_table(
        "automations",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.UUID(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "enabled", sa.Boolean, server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "webhook_id",
            sa.UUID(),
            sa.ForeignKey("webhooks.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("source_filter", sa.String(64), nullable=True),
        sa.Column("filter_json", sa.JSON, nullable=True),
        sa.Column("actions_json", sa.JSON, nullable=True),
        sa.Column(
            "created_by_user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
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
        sa.Column(
            "last_matched_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "match_count", sa.Integer, server_default="0", nullable=False
        ),
    )
    op.create_index(
        "ix_automations_organization_id", "automations", ["organization_id"]
    )
    op.create_index(
        "ix_automations_webhook_id", "automations", ["webhook_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_automations_webhook_id", table_name="automations")
    op.drop_index("ix_automations_organization_id", table_name="automations")
    op.drop_table("automations")
    op.drop_index(
        "ix_webhook_events_webhook_id_received_at",
        table_name="webhook_events",
    )
    op.drop_index(
        "ix_webhook_events_status_received_at", table_name="webhook_events"
    )
    op.drop_index(
        "ix_webhook_events_organization_id", table_name="webhook_events"
    )
    op.drop_index(
        "ix_webhook_events_webhook_id", table_name="webhook_events"
    )
    op.drop_table("webhook_events")
    op.drop_index("ix_webhooks_token", table_name="webhooks")
    op.drop_index("ix_webhooks_organization_id", table_name="webhooks")
    op.drop_table("webhooks")
    sa.Enum(name="webhookeventstatus").drop(op.get_bind(), checkfirst=True)
