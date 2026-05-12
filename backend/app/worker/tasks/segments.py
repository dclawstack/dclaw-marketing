"""Segment materializer — Phase 7.x.

Nightly Celery beat task that re-evaluates each Segment's filter
against the Org's Lead population and writes the matching count back
to ``Segment.last_evaluated_count`` + ``last_evaluated_at``.

The filter DSL (``Segment.filter_dsl_json``) is intentionally flat for
v1::

    {
      "stage": "mql",                — exact match
      "score__gte": 60,              — numeric comparator suffix
      "company__contains": "acme",   — substring match
      "domain__in": ["x.com", "y.io"],
      "any_of": [{"stage": "mql"}, {"stage": "sql"}],  — OR group
    }

Comparator suffixes: __eq (default), __neq, __gt, __gte, __lt, __lte,
__in, __contains, __startswith, __endswith.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.models.email_ads import Segment
from app.models.lead import Lead
from app.worker.celery_app import celery_app
from app.worker.helpers import SyncSession


_SUFFIXES = (
    "__eq",
    "__neq",
    "__gt",
    "__gte",
    "__lt",
    "__lte",
    "__in",
    "__contains",
    "__startswith",
    "__endswith",
)


def _eval_predicate(lead: Lead, key: str, expected: Any) -> bool:
    field, op = key, "__eq"
    for suffix in _SUFFIXES:
        if key.endswith(suffix):
            field = key[: -len(suffix)]
            op = suffix
            break
    actual = getattr(lead, field, None)
    # Enum → value
    if hasattr(actual, "value"):
        actual = actual.value
    try:
        if op == "__eq":
            return actual == expected
        if op == "__neq":
            return actual != expected
        if op == "__gt":
            return float(actual) > float(expected)
        if op == "__gte":
            return float(actual) >= float(expected)
        if op == "__lt":
            return float(actual) < float(expected)
        if op == "__lte":
            return float(actual) <= float(expected)
        if op == "__in":
            return actual in (expected or [])
        if op == "__contains":
            return expected in (actual or "")
        if op == "__startswith":
            return (actual or "").startswith(expected)
        if op == "__endswith":
            return (actual or "").endswith(expected)
    except (TypeError, ValueError):
        return False
    return False


def lead_matches_filter(lead: Lead, filter_dsl: dict | None) -> bool:
    """Returns True when the lead matches the (possibly nested) filter."""
    if not filter_dsl:
        return True  # empty filter ≡ everyone
    # Top-level keys are AND'd; ``any_of`` lists are OR'd within.
    for key, value in filter_dsl.items():
        if key == "any_of" and isinstance(value, list):
            ok = any(lead_matches_filter(lead, sub) for sub in value)
            if not ok:
                return False
            continue
        if not _eval_predicate(lead, key, value):
            return False
    return True


@celery_app.task(name="app.worker.tasks.segments.materialize_all_segments")
def materialize_all_segments() -> dict:
    """Nightly: refresh last_evaluated_count for every Segment."""
    now = datetime.now(tz=timezone.utc)
    counts = {"segments": 0}
    with SyncSession() as session:
        segments = session.execute(select(Segment)).scalars().all()
        for seg in segments:
            counts["segments"] += 1
            leads = (
                session.execute(
                    select(Lead).where(
                        Lead.organization_id == seg.organization_id
                    )
                )
                .scalars()
                .all()
            )
            n = sum(
                1
                for lead in leads
                if lead_matches_filter(lead, seg.filter_dsl_json)
            )
            seg.last_evaluated_count = n
            seg.last_evaluated_at = now
        session.commit()
    counts["at"] = now.isoformat()
    return counts


__all__ = ["lead_matches_filter", "materialize_all_segments"]
