"""Cost-cap evaluation + confidence-threshold escalation (Phase 11 / I3).

Two related guards that read the same per-Org config under
``Organization.autonomy_posture_json``:

  • ``daily_cap_usd`` / ``weekly_cap_usd`` — soft caps. The evaluator
    returns a ``CostCapStatus`` so a beat task or the agent inner
    loop can act on them. Warn at 80%, hard-stop at 100%.

  • ``confidence_thresholds`` — per-action floor. When an agent says
    "I want to do action X with confidence 0.6" and the threshold for
    X is 0.7, the action escalates to Hard-gate regardless of the
    org's posture.

Both are pure helpers — caller decides what to do with the result
(Slack DM the admin, write an AuditEvent, file an ApprovalRequest).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ops import CostLedger
from app.models.organization import Organization


# ---------- Cost cap evaluation -------------------------------------------


@dataclass(frozen=True, slots=True)
class CostCapStatus:
    organization_id: str
    period: str  # "day" | "week"
    spend_usd: float
    cap_usd: float | None
    pct_of_cap: float | None  # None when cap is unset
    state: str  # "ok" | "warn" | "blocked" | "no_cap"


def _autonomy(org: Organization) -> dict:
    return org.autonomy_posture_json or {}


def evaluate_caps_sync(
    session: Session,
    organization_id,
    *,
    now: datetime | None = None,
) -> list[CostCapStatus]:
    """Compute daily + weekly spend vs the Org's configured caps.

    Returns a list with at most two entries (one per period). When a
    cap isn't set for the period, ``state`` is ``"no_cap"`` and
    ``pct_of_cap`` is ``None``.
    """
    clock = now or datetime.now(tz=timezone.utc)
    org = session.get(Organization, organization_id)
    if org is None:
        return []
    autonomy = _autonomy(org)
    day_cap = autonomy.get("daily_cap_usd")
    week_cap = autonomy.get("weekly_cap_usd")
    out: list[CostCapStatus] = []

    day_start = clock.replace(hour=0, minute=0, second=0, microsecond=0)
    day_spend = float(
        session.execute(
            select(func.coalesce(func.sum(CostLedger.amount_usd), 0))
            .where(
                CostLedger.organization_id == organization_id,
                CostLedger.created_at >= day_start,
            )
        ).scalar()
        or 0
    )
    week_start = day_start - timedelta(days=clock.weekday())
    week_spend = float(
        session.execute(
            select(func.coalesce(func.sum(CostLedger.amount_usd), 0))
            .where(
                CostLedger.organization_id == organization_id,
                CostLedger.created_at >= week_start,
            )
        ).scalar()
        or 0
    )

    out.append(_one_status(str(organization_id), "day", day_spend, day_cap))
    out.append(_one_status(str(organization_id), "week", week_spend, week_cap))
    return out


def _one_status(
    org_id: str, period: str, spend: float, cap: float | None
) -> CostCapStatus:
    if cap is None or cap <= 0:
        return CostCapStatus(
            organization_id=org_id,
            period=period,
            spend_usd=round(spend, 4),
            cap_usd=None,
            pct_of_cap=None,
            state="no_cap",
        )
    pct = (spend / cap) * 100.0
    if pct >= 100:
        state = "blocked"
    elif pct >= 80:
        state = "warn"
    else:
        state = "ok"
    return CostCapStatus(
        organization_id=org_id,
        period=period,
        spend_usd=round(spend, 4),
        cap_usd=cap,
        pct_of_cap=round(pct, 2),
        state=state,
    )


# ---------- Confidence threshold -------------------------------------------


def confidence_threshold_for(
    autonomy_posture_json: dict | None, action_class: str
) -> float | None:
    """Look up the floor for a given action class.

    ``autonomy_posture_json``::

        {
          ...
          "confidence_thresholds": {
            "publish": 0.7,
            "send_email": 0.85,
            "create_lead": 0.5,
            "default": 0.6
          }
        }

    Returns the action's threshold (or the ``default`` value when set,
    else None).
    """
    if not autonomy_posture_json:
        return None
    thresholds = autonomy_posture_json.get("confidence_thresholds") or {}
    if action_class in thresholds:
        return float(thresholds[action_class])
    if "default" in thresholds:
        return float(thresholds["default"])
    return None


def should_escalate(
    *,
    autonomy_posture_json: dict | None,
    action_class: str,
    confidence: float,
) -> bool:
    """True when the action's stated confidence is below the floor.

    When no threshold is set for the action OR for the default, no
    escalation is forced (returns False).
    """
    floor = confidence_threshold_for(autonomy_posture_json, action_class)
    if floor is None:
        return False
    return confidence < floor


__all__ = [
    "CostCapStatus",
    "evaluate_caps_sync",
    "confidence_threshold_for",
    "should_escalate",
]
