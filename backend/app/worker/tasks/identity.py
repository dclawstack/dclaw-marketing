"""Identity resolution (Phase 8.2).

Most touchpoints are recorded against a ``visitor_id`` (anonymous
browser cookie / device id) before the visitor identifies themselves
by, say, filling out a form. Once they do, a Conversion or a logged-
in event ties a ``lead_id`` to that same ``visitor_id``.

This job propagates that linkage backwards: any prior Touchpoint
that shares a known visitor_id but has no ``lead_id`` gets the
lead_id stamped on it. That widens the attribution journey lookup
(Phase 8.3) without us needing to change the query shape.

Heuristic — intentionally conservative for v1:
  For each (org, visitor_id), if at least one Touchpoint already has
  a non-null lead_id, copy that lead_id onto every other Touchpoint
  with the same (org, visitor_id) and a null lead_id.

If multiple distinct lead_ids show up for the same visitor_id (a
shared device, two leads merging later), we keep whatever's already
there for the resolved rows and only fill in the nulls — never
overwrite.
"""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.attribution import Touchpoint
from app.models.organization import Organization
from app.worker.celery_app import celery_app
from app.worker.helpers import SyncSession


def resolve_for_org(session: Session, organization_id: UUID) -> int:
    """Run the resolution heuristic for one org. Returns the count of
    Touchpoints that got a new lead_id stamped on them.
    """
    # Pull all touchpoints with a visitor_id for this org. We intentionally
    # don't filter to "recent" — back-stamping older rows is the whole
    # point.
    rows = (
        session.execute(
            select(
                Touchpoint.id, Touchpoint.visitor_id, Touchpoint.lead_id
            ).where(
                Touchpoint.organization_id == organization_id,
                Touchpoint.visitor_id.is_not(None),
            )
        )
        .all()
    )

    # For each visitor_id, pick the first non-null lead_id encountered.
    chosen_lead: dict[str, UUID] = {}
    nulls_by_visitor: dict[str, list[UUID]] = defaultdict(list)
    for tp_id, visitor_id, lead_id in rows:
        if lead_id is not None:
            chosen_lead.setdefault(visitor_id, lead_id)
        else:
            nulls_by_visitor[visitor_id].append(tp_id)

    stamped = 0
    for visitor_id, tp_ids in nulls_by_visitor.items():
        lead_id = chosen_lead.get(visitor_id)
        if lead_id is None:
            continue
        session.execute(
            update(Touchpoint)
            .where(Touchpoint.id.in_(tp_ids))
            .values(lead_id=lead_id)
        )
        stamped += len(tp_ids)

    return stamped


@celery_app.task(name="app.worker.tasks.identity.resolve_visitor_identities")
def resolve_visitor_identities() -> dict:
    """Beat-driven: iterate orgs, resolve anonymous touchpoints to
    known leads via shared visitor_id.

    Idempotent — a touchpoint that already has a lead_id is never
    re-stamped, so running twice in a row is a no-op on the second run.
    """
    total_stamped = 0
    orgs_touched = 0
    with SyncSession() as session:
        org_ids = session.execute(select(Organization.id)).all()
        for (org_id,) in org_ids:
            n = resolve_for_org(session, org_id)
            if n > 0:
                orgs_touched += 1
                total_stamped += n
        session.commit()

    return {
        "orgs_touched": orgs_touched,
        "touchpoints_stamped": total_stamped,
    }
