"""Phase 9 — AgentThread + AgentMessage

Revision ID: 20260515_0001
Revises: 20260514_0002
Create Date: 2026-05-15

Persists conversation memory for the agent fleet. Threads are
org-scoped; messages reference a thread + an actor (user / agent /
system / tool). Approved actions link to ApprovalRequest.

Predecessor note: chains off 20260514_0002 (social accounts). The
Phase 6 connections migration (20260514_0003) lands on a separate
PR — alembic will resolve the multi-branch state via merge revision
if both land out of order, but we expect Phase 5 → Phase 6 → Phase 9
ordering on main.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260515_0001"
down_revision: Union[str, None] = "20260514_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


AGENT_KINDS = (
    "conductor",
    "creatives",
    "smm",
    "seo",
    "paid_media",
    "analyst",
    "inbox",
)

MESSAGE_ROLES = ("user", "agent", "system", "tool")


def upgrade() -> None:
    op.create_table(
        "agent_threads",
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
            "parent_thread_id",
            sa.Uuid(),
            sa.ForeignKey("agent_threads.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "kind", sa.Enum(*AGENT_KINDS, name="agentkind"), nullable=False
        ),
        sa.Column("title", sa.String(512), nullable=True),
        sa.Column(
            "started_by_user_id",
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
    )

    op.create_table(
        "agent_messages",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "thread_id",
            sa.Uuid(),
            sa.ForeignKey("agent_threads.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "role",
            sa.Enum(*MESSAGE_ROLES, name="agentmessagerole"),
            nullable=False,
        ),
        sa.Column(
            "agent_kind",
            sa.Enum(*AGENT_KINDS, name="agentkind"),
            nullable=True,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tool_name", sa.String(255), nullable=True),
        sa.Column("tool_arguments", sa.JSON(), nullable=True),
        sa.Column("tool_result", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column(
            "approval_request_id",
            sa.Uuid(),
            sa.ForeignKey("approval_requests.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("agent_messages")
    op.drop_table("agent_threads")
    sa.Enum(name="agentmessagerole").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="agentkind").drop(op.get_bind(), checkfirst=True)
