"""Audit retention pruner (S4-J2).

Daily beat task that deletes AuditEvent rows older than the org's
retention policy. Defaults to 365 days; orgs can override via
`autonomy_posture_json["audit_retention_days"]`.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.audit_event import AuditEvent
from app.models.organization import Organization
from app.worker.celery_app import celery_app

log = logging.getLogger(__name__)


DEFAULT_RETENTION_DAYS = 365


def _engine():
    url = settings.database_url.replace("+asyncpg", "")
    return create_engine(url, pool_pre_ping=True, future=True)


@celery_app.task(name="app.worker.tasks.audit_retention.prune_audit_events")
def prune_audit_events() -> dict:
    engine = _engine()
    pruned = 0
    with Session(engine, future=True) as db:
        orgs = db.execute(select(Organization)).scalars().all()
        for org in orgs:
            posture = org.autonomy_posture_json or {}
            days = int(posture.get("audit_retention_days", DEFAULT_RETENTION_DAYS))
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
            result = db.execute(
                delete(AuditEvent).where(
                    AuditEvent.organization_id == org.id,
                    AuditEvent.created_at < cutoff,
                )
            )
            pruned += result.rowcount or 0
        # Global rows (org_id NULL) → default retention.
        global_cutoff = datetime.now(timezone.utc) - timedelta(
            days=DEFAULT_RETENTION_DAYS
        )
        result = db.execute(
            delete(AuditEvent).where(
                AuditEvent.organization_id.is_(None),
                AuditEvent.created_at < global_cutoff,
            )
        )
        pruned += result.rowcount or 0
        db.commit()
    return {"ok": True, "pruned": pruned}
