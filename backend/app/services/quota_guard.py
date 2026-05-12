"""Quota guard (Phase 11.2).

Checks whether a requested action would breach the org's budget caps
(per-day) before it's filed as an ApprovalRequest. Caps live on the
Organization's ``constraints_json`` blob; if absent, no caps apply.

Shape of ``constraints_json``::

    {
      "daily_caps_usd": {
        "ads":         500.0,
        "email_sends": 10000,   # count, not USD
        "social_posts": 50
      }
    }

A cap of ``null`` or missing means "unlimited".

Today's usage is computed from ApprovalRequest rows that are
``approved`` (or ``auto_approved``) and whose ``payload_json.amount_usd``
/ ``payload_json.to.length`` etc. shows the action's cost.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval_request import ApprovalRequest, ApprovalStatus
from app.models.organization import Organization


@dataclass(frozen=True, slots=True)
class QuotaCheck:
    ok: bool
    cap_key: str
    cap_value: float | None
    used_today: float
    requested: float
    remaining: float | None
    reason: str | None


# action_type → (cap_key, "how to read the cost from payload_json")
_COST_RULES: dict[str, tuple[str, str]] = {
    "send_email": ("email_sends", "recipient_count"),
    "publish_ad": ("ads", "amount_usd"),
    "publish_social_post": ("social_posts", "one"),
    "publish_image_asset": ("social_posts", "one"),
    "publish_video_asset": ("social_posts", "one"),
}


def _cost_of(action_type: str, payload: dict | None) -> tuple[str | None, float]:
    rule = _COST_RULES.get(action_type)
    if rule is None:
        return None, 0.0
    cap_key, how = rule
    if how == "one":
        return cap_key, 1.0
    if how == "amount_usd":
        amount = (payload or {}).get("amount_usd", 0)
        try:
            return cap_key, float(amount)
        except (TypeError, ValueError):
            return cap_key, 0.0
    if how == "recipient_count":
        to = (payload or {}).get("to") or []
        return cap_key, float(len(to))
    return None, 0.0


def _today_bounds() -> tuple[datetime, datetime]:
    now = datetime.now(tz=timezone.utc)
    start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


async def check_quota(
    session: AsyncSession,
    organization_id: UUID,
    action_type: str,
    payload: dict | None,
) -> QuotaCheck:
    """Returns whether the proposed action fits within today's cap.

    Best-effort: silently returns ``ok=True`` for action types we
    don't have a cost rule for. Callers should treat that as "no
    quota applies".
    """
    cap_key, requested = _cost_of(action_type, payload)
    if cap_key is None:
        return QuotaCheck(
            ok=True,
            cap_key="",
            cap_value=None,
            used_today=0.0,
            requested=0.0,
            remaining=None,
            reason=None,
        )

    org = await session.get(Organization, organization_id)
    if org is None:
        return QuotaCheck(
            ok=False,
            cap_key=cap_key,
            cap_value=None,
            used_today=0.0,
            requested=requested,
            remaining=None,
            reason="Organization not found.",
        )

    caps = ((org.constraints_json or {}).get("daily_caps_usd") or {}) if isinstance(
        org.constraints_json, dict
    ) else {}
    cap_value = caps.get(cap_key)
    if cap_value is None:
        return QuotaCheck(
            ok=True,
            cap_key=cap_key,
            cap_value=None,
            used_today=0.0,
            requested=requested,
            remaining=None,
            reason=None,
        )

    # Sum today's approved spend on this cap_key.
    start, end = _today_bounds()
    approved_today = await session.execute(
        select(ApprovalRequest).where(
            ApprovalRequest.organization_id == organization_id,
            ApprovalRequest.status.in_(
                (ApprovalStatus.approved, ApprovalStatus.auto_approved)
            ),
            ApprovalRequest.decided_at >= start,
            ApprovalRequest.decided_at < end,
        )
    )
    used = 0.0
    for ar in approved_today.scalars().all():
        other_key, cost = _cost_of(ar.action_type, ar.payload_json)
        if other_key == cap_key:
            used += cost

    cap_f = float(cap_value)
    remaining = max(0.0, cap_f - used)
    ok = (used + requested) <= cap_f

    return QuotaCheck(
        ok=ok,
        cap_key=cap_key,
        cap_value=cap_f,
        used_today=used,
        requested=requested,
        remaining=remaining,
        reason=(
            None
            if ok
            else (
                f"Daily {cap_key} cap is {cap_f:g}; used {used:g} so far, "
                f"this request adds {requested:g} — would exceed by "
                f"{(used + requested) - cap_f:g}."
            )
        ),
    )


__all__ = ["check_quota", "QuotaCheck"]
