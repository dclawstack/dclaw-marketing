"""Phase 4 — ScheduledPost table (calendar + dispatcher)

Revision ID: 20260514_0001
Revises: 20260513_0001
Create Date: 2026-05-14

Adds the scheduled_posts table that the Celery beat dispatcher scans
each cycle. A row carries a copy + asset references + channel +
scheduled_at; the dispatcher flips status when due time arrives.

Per Phase 4 of IMPLEMENTATION-PLAN.md. The real per-channel publishers
land in Phase 5 — for now the dispatcher transitions to
`would_publish` so the loop can be demonstrated end-to-end.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260514_0001"
down_revision: Union[str, None] = "20260513_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CHANNEL_VALUES = (
    "linkedin",
    "x",
    "instagram",
    "threads",
    "bluesky",
    "facebook",
    "youtube",
    "tiktok",
    "newsletter",
    "blog",
)

STATUS_VALUES = (
    "queued",
    "publishing",
    "published",
    "failed",
    "cancelled",
    "would_publish",
)


def upgrade() -> None:
    op.create_table(
        "scheduled_posts",
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
            "parent_campaign_id",
            sa.Uuid(),
            sa.ForeignKey("campaigns.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "channel",
            sa.Enum(*CHANNEL_VALUES, name="scheduledpostchannel"),
            nullable=False,
        ),
        sa.Column("asset_ids", sa.JSON(), nullable=True),
        sa.Column("copy", sa.Text(), nullable=True),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column(
            "scheduled_at", sa.DateTime(timezone=True), nullable=False, index=True
        ),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("publisher_response", sa.JSON(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(*STATUS_VALUES, name="scheduledpoststatus"),
            nullable=False,
            server_default="queued",
        ),
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
    )
    op.create_index(
        "ix_scheduled_posts_status_scheduled_at",
        "scheduled_posts",
        ["status", "scheduled_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_scheduled_posts_status_scheduled_at", table_name="scheduled_posts"
    )
    op.drop_table("scheduled_posts")
    sa.Enum(name="scheduledpoststatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="scheduledpostchannel").drop(op.get_bind(), checkfirst=True)
