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
from app.services.cost_logger import record_cost_sync
from app.services.publishers import PublishResult
from app.services.sandbox import is_sandbox_mode_sync, sandbox_publish_result
from app.services.publishers.bluesky import (
    BlueskyAuthError,
    BlueskyPublishError,
    publish_to_bluesky,
)
from app.services.publishers.discord import (
    DiscordPublishError,
    publish_to_discord,
)
from app.services.publishers.facebook import (
    FacebookAuthError,
    FacebookPublishError,
    publish_to_facebook,
)
from app.services.publishers.instagram import (
    InstagramAuthError,
    InstagramPublishError,
    publish_to_instagram,
)
from app.services.publishers.linkedin import (
    LinkedInAuthError,
    LinkedInPublishError,
    publish_to_linkedin,
)
from app.services.publishers.mastodon import (
    MastodonAuthError,
    MastodonPublishError,
    publish_to_mastodon,
)
from app.services.publishers.pinterest import (
    PinterestAuthError,
    PinterestPublishError,
    publish_to_pinterest,
)
from app.services.publishers.reddit import (
    RedditAuthError,
    RedditPublishError,
    publish_to_reddit,
)
from app.services.publishers.threads import (
    ThreadsAuthError,
    ThreadsPublishError,
    publish_to_threads,
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
    # Phase 11.5 — Sandbox / dry-run. If the org is in sandbox mode,
    # short-circuit to a synthetic stub before touching any provider.
    if is_sandbox_mode_sync(session, post.organization_id):
        return sandbox_publish_result(post.channel.value, post.copy or "")

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

    if post.channel == ScheduledPostChannel.instagram:
        account = _find_active_account(
            session, post.organization_id, SocialPlatform.instagram
        )
        token = account._interim_access_token if account else None
        ig_user_id = (
            (account.auth_metadata_json or {}).get("ig_user_id")
            if account
            else None
        ) or "stub_ig_user"
        image_url = None
        if isinstance(post.publisher_response, dict):
            image_url = post.publisher_response.get("image_url")
        return publish_to_instagram(
            access_token=token,
            ig_user_id=ig_user_id,
            image_url=image_url,
            caption=post.copy or "",
            handle=account.handle if account else None,
        )

    if post.channel == ScheduledPostChannel.mastodon:
        account = _find_active_account(
            session, post.organization_id, SocialPlatform.mastodon
        )
        token = account._interim_access_token if account else None
        instance_url = (
            (account.auth_metadata_json or {}).get("instance_url")
            if account
            else None
        )
        return publish_to_mastodon(
            access_token=token,
            instance_url=instance_url,
            text=post.copy or "",
        )

    if post.channel == ScheduledPostChannel.reddit:
        account = _find_active_account(
            session, post.organization_id, SocialPlatform.reddit
        )
        token = account._interim_access_token if account else None
        subreddit = (
            (account.auth_metadata_json or {}).get("subreddit")
            if account
            else None
        ) or "test"
        return publish_to_reddit(
            access_token=token,
            subreddit=subreddit,
            text=post.copy or "",
        )

    if post.channel == ScheduledPostChannel.discord:
        account = _find_active_account(
            session, post.organization_id, SocialPlatform.discord
        )
        webhook_url = (
            (account.auth_metadata_json or {}).get("webhook_url")
            if account
            else None
        )
        return publish_to_discord(
            webhook_url=webhook_url,
            text=post.copy or "",
            username=account.display_name if account else None,
        )

    if post.channel == ScheduledPostChannel.facebook:
        account = _find_active_account(
            session, post.organization_id, SocialPlatform.facebook
        )
        token = account._interim_access_token if account else None
        page_id = (
            (account.auth_metadata_json or {}).get("page_id")
            if account
            else None
        )
        return publish_to_facebook(
            access_token=token,
            page_id=page_id,
            text=post.copy or "",
        )

    if post.channel == ScheduledPostChannel.threads:
        account = _find_active_account(
            session, post.organization_id, SocialPlatform.threads
        )
        token = account._interim_access_token if account else None
        threads_user_id = (
            (account.auth_metadata_json or {}).get("threads_user_id")
            if account
            else None
        )
        return publish_to_threads(
            access_token=token,
            threads_user_id=threads_user_id,
            text=post.copy or "",
            handle=account.handle if account else None,
        )

    if post.channel == ScheduledPostChannel.pinterest:
        account = _find_active_account(
            session, post.organization_id, SocialPlatform.pinterest
        )
        token = account._interim_access_token if account else None
        board_id = (
            (account.auth_metadata_json or {}).get("board_id")
            if account
            else None
        ) or "stub_board"
        image_url = None
        if isinstance(post.publisher_response, dict):
            image_url = post.publisher_response.get("image_url")
        title = (post.copy or "Untitled").split("\n", 1)[0][:100]
        description = (post.copy or "").split("\n", 1)[-1] if (post.copy and "\n" in post.copy) else ""
        return publish_to_pinterest(
            access_token=token,
            board_id=board_id,
            image_url=image_url,
            title=title,
            description=description,
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
            # Cost ledger — social publishers are free APIs today, but
            # we still record the call so /costs/recent shows publish
            # activity.
            record_cost_sync(
                session,
                organization_id=post.organization_id,
                provider=result.provider,
                kind="publish",
                amount_usd=0.0,
                units=1.0,
                units_kind="post",
                provider_resource=result.remote_id or None,
                metadata={"channel": post.channel.value, "stub": bool(result.raw.get("stub"))},
            )
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
        except (MastodonAuthError, MastodonPublishError) as exc:
            post.status = ScheduledPostStatus.failed
            post.error_message = f"mastodon: {exc}"
            session.commit()
            raise
        except (RedditAuthError, RedditPublishError) as exc:
            post.status = ScheduledPostStatus.failed
            post.error_message = f"reddit: {exc}"
            session.commit()
            raise
        except DiscordPublishError as exc:
            post.status = ScheduledPostStatus.failed
            post.error_message = f"discord: {exc}"
            session.commit()
            raise
        except (PinterestAuthError, PinterestPublishError) as exc:
            post.status = ScheduledPostStatus.failed
            post.error_message = f"pinterest: {exc}"
            session.commit()
            raise
        except (FacebookAuthError, FacebookPublishError) as exc:
            post.status = ScheduledPostStatus.failed
            post.error_message = f"facebook: {exc}"
            session.commit()
            raise
        except (ThreadsAuthError, ThreadsPublishError) as exc:
            post.status = ScheduledPostStatus.failed
            post.error_message = f"threads: {exc}"
            session.commit()
            raise
        except (XAuthError, XPublishError) as exc:
            post.status = ScheduledPostStatus.failed
            post.error_message = f"x: {exc}"
            session.commit()
            raise
        except (InstagramAuthError, InstagramPublishError) as exc:
            post.status = ScheduledPostStatus.failed
            post.error_message = f"instagram: {exc}"
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
