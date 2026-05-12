"""Analyst Agent — Monday-morning anomaly + narrative beat task.

Runs weekly (Monday at 07:00 UTC). For every Org it:

  1. Walks the per-Org AnalyticsRollup rows for the past 21 days.
  2. Extracts a flat (day, value) sequence per top-level metric in
     ``rollup.metric_json``.
  3. Runs the 3σ anomaly detector.
  4. Renders a Markdown narrative.
  5. Stores the narrative as an AuditEvent (action_type="analyst.weekly_report")
     so the Org's audit log + an eventual /reports/weekly UI can read it.

Real narrative generation via Claude lands later (the Analyst-agent
PR); this task ships the foundation so anomalies are detected and
recorded weekly without the LLM hop.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models.attribution import AnalyticsRollup
from app.models.audit_event import AuditActorKind, AuditEvent, AuditResult
from app.models.organization import Organization
from app.services.anomaly import MetricPoint, detect_anomalies, render_narrative
from app.worker.celery_app import celery_app
from app.worker.helpers import SyncSession


_HISTORY_DAYS = 21


def _build_series(
    rollups: list[AnalyticsRollup],
) -> dict[str, list[MetricPoint]]:
    """Group rollups by metric key → list of MetricPoint."""
    series: dict[str, list[MetricPoint]] = defaultdict(list)
    for r in rollups:
        if not isinstance(r.metric_json, dict):
            continue
        for k, v in r.metric_json.items():
            if isinstance(v, (int, float)):
                series[k].append(
                    MetricPoint(day=r.day.date(), value=float(v))
                )
    return series


@celery_app.task(name="app.worker.tasks.analyst.weekly_analyst_report")
def weekly_analyst_report() -> dict:
    """One row per Org per week. Returns a summary dict."""
    now = datetime.now(tz=timezone.utc)
    cutoff = now - timedelta(days=_HISTORY_DAYS)
    summary: dict = {"orgs_scanned": 0, "reports_emitted": 0}
    with SyncSession() as session:
        for org in session.execute(select(Organization)).scalars():
            summary["orgs_scanned"] += 1
            rollups = (
                session.execute(
                    select(AnalyticsRollup)
                    .where(
                        AnalyticsRollup.organization_id == org.id,
                        AnalyticsRollup.scope == "org",
                        AnalyticsRollup.day >= cutoff,
                    )
                    .order_by(AnalyticsRollup.day.asc())
                )
                .scalars()
                .all()
            )
            if not rollups:
                continue
            series = _build_series(rollups)
            sections: list[str] = []
            total_anoms = 0
            for metric, points in series.items():
                anoms = detect_anomalies(points)
                total_anoms += len(anoms)
                sections.append(render_narrative(anoms, metric_label=metric))
            narrative = "\n\n".join(sections) or "No metrics this period."
            audit = AuditEvent(
                organization_id=org.id,
                actor_kind=AuditActorKind.system,
                action_type="analyst.weekly_report",
                target_type="organization",
                target_id=str(org.id),
                payload_json={
                    "anomalies": total_anoms,
                    "metrics_scanned": list(series.keys()),
                    "narrative_markdown": narrative,
                    "period_days": _HISTORY_DAYS,
                },
                result=AuditResult.success,
            )
            session.add(audit)
            summary["reports_emitted"] += 1
        session.commit()
    summary["at"] = now.isoformat()
    return summary


__all__ = ["weekly_analyst_report"]
