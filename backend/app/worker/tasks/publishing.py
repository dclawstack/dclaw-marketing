"""Phase 4 — ScheduledPost dispatcher.

The Celery beat scheduler runs `scan_due_scheduled_posts` every minute.
It finds queued posts whose `scheduled_at <= now()` and hands each off
to `publish_scheduled_post`, which in v0 sets status to
`would_publish` (the real per-channel adapters land in Phase 5).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.models.scheduled_post import (
    ScheduledPost,
    ScheduledPostStatus,
)
from app.worker.celery_app import celery_app
from app.worker.helpers import SyncSession


@celery_app.task(name="app.worker.tasks.publishing.scan_due_scheduled_posts")
def scan_due_scheduled_posts() -> dict:
    """Beat-driven scan. Dispatches one task per due post."""
    now = datetime.now(tz=timezone.utc)
    dispatched: list[str] = []
    with SyncSession() as session:
        result = session.execute(
            select(ScheduledPost).where(
                ScheduledPost.status == ScheduledPostStatus.queued,
                ScheduledPost.scheduled_at <= now,
            )
        )
        for p in result.scalars().all():
            publish_scheduled_post.delay(str(p.id))
            dispatched.append(str(p.id))
    return {"dispatched": dispatched, "count": len(dispatched)}


@celery_app.task(
    name="app.worker.tasks.publishing.publish_scheduled_post",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def publish_scheduled_post(self, post_id: str) -> dict:
    """Per-post publisher.

    v0: no real channel adapters exist yet. We flip the post to
    `would_publish` and record the time so the UI can show the loop
    closing. Phase 5 replaces the body with per-channel publisher
    calls keyed off `post.channel`.
    """
    from uuid import UUID

    pid = UUID(post_id)
    with SyncSession() as session:
        post = session.get(ScheduledPost, pid)
        if post is None:
            return {"post_id": post_id, "result": "missing"}

        # Idempotency — only act on queued.
        if post.status != ScheduledPostStatus.queued:
            return {
                "post_id": post_id,
                "result": "skipped",
                "current_status": post.status.value,
            }

        post.status = ScheduledPostStatus.publishing
        session.commit()

        try:
            # ----- Real publisher would dispatch by channel here. -----
            # adapter = ADAPTERS[post.channel]  # Phase 5
            # adapter.publish(post)
            # post.status = ScheduledPostStatus.published
            #
            # v0 stub:
            result_payload = {
                "stub": True,
                "channel": post.channel.value,
                "note": (
                    "Phase 5 channel adapter not yet wired. Real publisher "
                    "lands when SocialAccount + OAuth flows ship."
                ),
            }
            post.publisher_response = result_payload
            post.published_at = datetime.now(tz=timezone.utc)
            post.status = ScheduledPostStatus.would_publish
            session.commit()
        except Exception as exc:  # pragma: no cover — defensive
            post.status = ScheduledPostStatus.failed
            post.error_message = str(exc)
            session.commit()
            raise

    return {
        "post_id": post_id,
        "result": "would_publish",
        "channel": post.channel.value,
    }
