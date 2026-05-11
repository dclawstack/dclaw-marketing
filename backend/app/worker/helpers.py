"""Helpers Celery tasks use to write back into the Job row.

Celery tasks run in a separate process (not the FastAPI event loop)
so they need their own DB engine. This module provides a small sync
helper that opens a session and updates a Job atomically.
"""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.job import Job, JobStatus


# Sync engine for use inside Celery tasks (Celery is sync-native).
# We rewrite the async URL to its sync counterpart on the fly so we
# don't need a second DATABASE_URL setting.
_sync_url = settings.database_url.replace("+asyncpg", "")
_sync_engine = create_engine(_sync_url, pool_pre_ping=True)
SyncSession = sessionmaker(_sync_engine, expire_on_commit=False)


def update_job(
    job_id: UUID,
    *,
    status: JobStatus | None = None,
    progress: float | None = None,
    progress_label: str | None = None,
    result_json: dict | None = None,
    result_url: str | None = None,
    error_message: str | None = None,
    celery_task_id: str | None = None,
) -> None:
    """Atomically update a Job row's progress / result / error fields.

    Called by tasks to publish progress updates. The SSE stream endpoint
    polls the DB and surfaces these changes to the client.
    """
    with SyncSession() as session:
        job = session.get(Job, job_id)
        if job is None:
            return  # job was deleted while task running — silently drop

        now = datetime.now(timezone.utc)
        if status is not None:
            job.status = status
            if status == JobStatus.running and job.started_at is None:
                job.started_at = now
            if status in (JobStatus.succeeded, JobStatus.failed, JobStatus.canceled):
                job.ended_at = now
                # Progress always reaches 1.0 on success regardless of how
                # the task reported it during its run.
                if status == JobStatus.succeeded:
                    job.progress = 1.0
        if progress is not None:
            job.progress = max(0.0, min(1.0, progress))
        if progress_label is not None:
            job.progress_label = progress_label
        if result_json is not None:
            job.result_json = result_json
        if result_url is not None:
            job.result_url = result_url
        if error_message is not None:
            job.error_message = error_message
        if celery_task_id is not None:
            job.celery_task_id = celery_task_id

        session.commit()
