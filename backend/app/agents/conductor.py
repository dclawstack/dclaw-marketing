"""Conductor agent — decomposes briefs, dispatches to role agents,
escalates to humans (Phase 9 / v2.0 §4.1).

Phase 9 stub: produces deterministic, brand-coherent suggestions
without calling Claude. The real agent ships in Phase 9.x when the
Claude Agent SDK runtime lands.
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass
from typing import Sequence


@dataclass
class ConductorTurn:
    """One Conductor reply — text plus optional structured suggestions
    the UI can render as cards.
    """

    text: str
    suggestions: list[dict] = None  # type: ignore[assignment]
    confidence: float = 0.7


def _intent(user_text: str) -> str:
    """Cheap keyword classifier — replaced by Claude in Phase 9.x."""
    t = user_text.lower()
    if any(k in t for k in ("blog", "seo", "rank", "keyword")):
        return "seo"
    if any(k in t for k in ("ad", "spend", "budget", "cac", "roas")):
        return "paid_media"
    if any(k in t for k in ("analyz", "report", "metric", "dashboard")):
        return "analyst"
    if any(k in t for k in ("post", "linkedin", "x ", "instagram", "schedule")):
        return "smm"
    if any(k in t for k in ("design", "draft", "variant", "copy", "image")):
        return "creatives"
    if any(k in t for k in ("hi", "hello", "hey", "what can")):
        return "intro"
    return "general"


def _intro_turn() -> ConductorTurn:
    return ConductorTurn(
        text=textwrap.dedent(
            """
            I'm the Conductor — the Manager-station agent. Hand me a
            campaign brief, a problem, or a goal, and I'll decompose
            it into work for the role agents (Creatives, SMM, SEO,
            Paid Media, Analyst) and surface what needs your approval.

            Try something like:
              • "Announce our Q2 release on LinkedIn next Tuesday"
              • "Plan a 4-week content calendar for SaaS CMOs"
              • "Find out why our LinkedIn engagement dropped last week"
            """
        ).strip(),
        suggestions=[
            {
                "label": "Announce Q2 release",
                "prompt": "Announce our Q2 release on LinkedIn next Tuesday",
            },
            {
                "label": "Plan content calendar",
                "prompt": "Plan a 4-week content calendar for SaaS CMOs",
            },
            {
                "label": "Engagement dip review",
                "prompt": "Find out why our LinkedIn engagement dropped last week",
            },
        ],
        confidence=0.95,
    )


def reply(user_text: str, *, history: Sequence[dict] | None = None) -> ConductorTurn:
    """One-shot conductor reply.

    `history` is included for forward-compat; the stub ignores it.
    """
    intent = _intent(user_text)
    if intent == "intro":
        return _intro_turn()

    if intent == "smm":
        return ConductorTurn(
            text=(
                "Sounds like a publishing task — I'll route to the SMM "
                "agent. It will draft variants, queue them on the "
                "Calendar, and surface each post in your Approval Inbox. "
                "Outbound posting is hard-gate by default, so nothing "
                "goes live until you decide."
            ),
            suggestions=[
                {"label": "Open Calendar", "href": "/calendar"},
                {"label": "Run Creatives Agent", "href": "/agents/creatives"},
                {"label": "Review Inbox", "href": "/inbox"},
            ],
        )
    if intent == "seo":
        return ConductorTurn(
            text=(
                "SEO work — the SEO agent (coming online in Phase 9.x) "
                "researches keywords, drafts an outline, writes the post, "
                "and queues it through the editorial review flow. For now "
                "you can prep the brief and the brand kit so it's ready "
                "the moment the agent ships."
            ),
            suggestions=[
                {"label": "Set up Brand Kit", "href_template": "brand"},
                {"label": "Add knowledge sources", "href_template": "knowledge"},
            ],
        )
    if intent == "paid_media":
        return ConductorTurn(
            text=(
                "Paid-media adjustments are gated by budget caps and "
                "trust mode. Review the org's autonomy posture for "
                "`ad_spend` before the Paid Media agent acts. Phase 9.x "
                "wires real ad-platform calls."
            ),
            suggestions=[
                {"label": "Review autonomy posture", "href_template": "goals"},
            ],
        )
    if intent == "analyst":
        return ConductorTurn(
            text=(
                "Analyst-style requests go to the Analyst agent — daily "
                "rollups, anomaly detection, Monday-narrative reports. "
                "Phase 9.x lands the live analytics pipeline. In the "
                "meantime, the Dashboard shows current campaign + lead "
                "+ spend totals."
            ),
            suggestions=[
                {"label": "Open Dashboard", "href": "/"},
            ],
        )
    if intent == "creatives":
        return ConductorTurn(
            text=(
                "I'll route to the Creatives agent — it pulls your active "
                "brand kit, retrieves relevant context from the knowledge "
                "graph, and drafts N variants. Every variant lands in the "
                "Approval Inbox first."
            ),
            suggestions=[
                {"label": "Run Creatives", "href": "/agents/creatives"},
                {"label": "Review Inbox", "href": "/inbox"},
            ],
        )

    return ConductorTurn(
        text=(
            "I'll decompose that into the right role-agent tasks once the "
            "Claude Agent SDK runtime ships (Phase 9.x). For now I can "
            "point you to the right station to do the work manually."
        ),
        suggestions=[
            {"label": "Open Creatives Station", "href": "/agents/creatives"},
            {"label": "Open Calendar", "href": "/calendar"},
            {"label": "Open Inbox", "href": "/inbox"},
        ],
        confidence=0.5,
    )
