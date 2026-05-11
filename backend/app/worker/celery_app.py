"""Celery app config.

Connects to Redis (broker + result backend). Tasks live in
`app.worker.tasks` and are auto-discovered.

To run a worker locally:
    cd backend
    celery -A app.worker.celery_app worker --loglevel=info

To run the scheduler (Celery Beat) for cron-like periodic tasks:
    celery -A app.worker.celery_app beat --loglevel=info
"""

from celery import Celery

from app.core.config import settings


celery_app = Celery(
    "dclaw_marketing",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_acks_late=True,             # ack only after task completes — survives crashes
    task_reject_on_worker_lost=True, # re-queue if a worker disappears mid-task
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",
    # Result expiration: keep results for 7 days, then GC.
    result_expires=60 * 60 * 24 * 7,
    # Timezone handling — store everything in UTC.
    enable_utc=True,
    timezone="UTC",
    # Worker concurrency tuned for I/O-heavy LLM / HTTP work, not CPU.
    worker_prefetch_multiplier=1,
    # Beat schedule lives here — extended by per-feature tasks as the
    # platform grows (Q4 freshness re-crawls, F1 daily analytics rollups,
    # etc.).
    beat_schedule={
        # "freshness-recrawl-urls": {
        #     "task": "app.worker.tasks.ingestion.recrawl_subscribed_urls",
        #     "schedule": timedelta(hours=6),
        # },
    },
)
