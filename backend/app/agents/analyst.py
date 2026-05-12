"""Analyst agent — Phase 9.2.

Read-only by design — no outbound actions, only insights.
"""

from __future__ import annotations

import textwrap
from typing import Sequence

from app.agents._agent_base import (
    RoleAgentTurn,
    SHARED_OUTPUT_RULES,
    run_role_agent,
)


_SYSTEM_PROMPT = textwrap.dedent(
    f"""
    You are the Analyst Agent for DClaw Marketing.

    Responsibilities:
    - Compute daily rollups (reach, engagement, conversions, spend, CAC).
    - Detect anomalies on rolling baselines (3σ flags).
    - Write the Monday-morning narrative report — plain-English
      summary of what worked, what didn't, what to test next.
    - Drill into any campaign or touchpoint to surface root causes.

    Hard rules:
    - READ-ONLY. You never take outbound actions, never spend money,
      never publish.
    - Be specific. Reference numbers when you have them; flag when you
      don't have data instead of guessing.

    {SHARED_OUTPUT_RULES}
    """
).strip()

_STUB = RoleAgentTurn(
    text=(
        "Analyst Agent. I can produce daily rollups, detect "
        "anomalies, and write your Monday-morning narrative — but I "
        "need the analytics rollup job wired up (Phase 8.x). For now "
        "the Dashboard shows current campaign / lead / spend totals. "
        "[stub mode — set ANTHROPIC_API_KEY for real responses]"
    ),
    suggestions=[
        {"label": "Open Dashboard", "href": "/"},
        {"label": "Open Attribution", "href": "/analytics/attribution"},
    ],
    confidence=0.5,
)


async def reply(
    user_text: str, *, history: Sequence[dict] | None = None
) -> RoleAgentTurn:
    return await run_role_agent(
        system_prompt=_SYSTEM_PROMPT,
        user_text=user_text,
        history=history,
        stub_fallback=_STUB,
    )
