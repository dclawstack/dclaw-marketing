"""Trust-mode resolver (S4-A4).

Reads `Organization.autonomy_posture_json` (per-action overrides) plus
platform defaults to answer "does this action need approval right now?".

Per PLAN-v1.2 §v2.0 §5:
  hard_gate — always pause for human approval
  soft_gate — proceed but require human sign-off post-hoc
  auto      — no human in the loop

Default posture per action_class:
  social_post   → hard_gate
  email_send    → hard_gate
  paid_ad_spend → hard_gate
  draft_email   → soft_gate
  draft_post    → soft_gate
  reply_dm      → soft_gate
  internal_report → auto
"""

from __future__ import annotations

from enum import Enum
from typing import Mapping
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization


class TrustMode(str, Enum):
    hard_gate = "hard_gate"
    soft_gate = "soft_gate"
    auto = "auto"


PLATFORM_DEFAULTS: dict[str, TrustMode] = {
    "social_post":     TrustMode.hard_gate,
    "email_send":      TrustMode.hard_gate,
    "paid_ad_spend":   TrustMode.hard_gate,
    "draft_email":     TrustMode.soft_gate,
    "draft_post":      TrustMode.soft_gate,
    "reply_dm":        TrustMode.soft_gate,
    "internal_report": TrustMode.auto,
    "kg_query":        TrustMode.auto,
    "embedding":       TrustMode.auto,
}


async def resolve_trust_mode(
    db: AsyncSession,
    *,
    org_id: UUID | None,
    action_class: str,
) -> TrustMode:
    """Return the trust mode for (org, action_class), falling back to
    PLATFORM_DEFAULTS, then `auto`."""
    if org_id is None:
        return PLATFORM_DEFAULTS.get(action_class, TrustMode.auto)
    org = await db.get(Organization, org_id)
    posture: Mapping[str, str] | None = (
        org.autonomy_posture_json if org else None
    )
    if posture and action_class in posture:
        try:
            return TrustMode(posture[action_class])
        except ValueError:
            pass
    return PLATFORM_DEFAULTS.get(action_class, TrustMode.auto)


def requires_human_pause(mode: TrustMode) -> bool:
    """True if the runtime must create an ApprovalRequest before executing."""
    return mode == TrustMode.hard_gate
