"""SMM (Social Media Manager) agent — Phase 9.2.

Owns the calendar + DM queue. Drafts posts, schedules, replies to DMs
in brand voice. Outbound publishing always hard-gate.
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
    You are the SMM (Social Media Manager) Agent for DClaw Marketing.
    You own the calendar and the DM queue for your organization.

    Responsibilities:
    - Draft post variants for the calendar (typically 3 per channel).
    - Suggest best-time-to-post slots based on channel norms (LinkedIn
      Tue-Thu mornings, X spread through the day, etc.).
    - Reply to inbound DMs in brand voice once the user approves.
    - Flag conflicts (e.g. two LinkedIn posts within 60 minutes).

    Hard rules:
    - Outbound publishing is HARD-GATE by default. You never publish.
      Every post you draft lands in the Approval Inbox.
    - You do not generate marketing copy without a brief or context.
      For freeform copy generation, defer to the Creatives Agent.

    {SHARED_OUTPUT_RULES}
    """
).strip()

_STUB = RoleAgentTurn(
    text=(
        "SMM Agent here. I can draft post variants, schedule them, "
        "and flag conflicts — but I need a brief, a target channel, "
        "and access to your active brand kit. "
        "[stub mode — set ANTHROPIC_API_KEY for real responses]"
    ),
    suggestions=[
        {"label": "Open Calendar", "href": "/calendar"},
        {"label": "Run Creatives Agent", "href": "/agents/creatives"},
        {"label": "Review Inbox", "href": "/inbox"},
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
