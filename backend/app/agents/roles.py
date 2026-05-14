"""Role-agent runner (S4-A3).

A thin wrapper that takes a role name (creatives / smm / seo / paid_media
/ analyst / inbox / reviewer) plus an input brief and returns the
agent's JSON response. Uses `agents.runtime.run_completion()` so every
role agent goes through the model resolver chain.

Each role has a curated system prompt — the same prompts the legacy
per-agent endpoints used, consolidated here so /agents/role/{name}/run
is the canonical end-to-end path.
"""

from __future__ import annotations

import json
import logging
import textwrap
from dataclasses import dataclass
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.runtime import run_completion
from app.models.model_registry import Capability

log = logging.getLogger(__name__)


ROLE_SYSTEM_PROMPTS: dict[str, str] = {
    "creatives": textwrap.dedent(
        """
        You are the Creatives Agent for DClaw.

        Generate 3 distinct text variants for the brief; keep each under
        70 words. Avoid hype, exclamation marks, and emoji unless the
        brief asks for them. End with a short rationale per variant.
        """
    ).strip(),
    "smm": textwrap.dedent(
        """
        You are the SMM Agent for DClaw.

        Plan a 1-week cross-channel calendar (LinkedIn / X / Instagram).
        For each day list (channel, post type, 1-line hook, tag). 7 rows.
        """
    ).strip(),
    "seo": textwrap.dedent(
        """
        You are the SEO Agent for DClaw.

        Given the topic, return 8 keyword ideas with rough intent
        (informational / commercial / navigational) and one suggested H1
        per topic cluster.
        """
    ).strip(),
    "paid_media": textwrap.dedent(
        """
        You are the Paid Media Agent for DClaw.

        Outline a single-channel campaign: audience, 3 ad concepts,
        suggested daily budget (USD), and one KPI to optimise.
        """
    ).strip(),
    "analyst": textwrap.dedent(
        """
        You are the Analyst Agent for DClaw.

        Read the provided rollup numbers; flag any metric that's >2σ
        away from its trailing 7-day mean. Return a Markdown bullet list.
        """
    ).strip(),
    "inbox": textwrap.dedent(
        """
        You are the Inbox Agent for DClaw.

        Draft 3 reply options for the incoming message: warm-friendly,
        neutral-precise, brief-acknowledge. Each reply ≤ 40 words.
        """
    ).strip(),
    "reviewer": textwrap.dedent(
        """
        You are the Reviewer Agent for DClaw.

        Audit the draft for: brand voice fit, factual claims that need
        sources, regulatory red flags. Return JSON
        {"verdict": "pass"|"changes_requested"|"reject", "notes": [...]}.
        """
    ).strip(),
}


@dataclass
class RoleRun:
    agent: str
    request_id: str
    text: str
    model_id: str | None
    resolved_by: str | None


async def run_role(
    *,
    db: AsyncSession,
    agent: str,
    brief: str,
    org_id: UUID | None,
    user_id: UUID | None,
    request_id: str | None = None,
    max_tokens: int = 800,
) -> RoleRun:
    """Run one role-agent through the resolver. Always tags the call
    with a shared request_id so the trace replay (S4-A6) can stitch the
    sequence back together later."""
    rid = request_id or str(uuid4())
    system = ROLE_SYSTEM_PROMPTS.get(agent, ROLE_SYSTEM_PROMPTS["creatives"])
    res = await run_completion(
        db=db,
        org_id=org_id,
        user_id=user_id,
        caller_component=f"{agent}_agent",
        system=system,
        user=brief,
        max_tokens=max_tokens,
        capability=Capability.text,
    )
    return RoleRun(
        agent=agent,
        request_id=rid,
        text=res["text"],
        model_id=res.get("model_id"),
        resolved_by=res.get("resolved_by"),
    )
