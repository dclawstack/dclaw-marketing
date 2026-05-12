"""Daily Lead-scoring beat task — Phase 8.8 follow-up.

Walks every Lead in every Org, recomputes the 0-100 score from its
LeadActivity timeline (via app.services.lead_scoring.compute_score),
writes the new value to Lead.score, and emits a
LeadActivity(kind=stage_change) row when the score crosses one of the
MQL / SQL thresholds:

  score < 25            → stage = new
  25 ≤ score < 60       → stage = mql
  60 ≤ score < 90       → stage = sql
  score ≥ 90            → stage = customer  (only auto-promoted if
                                                already at sql)

The promotion is **monotonic** within this task: a leading drop in
score never demotes the stage automatically — only sales-ops actions
demote (a separate manual flow). This avoids flapping when a lead
goes quiet for a week.

Run cadence: daily at 04:30 UTC (before the rollups so the lifecycle
Kanban + dashboards see consistent data).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select

from app.models.lead import Lead, LeadActivity, LeadActivityKind, LeadStage
from app.services.lead_scoring import compute_score
from app.worker.celery_app import celery_app
from app.worker.helpers import SyncSession


# Score → stage thresholds. Order matters — bisect from the top.
_THRESHOLDS: list[tuple[float, LeadStage]] = [
    (90.0, LeadStage.customer),
    (60.0, LeadStage.sql),
    (25.0, LeadStage.mql),
    (0.0, LeadStage.new),
]

# Monotonic order — a lead can only move *forward* through these on
# auto-promotion. customer/churned are sticky on the manual side.
_STAGE_ORDER: dict[LeadStage, int] = {
    LeadStage.visitor: 0,
    LeadStage.new: 1,
    LeadStage.mql: 2,
    LeadStage.sql: 3,
    LeadStage.customer: 4,
    LeadStage.churned: -1,  # not promoted out of automatically
}


def _stage_from_score(score: float) -> LeadStage:
    for cutoff, stage in _THRESHOLDS:
        if score >= cutoff:
            return stage
    return LeadStage.new


def _should_promote(current: LeadStage, proposed: LeadStage) -> bool:
    if current == LeadStage.churned:
        return False
    return _STAGE_ORDER.get(proposed, 0) > _STAGE_ORDER.get(current, 0)


def _lead_to_dict(lead: Lead) -> dict:
    return {
        "stage": lead.stage,
        "domain": lead.domain,
        "linkedin_url": lead.linkedin_url,
        "company": lead.company,
        "phone": lead.phone,
    }


@celery_app.task(name="app.worker.tasks.lead_scoring.recompute_lead_scores")
def recompute_lead_scores() -> dict:
    """One-shot pass over every Lead. Returns a summary dict suitable
    for the Celery result backend + the Analyst Agent's daily report."""
    now = datetime.now(tz=timezone.utc)
    rescored = 0
    promoted = 0
    with SyncSession() as session:
        leads = session.execute(select(Lead)).scalars().all()
        for lead in leads:
            activities = (
                session.execute(
                    select(LeadActivity).where(LeadActivity.lead_id == lead.id)
                )
                .scalars()
                .all()
            )
            breakdown = compute_score(_lead_to_dict(lead), activities, now=now)
            new_score = breakdown.score
            lead.score = new_score
            rescored += 1

            proposed = _stage_from_score(new_score)
            if _should_promote(lead.stage, proposed):
                from_stage = lead.stage
                lead.stage = proposed
                session.add(
                    LeadActivity(
                        lead_id=lead.id,
                        organization_id=lead.organization_id,
                        kind=LeadActivityKind.stage_change,
                        summary=(
                            f"auto-promoted {from_stage.value} → {proposed.value} "
                            f"(score {new_score})"
                        ),
                        payload_json={
                            "from": from_stage.value,
                            "to": proposed.value,
                            "score": new_score,
                            "auto": True,
                        },
                        occurred_at=now,
                    )
                )
                promoted += 1
        session.commit()

    return {"rescored": rescored, "promoted": promoted, "at": now.isoformat()}
