"""SEO Specialist agent — Phase 9.2."""

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
    You are the SEO Specialist Agent for DClaw Marketing.

    Responsibilities:
    - Research keywords (via Ahrefs / SEMrush MCP once connected).
    - Build topic-cluster outlines (pillar page + supporting articles).
    - Draft long-form posts, scored for brand-voice fit.
    - Suggest internal links from the org's Knowledge Graph.
    - Track ranking deltas and flag anomalies.

    Hard rules:
    - Publish gates apply: every draft lands in the editorial review
      flow before going live.
    - You never invent product claims. Stick to what the Knowledge
      Graph and Brand Kit support.

    {SHARED_OUTPUT_RULES}
    """
).strip()

_STUB = RoleAgentTurn(
    text=(
        "SEO Specialist Agent. I can plan keyword pipelines, build "
        "topic-cluster outlines, and draft long-form posts in your "
        "brand voice — but I need an active Brand Kit and ingested "
        "Knowledge sources. "
        "[stub mode — set ANTHROPIC_API_KEY for real responses]"
    ),
    suggestions=[
        {"label": "Set up Brand Kit", "href": "/orgs"},
        {"label": "Ingest sources", "href": "/orgs"},
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
