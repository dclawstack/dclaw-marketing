"""Weekly freshness re-ingestion — Phase 2.x / Q4.

Knowledge sources of type ``url`` and ``git`` drift over time — the
linked page gets edited, the repo's README changes. Without periodic
re-ingestion the knowledge graph slowly diverges from reality.

This beat task scans ``ingestion_sources`` once per week and re-queues
any URL/git source whose last successful update is older than the
configured staleness threshold (default 7 days). Files and zips are
left alone — they're snapshots, not live streams.

The re-ingestion path is the same as the original POST /ingest call:
the source row's status is reset to ``queued`` and the existing
ingestion task picks it up.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models.ingestion import (
    IngestionSource,
    IngestionSourceType,
    IngestionStatus,
)
from app.worker.celery_app import celery_app
from app.worker.helpers import SyncSession


_STALE_AFTER_DAYS = 7
_REFRESHABLE_TYPES = (IngestionSourceType.url, IngestionSourceType.git)


@celery_app.task(name="app.worker.tasks.freshness.refresh_stale_sources")
def refresh_stale_sources(batch_size: int = 100) -> dict:
    """Re-queue URL + git sources that haven't been refreshed in 7+ days.

    Returns a summary dict with the count of sources refreshed.
    """
    now = datetime.now(tz=timezone.utc)
    cutoff = now - timedelta(days=_STALE_AFTER_DAYS)
    refreshed = 0
    with SyncSession() as session:
        rows = (
            session.execute(
                select(IngestionSource)
                .where(
                    IngestionSource.source_type.in_(_REFRESHABLE_TYPES),
                    IngestionSource.status == IngestionStatus.ready,
                    IngestionSource.updated_at < cutoff,
                )
                .limit(batch_size)
            )
            .scalars()
            .all()
        )
        for src in rows:
            # Reset to queued so the existing ingestion worker re-fetches
            # + re-chunks. Older DocumentChunks are kept until the new
            # batch lands; downstream KG search remains available.
            src.status = IngestionStatus.queued
            src.error_message = None
            refreshed += 1
        session.commit()

    # Late import — the ingestion worker module pulls in heavy deps and
    # we don't want to load it on celery_app startup.
    from app.worker.tasks.ingestion import process_ingestion_source

    with SyncSession() as session:
        queued = (
            session.execute(
                select(IngestionSource.id).where(
                    IngestionSource.status == IngestionStatus.queued,
                    IngestionSource.source_type.in_(_REFRESHABLE_TYPES),
                )
                .limit(batch_size)
            )
        ).all()
        for (sid,) in queued:
            try:
                process_ingestion_source.delay(str(sid))
            except Exception:  # pragma: no cover — broker not available
                pass

    return {
        "refreshed": refreshed,
        "at": now.isoformat(),
        "stale_after_days": _STALE_AFTER_DAYS,
    }


__all__ = ["refresh_stale_sources"]
