"""A4 — audit_events and approval_requests tables

Revision ID: 20260512_0005
Revises: 20260512_0004
Create Date: 2026-05-12

The governance layer: every consequential action writes an
AuditEvent; every Hard-gate action sits in an ApprovalRequest until
a reviewer decides.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260512_0005"
down_revision: Union[str, None] = "20260512_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    actor_kind = sa.Enum("user", "agent", "system", name="auditactorkind")
    actor_kind.create(op.get_bind(), checkfirst=False)
    result_enum = sa.Enum("success", "failure", name="auditresult")
    result_enum.create(op.get_bind(), checkfirst=False)
    approval_status = sa.Enum(
        "pending", "approved", "rejected", "expired", "auto_approved", "canceled",
        name="approvalstatus",
    )
    approval_status.create(op.get_bind(), checkfirst=False)

    # approval_requests first (audit_events FKs into it)
    op.create_table(
        "approval_requests",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "organization_id",
            sa.UUID(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "project_id",
            sa.UUID(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "requested_by_user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("requested_by_agent", sa.String(length=128), nullable=True),
        sa.Column("action_type", sa.String(length=128), nullable=False),
        sa.Column("target_type", sa.String(length=128), nullable=True),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(name="approvalstatus", create_type=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "decided_by_user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decision_reason", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index("ix_approval_requests_organization_id", "approval_requests", ["organization_id"])
    op.create_index("ix_approval_requests_project_id", "approval_requests", ["project_id"])
    op.create_index("ix_approval_requests_action_type", "approval_requests", ["action_type"])
    op.create_index("ix_approval_requests_status", "approval_requests", ["status"])
    op.create_index("ix_approval_requests_created_at", "approval_requests", ["created_at"])

    # audit_events
    op.create_table(
        "audit_events",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "organization_id",
            sa.UUID(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "actor_kind",
            sa.Enum(name="auditactorkind", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "actor_user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("actor_agent", sa.String(length=128), nullable=True),
        sa.Column("action_type", sa.String(length=128), nullable=False),
        sa.Column("target_type", sa.String(length=128), nullable=True),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column(
            "result",
            sa.Enum(name="auditresult", create_type=False),
            nullable=False,
            server_default="success",
        ),
        sa.Column("error_message", sa.String(length=2048), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column(
            "approval_request_id",
            sa.UUID(),
            sa.ForeignKey("approval_requests.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_audit_events_organization_id", "audit_events", ["organization_id"])
    op.create_index("ix_audit_events_actor_kind", "audit_events", ["actor_kind"])
    op.create_index("ix_audit_events_actor_user_id", "audit_events", ["actor_user_id"])
    op.create_index("ix_audit_events_actor_agent", "audit_events", ["actor_agent"])
    op.create_index("ix_audit_events_action_type", "audit_events", ["action_type"])
    op.create_index("ix_audit_events_target_type", "audit_events", ["target_type"])
    op.create_index("ix_audit_events_target_id", "audit_events", ["target_id"])
    op.create_index("ix_audit_events_approval_request_id", "audit_events", ["approval_request_id"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])


def downgrade() -> None:
    for ix in (
        "ix_audit_events_created_at",
        "ix_audit_events_approval_request_id",
        "ix_audit_events_target_id",
        "ix_audit_events_target_type",
        "ix_audit_events_action_type",
        "ix_audit_events_actor_agent",
        "ix_audit_events_actor_user_id",
        "ix_audit_events_actor_kind",
        "ix_audit_events_organization_id",
    ):
        op.drop_index(ix, table_name="audit_events")
    op.drop_table("audit_events")

    for ix in (
        "ix_approval_requests_created_at",
        "ix_approval_requests_status",
        "ix_approval_requests_action_type",
        "ix_approval_requests_project_id",
        "ix_approval_requests_organization_id",
    ):
        op.drop_index(ix, table_name="approval_requests")
    op.drop_table("approval_requests")

    sa.Enum(name="approvalstatus").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="auditresult").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="auditactorkind").drop(op.get_bind(), checkfirst=False)
