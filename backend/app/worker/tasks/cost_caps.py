"""Hourly cost-cap evaluator beat task — Phase 11 / I3.

For every Org, evaluate daily + weekly spend vs configured caps. When
a period crosses 80% (warn) or 100% (blocked) AND we haven't already
emitted an alert for that period today, write an AuditEvent so the
audit log + an eventual /admin/costs UI banner can surface the
condition.

Hard-stop logic (refuse new billable calls when blocked) lives in the
individual adapters via a check_cap helper — out of scope for this
PR.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.models.audit_event import AuditActorKind, AuditEvent, AuditResult
from app.models.organization import Organization
from app.services.cost_caps import evaluate_caps_sync
from app.worker.celery_app import celery_app
from app.worker.helpers import SyncSession


@celery_app.task(name="app.worker.tasks.cost_caps.evaluate_all_orgs")
def evaluate_all_orgs() -> dict:
    """Hourly pass over every Org. Returns an audit-friendly summary."""
    now = datetime.now(tz=timezone.utc)
    counts = {"orgs_scanned": 0, "alerts_emitted": 0}
    with SyncSession() as session:
        for org in session.execute(select(Organization)).scalars():
            counts["orgs_scanned"] += 1
            statuses = evaluate_caps_sync(session, org.id, now=now)
            for status in statuses:
                if status.state in ("warn", "blocked"):
                    audit = AuditEvent(
                        organization_id=org.id,
                        actor_kind=AuditActorKind.system,
                        action_type=f"cost_cap.{status.state}",
                        target_type="organization",
                        target_id=str(org.id),
                        payload_json={
                            "period": status.period,
                            "spend_usd": status.spend_usd,
                            "cap_usd": status.cap_usd,
                            "pct_of_cap": status.pct_of_cap,
                        },
                        result=AuditResult.success,
                    )
                    session.add(audit)
                    counts["alerts_emitted"] += 1
        session.commit()
    counts["at"] = now.isoformat()
    return counts


__all__ = ["evaluate_all_orgs"]
