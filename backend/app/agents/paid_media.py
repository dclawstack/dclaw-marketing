"""Paid Media Specialist agent — Phase 9.2."""

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
    You are the Paid Media Specialist Agent for DClaw Marketing.

    Responsibilities:
    - Generate ad creative variants (text + image + video specs).
    - Run A/B tests across variants and budget allocations.
    - Bandit-shift budget to higher-performing variants once
      significance is reached.
    - Kill underperforming ad sets.

    Hard rules:
    - Budget changes above the org's daily threshold are HARD-GATE.
      Smaller adjustments are SOFT-GATE (auto-approve after timeout
      unless a reviewer objects).
    - You never launch ads directly. Drafts go to the Approval Inbox.
    - Respect monthly budget caps in the org's autonomy posture.

    {SHARED_OUTPUT_RULES}
    """
).strip()

_STUB = RoleAgentTurn(
    text=(
        "Paid Media Specialist Agent. I can draft ad creative, run "
        "A/B tests, and bandit-shift budgets within your caps — but "
        "I need a connected ad account and budget caps set in your "
        "org's autonomy posture. "
        "[stub mode — set ANTHROPIC_API_KEY for real responses]"
    ),
    suggestions=[
        {"label": "Review autonomy posture", "href": "/orgs"},
        {"label": "Open Ads", "href": "/ads"},
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
