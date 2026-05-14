"""Registered Celery tasks.

This module is `include`-d by celery_app.py so all task functions
declared in submodules here are auto-registered when the worker
starts.

As the platform grows, each subsystem adds its own submodule:
- tasks/ingestion.py — Theme Q2 file/url/git/zip ingestion
- tasks/generation.py — Theme B3 LLM / image / video / voice gen
- tasks/publishing.py — Theme C2 scheduled posts
- tasks/analytics.py — Theme F1 daily rollups
- tasks/agents.py — Theme G1+ agent runs
"""

# Re-export the example task so it's registered without needing
# explicit submodule imports.
from app.worker.tasks.analytics import compute_daily_rollups  # noqa: F401
from app.worker.tasks.attribution import compute_attribution  # noqa: F401
from app.worker.tasks.email_send import deliver_approved_email  # noqa: F401
from app.worker.tasks.example import sleep_and_progress  # noqa: F401
from app.worker.tasks.gdpr import export_organization_data  # noqa: F401
from app.worker.tasks.identity import resolve_visitor_identities  # noqa: F401
from app.worker.tasks.ingestion import ingest_asset  # noqa: F401
from app.worker.tasks.model_registry import (  # noqa: F401
    discover_provider_models,
    health_check_all_providers,
)
from app.worker.tasks.audit_retention import prune_audit_events  # noqa: F401
from app.worker.tasks.publishing import (  # noqa: F401
    publish_scheduled_post,
    scan_due_scheduled_posts,
)

__all__ = [
    "compute_daily_rollups",
    "compute_attribution",
    "deliver_approved_email",
    "export_organization_data",
    "resolve_visitor_identities",
    "sleep_and_progress",
    "ingest_asset",
    "discover_provider_models",
    "health_check_all_providers",
    "publish_scheduled_post",
    "scan_due_scheduled_posts",
]
