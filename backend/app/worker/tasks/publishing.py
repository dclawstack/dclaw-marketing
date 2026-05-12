"""Phase 4 — ScheduledPost dispatcher (Phases 5.1 Bluesky + 5.2 LinkedIn).

The Celery beat scheduler runs `scan_due_scheduled_posts` every minute.
It finds queued posts whose `scheduled_at <= now()` and hands each off
to `publish_scheduled_post`, which:

  - dispatches to a real per-channel publisher when one exists (Phase
    5 onward), and
  - falls back to the v0 `would_publish` stub for channels that
    don't have an adapter yet.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.models.scheduled_post import (
    ScheduledPost,
    ScheduledPostChannel,
    ScheduledPostStatus,
)
from app.models.social_account import SocialAccount, SocialPlatform
from app.services.publishers import PublishResult
from app.services.publishers.bluesky import (
    BlueskyAuthError,
    BlueskyPublishError,
    publish_to_bluesky,
)
from app.services.publishers.linkedin import (
    LinkedInAuthError,
    LinkedInPublishError,
    publish_to_linkedin,
)
from app.services.publishers.x import (
    XAuthError,
    XPublishError,
    publish_to_x,
)
from app.worker.celery_app import celery_app
from app.worker.helpers import SyncSession


def _find_active_account(
    session, organization_id, platform: SocialPlatform
) -> SocialAccount | None:
    """Pick the default-or-first SocialAccount for the given platform."""
    accounts = (
        session.execute(
            select(SocialAccount).where(
                SocialAccount.organization_id == organization_id,
                SocialAccount.platform == platform,
            )
        )
        .scalars()
        .all()
    )
    if not accounts:
        return None
    # Prefer the default-marked one; otherwise return the first.
    for a in accounts:
        if a.is_default_for_platform:
            return a
    return accounts[0]


def _dispatch_publish(post: ScheduledPost, session) -> PublishResult:
    """Pick the right per-channel publisher. Returns the publisher's
    result on success; raises on failure (caller marks the post as
    `failed`).
    """
    if post.channel == ScheduledPostChannel.bluesky:
        account = _find_active_account(
            session, post.organization_id, SocialPlatform.bluesky
        )
        handle = account.handle if account else "stub.bsky.social"
        password = account._interim_access_token if account else None
        return publish_to_bluesky(
            handle=handle,
            app_password=password,
            text=post.copy or "",
        )

    if post.channel == ScheduledPostChannel.linkedin:
        account = _find_active_account(
            session, post.organization_id, SocialPlatform.linkedin
        )
        token = account._interim_access_token if account else None
        author_urn = (
            (account.auth_metadata_json or {}).get("author_urn")
            if account
            else None
        ) or "urn:li:person:stub"
        return publish_to_linkedin(
            access_token=token,
            author_urn=author_urn,
            text=post.copy or "",
        )

    if post.channel == ScheduledPostChannel.x:
        account = _find_active_account(
            session, post.organization_id, SocialPlatform.x
        )
        handle = account.handle if account else "stub"
        token = account._interim_access_token if account else None
        return publish_to_x(
            access_token=token,
            handle=handle,
            text=post.copy or "",
        )

    # No adapter for this channel yet — fall back to the v0 stub so
    # the rest of the loop still closes.
    return PublishResult(
        provider=post.channel.value,
        remote_id="",
        permalink=None,
        raw={
            "stub": True,
            "channel": post.channel.value,
            "note": (
                "Phase 5 channel adapter not yet wired. Real publisher "
                "lands when SocialAccount + OAuth flows ship."
            ),
        },
    )


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

    Dispatches to the right per-channel adapter via ``_dispatch_publish``.
    Channels with no adapter fall back to a `would_publish` stub so the
    rest of the pipeline still completes — this keeps the demo flow
    moving even while OAuth onboarding is incomplete.
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
            result = _dispatch_publish(post, session)
            post.publisher_response = {
                "provider": result.provider,
                "remote_id": result.remote_id,
                "permalink": result.permalink,
                "raw": result.raw,
            }
            post.published_at = datetime.now(tz=timezone.utc)
            # If the adapter returned a real provider response (no
            # `stub: True`), mark the post as fully published.
            if result.raw.get("stub"):
                post.status = ScheduledPostStatus.would_publish
            else:
                post.status = ScheduledPostStatus.published
            session.commit()
        except (BlueskyAuthError, BlueskyPublishError) as exc:
            post.status = ScheduledPostStatus.failed
            post.error_message = f"bluesky: {exc}"
            session.commit()
            raise
        except (LinkedInAuthError, LinkedInPublishError) as exc:
            post.status = ScheduledPostStatus.failed
            post.error_message = f"linkedin: {exc}"
            session.commit()
            raise
        except (XAuthError, XPublishError) as exc:
            post.status = ScheduledPostStatus.failed
            post.error_message = f"x: {exc}"
            session.commit()
            raise
        except Exception as exc:  # pragma: no cover — defensive
            post.status = ScheduledPostStatus.failed
            post.error_message = str(exc)
            session.commit()
            raise

    return {
        "post_id": post_id,
        "result": post.status.value,
        "channel": post.channel.value,
        "remote_id": (post.publisher_response or {}).get("remote_id"),
    }
