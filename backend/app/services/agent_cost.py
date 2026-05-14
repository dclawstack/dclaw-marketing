"""Per-agent-run cost ledger writer (S4-B2).

Every generation run lands one CostLedger row tagged with
`(org_id, project_id, kind, provider, model_id, units)` so the
/admin/costs dashboard can break spend down by agent + model.

Cost is computed from token counts using a small per-model rate table.
Unknown models fall back to a defensive flat rate so we never write
NaNs / negatives.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ops import CostLedger


# Per-1M-token rates in USD. Captures the headline models.
LLM_RATES: dict[str, tuple[float, float]] = {  # model_id → (input, output)
    "claude-opus-4-7":     (15.00, 75.00),
    "claude-sonnet-4-6":   (3.00,  15.00),
    "claude-haiku-4-5":    (0.80,   4.00),
    "gpt-4o":              (2.50,  10.00),
    "gpt-4o-mini":         (0.15,   0.60),
    "text-embedding-3-large": (0.13, 0.0),
    "gemini-2.0-flash":    (0.075,  0.30),
    "gemini-2.0-pro":      (1.25,   5.00),
    "command-a-03-2025":   (2.50,  10.00),
    "deepseek-chat":       (0.27,   1.10),
}


def estimate_cost(
    model_id: str | None, input_tokens: int, output_tokens: int
) -> float:
    if not model_id:
        return 0.0
    rate = LLM_RATES.get(model_id)
    if rate is None:
        # Defensive fallback: assume mid-tier pricing.
        rate = (1.0, 4.0)
    return (input_tokens * rate[0] + output_tokens * rate[1]) / 1_000_000


async def write_run_cost(
    db: AsyncSession,
    *,
    org_id: UUID,
    project_id: UUID | None,
    agent: str,
    kind: str,
    provider: str,
    model_id: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
    units: float | None = None,
    units_kind: str | None = None,
    job_id: UUID | None = None,
    agent_message_id: UUID | None = None,
    extra: dict[str, Any] | None = None,
) -> CostLedger:
    cost = estimate_cost(model_id, input_tokens, output_tokens)
    row = CostLedger(
        organization_id=org_id,
        project_id=project_id,
        provider=provider,
        provider_resource=model_id,
        kind=kind,
        amount_usd=cost,
        units=units if units is not None else (input_tokens + output_tokens),
        units_kind=units_kind or "tokens",
        job_id=job_id,
        agent_message_id=agent_message_id,
        occurred_at=datetime.now(timezone.utc),
        metadata_json={
            "agent": agent,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            **(extra or {}),
        },
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row
