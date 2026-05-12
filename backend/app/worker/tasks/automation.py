"""Automation runner — Theme D4 / Phase 6.

Periodic Celery task that consumes pending WebhookEvent rows and
dispatches the actions of any Automation whose filter matches.

Action execution is currently log-only — each matched action writes
an AuditEvent describing what would happen. The real action
implementations (create_lead, push_to_crm, schedule_post, …) land
incrementally; the runner already has the dispatch slot for each.
This keeps the runner-side change-set focused on the loop semantics:
filter matching, the audit trail, the status transitions, and the
beat schedule entry.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.models.audit_event import AuditActorKind, AuditEvent, AuditResult
from app.models.webhook import (
    Automation,
    Webhook,
    WebhookEvent,
    WebhookEventStatus,
)
from app.worker.celery_app import celery_app
from app.worker.helpers import SyncSession


# ---------- Filter matching -----------------------------------------------


def _match_filter(payload: dict | None, filter_json: dict | None) -> bool:
    """Flat top-level key match. Empty filter matches everything."""
    if not filter_json:
        return True
    if not isinstance(payload, dict):
        return False
    for k, expected in filter_json.items():
        if payload.get(k) != expected:
            return False
    return True


def _automation_matches(
    auto: Automation,
    event: WebhookEvent,
    webhook: Webhook | None,
) -> bool:
    if not auto.enabled:
        return False
    # Webhook id match (when set on the Automation)
    if auto.webhook_id is not None and auto.webhook_id != event.webhook_id:
        return False
    # Source filter match (against the Webhook's source label)
    if auto.source_filter:
        if not webhook or webhook.source != auto.source_filter:
            return False
    return _match_filter(event.payload_json, auto.filter_json)


# ---------- Action dispatch -----------------------------------------------


def _dispatch_action(
    session,
    automation: Automation,
    event: WebhookEvent,
    action: dict[str, Any],
) -> dict:
    """Emit an audit row describing the action. Real handlers replace
    the audit-only branch incrementally."""
    kind = action.get("action") or "log_only"
    params = action.get("params") or {}
    audit = AuditEvent(
        organization_id=automation.organization_id,
        actor_kind=AuditActorKind.system,
        action_type=f"automation.{kind}",
        target_type="webhook_event",
        target_id=str(event.id),
        payload_json={
            "automation_id": str(automation.id),
            "automation_name": automation.name,
            "params": params,
            "event_payload": event.payload_json,
        },
        result=AuditResult.success,
    )
    session.add(audit)
    return {"action": kind, "audit_id": None}


# ---------- The task -------------------------------------------------------


@celery_app.task(name="app.worker.tasks.automation.process_pending_events")
def process_pending_events(batch_size: int = 100) -> dict:
    """Read up-to ``batch_size`` pending WebhookEvent rows, match
    against the Automation table for each event's Org, dispatch
    actions, and flip status to processed / ignored / failed.
    """
    now = datetime.now(tz=timezone.utc)
    counts = {"processed": 0, "ignored": 0, "failed": 0}
    with SyncSession() as session:
        events = (
            session.execute(
                select(WebhookEvent)
                .where(WebhookEvent.status == WebhookEventStatus.pending)
                .order_by(WebhookEvent.received_at.asc())
                .limit(batch_size)
            )
            .scalars()
            .all()
        )
        for event in events:
            event.status = WebhookEventStatus.processing
            session.flush()

            webhook = session.get(Webhook, event.webhook_id)
            automations = (
                session.execute(
                    select(Automation).where(
                        Automation.organization_id == event.organization_id,
                        Automation.enabled.is_(True),
                    )
                )
                .scalars()
                .all()
            )
            matched_ids: list[str] = []
            try:
                for auto in automations:
                    if _automation_matches(auto, event, webhook):
                        for action in (auto.actions_json or []):
                            _dispatch_action(session, auto, event, action)
                        auto.match_count = (auto.match_count or 0) + 1
                        auto.last_matched_at = now
                        matched_ids.append(str(auto.id))
                event.matched_automation_ids = matched_ids
                event.status = (
                    WebhookEventStatus.processed
                    if matched_ids
                    else WebhookEventStatus.ignored
                )
                if matched_ids:
                    counts["processed"] += 1
                else:
                    counts["ignored"] += 1
            except Exception as exc:  # pragma: no cover — defensive
                event.status = WebhookEventStatus.failed
                event.error_message = str(exc)
                counts["failed"] += 1
            session.flush()
        session.commit()
    return counts


__all__ = ["process_pending_events"]
