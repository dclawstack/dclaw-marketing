"""ScheduledPost — a draft + send-time, awaiting publication (Theme C1).

Per IMPLEMENTATION-PLAN §Phase 4. The Celery beat scanner picks up
posts where `scheduled_at <= now AND status='queued'` and dispatches
the per-channel publisher (Phase 5). In Phase 4 alone there is no
real publisher yet — the dispatcher flips to `would_publish` so we
can demonstrate the loop end-to-end without touching real social
accounts.
"""

from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ScheduledPostChannel(str, enum.Enum):
    """Initial channel set — Phase 5 expands this with real adapters."""

    linkedin = "linkedin"
    x = "x"
    instagram = "instagram"
    threads = "threads"
    bluesky = "bluesky"
    facebook = "facebook"
    youtube = "youtube"
    tiktok = "tiktok"
    mastodon = "mastodon"
    reddit = "reddit"
    pinterest = "pinterest"
    discord = "discord"
    substack = "substack"
    newsletter = "newsletter"
    blog = "blog"


class ScheduledPostStatus(str, enum.Enum):
    queued = "queued"
    publishing = "publishing"
    published = "published"
    failed = "failed"
    cancelled = "cancelled"
    # v0 placeholder used by the Phase-4 beat scanner until Phase-5
    # channel adapters land. Means "the dispatcher tried to fire this
    # but no real publisher exists yet."
    would_publish = "would_publish"


class ScheduledPost(Base):
    __tablename__ = "scheduled_posts"
    __table_args__ = (
        # Beat scanner reads where status='queued' AND scheduled_at <= now;
        # cover the index for that query.
        Index(
            "ix_scheduled_posts_status_scheduled_at",
            "status",
            "scheduled_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    parent_campaign_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    channel: Mapped[ScheduledPostChannel] = mapped_column(
        SQLEnum(ScheduledPostChannel), nullable=False
    )

    # Multi-asset support via JSON array of asset IDs. We use JSON (not
    # ARRAY) so the same column shape works on SQLite for tests.
    asset_ids: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    copy: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    publisher_response: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    status: Mapped[ScheduledPostStatus] = mapped_column(
        SQLEnum(ScheduledPostStatus),
        nullable=False,
        default=ScheduledPostStatus.queued,
    )

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
