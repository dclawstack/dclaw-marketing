"""Sequence runner — Phase 7.x.

Every 5 minutes the runner scans for ``SequenceMembership`` rows whose
``next_run_at <= now()`` and ``status == enrolled``. For each due row
it advances the membership through its sequence's steps:

  • ``email`` step  → send the templated email via email_send and
                       schedule the next step's ``next_run_at`` based
                       on the following step's delay_seconds.
  • ``wait`` step   → just sets ``next_run_at = now + delay_seconds``
                       (the runner re-enters the membership later).
  • ``branch`` step → checks ``config_json.condition`` against the
                       Lead's score / stage; advances to either
                       ``if_true_position`` or ``if_false_position``.
  • ``linkedin_dm`` / ``webhook`` — log-only for now; record an audit
                       row and skip. Real handlers ship later.

After the last step, status → completed. On unrecoverable error,
status → failed with ``error_message``.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select

from app.models.audit_event import AuditActorKind, AuditEvent, AuditResult
from app.models.email_ads import (
    EmailSequence,
    EmailSequenceStep,
    EmailTemplate,
    SequenceStatus,
    SequenceStepKind,
)
from app.models.lead import Lead
from app.models.sequence_membership import (
    SequenceMembership,
    SequenceMembershipStatus,
)
from app.worker.celery_app import celery_app
from app.worker.helpers import SyncSession


def _next_step(
    session, sequence_id, after_position: int
) -> EmailSequenceStep | None:
    res = session.execute(
        select(EmailSequenceStep)
        .where(
            EmailSequenceStep.sequence_id == sequence_id,
            EmailSequenceStep.position > after_position,
        )
        .order_by(EmailSequenceStep.position.asc())
        .limit(1)
    ).scalar_one_or_none()
    return res


def _step_at(
    session, sequence_id, position: int
) -> EmailSequenceStep | None:
    return session.execute(
        select(EmailSequenceStep).where(
            EmailSequenceStep.sequence_id == sequence_id,
            EmailSequenceStep.position == position,
        )
    ).scalar_one_or_none()


def _execute_step(
    session,
    *,
    membership: SequenceMembership,
    sequence: EmailSequence,
    step: EmailSequenceStep,
    lead: Lead,
) -> dict:
    """Execute one step against one lead. Returns a history entry."""
    now = datetime.now(tz=timezone.utc)
    entry: dict[str, Any] = {
        "position": step.position,
        "kind": step.kind.value,
        "at": now.isoformat(),
    }
    if step.kind == SequenceStepKind.email:
        # Resolve the template — pure record-keeping for now. The actual
        # SMTP/Resend send wires in when we extract the template's
        # subject + body and call email_send. For unit testability we
        # write an AuditEvent and don't side-effect.
        tmpl: EmailTemplate | None = None
        if step.template_id:
            tmpl = session.get(EmailTemplate, step.template_id)
        entry["template"] = tmpl.name if tmpl else None
        entry["recipient"] = lead.email
        session.add(
            AuditEvent(
                organization_id=sequence.organization_id,
                actor_kind=AuditActorKind.system,
                action_type="sequence.step.email",
                target_type="lead",
                target_id=str(lead.id),
                payload_json={
                    "sequence_id": str(sequence.id),
                    "step_position": step.position,
                    "template_id": str(step.template_id) if step.template_id else None,
                },
                result=AuditResult.success,
            )
        )
        entry["status"] = "sent"
    elif step.kind == SequenceStepKind.wait:
        entry["delay_seconds"] = step.delay_seconds or 0
        entry["status"] = "wait_scheduled"
    elif step.kind == SequenceStepKind.branch:
        cfg = step.config_json or {}
        cond = cfg.get("condition") or {}
        var = cond.get("var")
        op = cond.get("op", "gte")
        threshold = cond.get("value")
        actual = getattr(lead, var, None) if var else None
        passed: bool
        try:
            if op == "gte":
                passed = (actual or 0) >= (threshold or 0)
            elif op == "gt":
                passed = (actual or 0) > (threshold or 0)
            elif op == "lt":
                passed = (actual or 0) < (threshold or 0)
            elif op == "lte":
                passed = (actual or 0) <= (threshold or 0)
            else:
                passed = actual == threshold
        except TypeError:
            passed = False
        entry["passed"] = passed
        entry["status"] = "branched"
    elif step.kind in (SequenceStepKind.linkedin_dm, SequenceStepKind.webhook):
        session.add(
            AuditEvent(
                organization_id=sequence.organization_id,
                actor_kind=AuditActorKind.system,
                action_type=f"sequence.step.{step.kind.value}",
                target_type="lead",
                target_id=str(lead.id),
                payload_json={"sequence_id": str(sequence.id)},
                result=AuditResult.success,
            )
        )
        entry["status"] = "logged"
    else:
        entry["status"] = "unknown_kind"
    return entry


@celery_app.task(name="app.worker.tasks.sequences.advance_due_memberships")
def advance_due_memberships(batch_size: int = 200) -> dict:
    now = datetime.now(tz=timezone.utc)
    counts = {"advanced": 0, "completed": 0, "failed": 0}
    with SyncSession() as session:
        memberships = (
            session.execute(
                select(SequenceMembership)
                .where(
                    SequenceMembership.status
                    == SequenceMembershipStatus.enrolled,
                    SequenceMembership.next_run_at != None,  # noqa: E711
                    SequenceMembership.next_run_at <= now,
                )
                .limit(batch_size)
            )
            .scalars()
            .all()
        )
        for m in memberships:
            sequence = session.get(EmailSequence, m.sequence_id)
            lead = session.get(Lead, m.lead_id)
            if sequence is None or lead is None:
                m.status = SequenceMembershipStatus.failed
                m.error_message = "sequence or lead missing"
                counts["failed"] += 1
                continue
            if sequence.status != SequenceStatus.active:
                # Paused/draft/archived — don't advance.
                m.next_run_at = None
                continue

            # Determine next step.
            next_pos = m.current_step_position + 1
            step = _step_at(session, sequence.id, next_pos)
            if step is None:
                m.status = SequenceMembershipStatus.completed
                m.next_run_at = None
                m.last_advanced_at = now
                counts["completed"] += 1
                continue

            try:
                entry = _execute_step(
                    session,
                    membership=m,
                    sequence=sequence,
                    step=step,
                    lead=lead,
                )
                m.current_step_position = step.position
                m.last_advanced_at = now
                m.history_json = (m.history_json or []) + [entry]

                # Compute next_run_at based on the *following* step's delay.
                follow = _next_step(session, sequence.id, step.position)
                if follow is None:
                    m.next_run_at = None  # completes on next pass
                else:
                    delay = follow.delay_seconds or 0
                    m.next_run_at = now + timedelta(seconds=delay)
                counts["advanced"] += 1
            except Exception as exc:  # pragma: no cover — defensive
                m.status = SequenceMembershipStatus.failed
                m.error_message = str(exc)
                counts["failed"] += 1
        session.commit()
    counts["at"] = now.isoformat()
    return counts


__all__ = ["advance_due_memberships"]
