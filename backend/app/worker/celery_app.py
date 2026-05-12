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
from celery.schedules import crontab

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
        # Phase 4 — calendar dispatcher: every minute, scan for due
        # scheduled posts and hand each one to the per-post publisher.
        "scan-due-scheduled-posts": {
            "task": "app.worker.tasks.publishing.scan_due_scheduled_posts",
            "schedule": 60.0,
        },
        # Phase 8.2 — identity resolution. Runs at 05:30 UTC, before
        # the rollups so attribution + dashboard see the widest possible
        # journey for each lead. Stamps lead_id on anonymous touchpoints
        # that share a visitor_id with an identified touchpoint.
        "resolve-visitor-identities": {
            "task": "app.worker.tasks.identity.resolve_visitor_identities",
            "schedule": crontab(hour=5, minute=30),
        },
        # Phase 8.1 — daily analytics rollups. Runs at 06:00 UTC, just
        # after typical EU/US-east overnight data settles. Computes
        # yesterday's per-channel + org-wide rollups for every Org.
        "compute-daily-rollups": {
            "task": "app.worker.tasks.analytics.compute_daily_rollups",
            "schedule": crontab(hour=6, minute=0),
        },
        # Phase 8.3 — attribution computation. Runs at 06:30 UTC,
        # after the rollups so the dashboard reads consistent data.
        # Builds AttributionResult rows for yesterday's conversions
        # under first-touch / last-touch / linear models.
        "compute-attribution": {
            "task": "app.worker.tasks.attribution.compute_attribution",
            "schedule": crontab(hour=6, minute=30),
        },
        # Phase 8.8 follow-up — daily lead rescore + auto stage
        # promotion (new → mql → sql → customer based on the 0-100
        # score crossing 25 / 60 / 90 thresholds). Runs at 04:30 UTC
        # before the rollups so the lifecycle Kanban shows consistent
        # stage counts.
        "recompute-lead-scores": {
            "task": "app.worker.tasks.lead_scoring.recompute_lead_scores",
            "schedule": crontab(hour=4, minute=30),
        },
        # Phase 9 — Analyst Agent weekly report. Runs Monday at
        # 07:00 UTC (after Sunday's rollups have settled). 3σ
        # anomaly-detection over the past 21 days; Markdown
        # narrative written into AuditEvent.payload_json.
        "weekly-analyst-report": {
            "task": "app.worker.tasks.analyst.weekly_analyst_report",
            "schedule": crontab(day_of_week=1, hour=7, minute=0),
        },
        # Phase 7.x — sequence runner. Every 5 min advance any
        # SequenceMembership whose next_run_at has elapsed.
        "advance-sequence-memberships": {
            "task": "app.worker.tasks.sequences.advance_due_memberships",
            "schedule": 300.0,
        },
        # Phase 7.x — segment materializer. Nightly at 03:30 UTC.
        "materialize-segments": {
            "task": "app.worker.tasks.segments.materialize_all_segments",
            "schedule": crontab(hour=3, minute=30),
        },
        # Phase 11 / I3 — hourly cost-cap evaluation. Warns at 80%,
        # writes a "cost_cap.blocked" audit row at 100%. Per-Org
        # config under autonomy_posture_json.{daily_cap_usd, weekly_cap_usd}.
        "evaluate-cost-caps-hourly": {
            "task": "app.worker.tasks.cost_caps.evaluate_all_orgs",
            "schedule": crontab(minute=15),
        },
    },
)
