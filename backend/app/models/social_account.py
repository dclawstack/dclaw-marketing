"""SocialAccount — a connected publishing endpoint (Theme C2 / Phase 5).

Per v2.0 §6.1. An Org can have N accounts on each platform (e.g. 3 X
handles, 2 LinkedIn company pages). Each account is a separate OAuth
grant; tokens stored encrypted at rest (using cryptography.fernet
keyed off a per-Org data key — wired in Phase 6 / Theme D when the
MCP secret store lands; in Phase 5 we keep a plaintext column behind
a name-mangle to make it clear it's interim).
"""

from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SocialPlatform(str, enum.Enum):
    """Every platform we publish to (or stub for) — keep in sync with
    `ScheduledPostChannel` (10 surfaces in Phase 4) plus the
    Phase 5 expansion to 23.
    """

    # Phase 4 set (also valid as ScheduledPostChannel)
    linkedin = "linkedin"
    x = "x"
    instagram = "instagram"
    threads = "threads"
    bluesky = "bluesky"
    facebook = "facebook"
    youtube = "youtube"
    tiktok = "tiktok"
    newsletter = "newsletter"
    blog = "blog"
    # Phase 5 additions
    reddit = "reddit"
    pinterest = "pinterest"
    mastodon = "mastodon"
    snapchat = "snapchat"
    telegram = "telegram"
    whatsapp = "whatsapp"
    discord = "discord"
    quora = "quora"
    medium = "medium"
    substack = "substack"
    beehiiv = "beehiiv"
    ghost = "ghost"
    wordpress = "wordpress"
    webflow = "webflow"
    spotify_podcasters = "spotify_podcasters"


class SocialAccountStatus(str, enum.Enum):
    active = "active"
    reauth_required = "reauth_required"
    revoked = "revoked"


class SocialAccount(Base):
    """One social account / publishing endpoint connected to an Org."""

    __tablename__ = "social_accounts"
    __table_args__ = (
        # Block duplicate connections for the same (org, platform, handle).
        UniqueConstraint(
            "organization_id",
            "platform",
            "handle",
            name="uq_social_account_org_platform_handle",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    platform: Mapped[SocialPlatform] = mapped_column(
        SQLEnum(SocialPlatform), nullable=False
    )
    handle: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Auth material. In Phase 5 we keep plaintext access_token + a JSON
    # blob for metadata (refresh_token, expires_at, etc). Phase 6 swaps
    # this for an encrypted Connection row with per-Org Fernet keys.
    # Renamed `_interim_access_token` so it's clear we'll migrate it.
    _interim_access_token: Mapped[str | None] = mapped_column(
        "interim_access_token", Text, nullable=True
    )
    auth_metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    scopes: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    is_default_for_platform: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    status: Mapped[SocialAccountStatus] = mapped_column(
        SQLEnum(SocialAccountStatus),
        nullable=False,
        default=SocialAccountStatus.active,
    )
    last_health_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_publish_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class ProjectSocialAccount(Base):
    """Many-to-many join — projects opt into a subset of an org's
    connected accounts.
    """

    __tablename__ = "project_social_accounts"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "social_account_id",
            name="uq_project_social_account",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    social_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("social_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
