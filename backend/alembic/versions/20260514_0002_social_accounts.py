"""Phase 5 — SocialAccount + ProjectSocialAccount tables

Revision ID: 20260514_0002
Revises: 20260514_0001
Create Date: 2026-05-14

Adds connected-publishing-endpoint storage. SocialAccount holds an
OAuth grant (or pasted access token for manual flows) for one
account on one platform within one org. ProjectSocialAccount lets
each project opt into a subset of the org's connected accounts.

Per IMPLEMENTATION-PLAN §Phase 5 / v2.0 §6.1.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260514_0002"
down_revision: Union[str, None] = "20260514_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PLATFORM_VALUES = (
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
    "reddit",
    "pinterest",
    "mastodon",
    "snapchat",
    "telegram",
    "whatsapp",
    "discord",
    "quora",
    "medium",
    "substack",
    "beehiiv",
    "ghost",
    "wordpress",
    "webflow",
    "spotify_podcasters",
)

STATUS_VALUES = ("active", "reauth_required", "revoked")


def upgrade() -> None:
    op.create_table(
        "social_accounts",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "platform",
            sa.Enum(*PLATFORM_VALUES, name="socialplatform"),
            nullable=False,
        ),
        sa.Column("handle", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("avatar_url", sa.Text(), nullable=True),
        sa.Column("interim_access_token", sa.Text(), nullable=True),
        sa.Column("auth_metadata_json", sa.JSON(), nullable=True),
        sa.Column("scopes", sa.JSON(), nullable=True),
        sa.Column(
            "is_default_for_platform",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "status",
            sa.Enum(*STATUS_VALUES, name="socialaccountstatus"),
            nullable=False,
            server_default="active",
        ),
        sa.Column("last_health_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_publish_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
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
            "organization_id",
            "platform",
            "handle",
            name="uq_social_account_org_platform_handle",
        ),
    )

    op.create_table(
        "project_social_accounts",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "project_id",
            sa.Uuid(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "social_account_id",
            sa.Uuid(),
            sa.ForeignKey("social_accounts.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "project_id",
            "social_account_id",
            name="uq_project_social_account",
        ),
    )


def downgrade() -> None:
    op.drop_table("project_social_accounts")
    op.drop_table("social_accounts")
    sa.Enum(name="socialaccountstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="socialplatform").drop(op.get_bind(), checkfirst=True)
