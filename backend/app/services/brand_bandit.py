"""BrandKitInsight bandit ranking (S4-E5).

The legacy injection picks insights in FIFO order. Sprint 4 swaps that
for a small ε-greedy multi-armed bandit so the agent runtime converges
on the brand voice fastest.

Each `BrandKitInsight` carries a `reward_sum` + `pull_count` (stored in
the existing `metadata_json` blob for now; a follow-up migration may
promote these to columns). The bandit returns the top-N insights for a
given context (channel / persona / agent), with an ε chance of pulling
a random insight to keep exploring.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.brand_kit_insight import BrandKitInsight

log = logging.getLogger(__name__)


EPSILON = 0.1


@dataclass
class RankedInsight:
    id: UUID
    score: float
    text: str | None


def _meta(insight: BrandKitInsight) -> dict:
    return insight.metadata_json or {}


def _score(insight: BrandKitInsight) -> float:
    m = _meta(insight)
    pulls = float(m.get("pull_count", 0) or 0)
    rewards = float(m.get("reward_sum", 0) or 0)
    if pulls <= 0:
        return 1.0  # Optimistic prior so unseen insights get a turn.
    return rewards / pulls


async def rank_insights_for(
    db: AsyncSession,
    *,
    organization_id: UUID,
    limit: int = 5,
    epsilon: float = EPSILON,
) -> list[RankedInsight]:
    rows = (
        await db.execute(
            select(BrandKitInsight).where(
                BrandKitInsight.organization_id == organization_id
            )
        )
    ).scalars().all()
    if not rows:
        return []

    scored = sorted(
        [(insight, _score(insight)) for insight in rows],
        key=lambda x: x[1],
        reverse=True,
    )
    picked: list[BrandKitInsight] = [s[0] for s in scored[:limit]]
    # ε chance to swap one of the picks for a random unseen insight.
    if random.random() < epsilon and len(rows) > len(picked):
        rest = [r for r in rows if r not in picked]
        if rest:
            picked[-1] = random.choice(rest)
    return [
        RankedInsight(
            id=p.id, score=_score(p), text=getattr(p, "text_excerpt", None)
        )
        for p in picked
    ]


async def record_reward(
    db: AsyncSession, *, insight_id: UUID, reward: float
) -> None:
    """Increment pull_count + reward_sum on an insight after a run uses it."""
    row = await db.get(BrandKitInsight, insight_id)
    if row is None:
        return
    m = dict(row.metadata_json or {})
    m["pull_count"] = int(m.get("pull_count", 0) or 0) + 1
    m["reward_sum"] = float(m.get("reward_sum", 0) or 0) + reward
    row.metadata_json = m
    await db.commit()
