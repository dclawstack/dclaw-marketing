"""Example task — sleeps for `total_seconds`, reporting progress.

Used in development + as the canonical "does the worker actually
work?" smoke test. Replace or delete once real tasks (ingestion,
generation, publishing) start landing.
"""

import time
from uuid import UUID

from app.models.job import JobStatus
from app.worker.celery_app import celery_app
from app.worker.helpers import update_job


@celery_app.task(name="app.worker.tasks.sleep_and_progress", bind=True)
def sleep_and_progress(self, job_id: str, total_seconds: int = 10) -> dict:
    """Sleep for `total_seconds`, updating progress every second.

    Returns a result_json summary on success. Demonstrates the
    job-update lifecycle that real tasks should follow.
    """
    jid = UUID(job_id)
    update_job(
        jid,
        status=JobStatus.running,
        celery_task_id=self.request.id if hasattr(self.request, "id") else None,
        progress_label="starting",
    )
    try:
        for second in range(1, total_seconds + 1):
            time.sleep(1)
            update_job(
                jid,
                progress=second / total_seconds,
                progress_label=f"elapsed {second}/{total_seconds}s",
            )
    except Exception as exc:
        update_job(jid, status=JobStatus.failed, error_message=str(exc))
        raise

    result = {"slept_seconds": total_seconds}
    update_job(
        jid,
        status=JobStatus.succeeded,
        progress=1.0,
        progress_label="done",
        result_json=result,
    )
    return result
