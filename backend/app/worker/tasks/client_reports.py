"""Weekly + monthly client report writer — Phase 10 / M.

Two periodic Celery tasks:

  • ``emit_weekly_client_reports`` — every Monday at 07:30 UTC, for
    each Org, build the past-7-day HTML report, upload it to MinIO at
    ``client-reports/<org>/weekly/<YYYY-MM-DD>.html``, and write a
    matching AuditEvent so the eventual /reports/weekly UI can read
    the index.
  • ``emit_monthly_client_reports`` — on the 1st at 08:00 UTC, same
    for the past 30 days.

Embeddable read-only dashboard URLs come for free — once a report is
uploaded the storage key is signed via the existing presigned-URL
helper.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.models.audit_event import AuditActorKind, AuditEvent, AuditResult
from app.models.organization import Organization
from app.services.client_pdf_report import build_report_html
from app.services.storage import sync_s3_client
from app.worker.celery_app import celery_app
from app.worker.helpers import SyncSession


def _upload(html: str, org_id, period_label: str, when: datetime) -> str:
    from app.core.config import settings as _settings

    key = (
        f"client-reports/{org_id}/{period_label}/{when.strftime('%Y-%m-%d')}.html"
    )
    try:
        client = sync_s3_client()
        client.put_object(
            Bucket=_settings.s3_bucket,
            Key=key,
            Body=html.encode("utf-8"),
            ContentType="text/html",
        )
    except Exception:  # pragma: no cover — MinIO may not be available
        pass
    return key


def _run(period_label: str, period_days: int) -> dict:
    now = datetime.now(tz=timezone.utc)
    counts = {"orgs": 0, "uploaded": 0}
    with SyncSession() as session:
        for org in session.execute(select(Organization)).scalars():
            counts["orgs"] += 1
            try:
                html = build_report_html(
                    session,
                    org.id,
                    period_label=period_label,
                    period_days=period_days,
                    now=now,
                )
            except Exception:  # pragma: no cover — keep sweeping
                continue
            key = _upload(html, org.id, period_label, now)
            session.add(
                AuditEvent(
                    organization_id=org.id,
                    actor_kind=AuditActorKind.system,
                    action_type=f"client_report.{period_label}",
                    target_type="organization",
                    target_id=str(org.id),
                    payload_json={
                        "storage_key": key,
                        "period_days": period_days,
                        "size_bytes": len(html),
                    },
                    result=AuditResult.success,
                )
            )
            counts["uploaded"] += 1
        session.commit()
    counts["at"] = now.isoformat()
    return counts


@celery_app.task(
    name="app.worker.tasks.client_reports.emit_weekly_client_reports"
)
def emit_weekly_client_reports() -> dict:
    return _run("weekly", 7)


@celery_app.task(
    name="app.worker.tasks.client_reports.emit_monthly_client_reports"
)
def emit_monthly_client_reports() -> dict:
    return _run("monthly", 30)


__all__ = [
    "emit_weekly_client_reports",
    "emit_monthly_client_reports",
]
