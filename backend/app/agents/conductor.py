"""Conductor agent — decomposes briefs, dispatches to role agents,
escalates to humans (Phase 9 / v2.0 §4.1).

Now Claude-backed. Falls back to a keyword-classifier stub when no
ANTHROPIC_API_KEY is configured (same shape so the UI behaves
identically in dev/CI).
"""

from __future__ import annotations

import json
import logging
import textwrap
from dataclasses import dataclass
from typing import Sequence

from app.agents.anthropic_client import complete, is_real_provider_configured


logger = logging.getLogger(__name__)


@dataclass
class ConductorTurn:
    text: str
    suggestions: list[dict] = None  # type: ignore[assignment]
    confidence: float = 0.7


# ----- Real-Claude path -----------------------------------------------------

_SYSTEM_PROMPT = textwrap.dedent(
    """
    You are the Conductor — the Manager-station agent for DClaw
    Marketing, an AI-driven marketing operating system. You are a
    decomposer and dispatcher, not a doer. Humans bring you goals or
    briefs; you decompose them into work for the role agents
    (Creatives / SMM / SEO / Paid Media / Analyst) and surface the
    right next step.

    Platform surfaces you can point users at:
    - /agents/creatives — Creatives Agent runs (generate post variants
      from a brief).
    - /calendar — schedule posts across channels.
    - /channels — connected social accounts.
    - /integrations — MCP integration hub (CRM / analytics / generation
      tools).
    - /orgs — brand setup, knowledge graph, goals, projects.
    - /inbox — the Approval Inbox (Hard-gate for all outbound posting).
    - /agents/smm /agents/seo /agents/paid-media /agents/analyst — role
      stations.

    Hard rules:
    - Outbound posting is hard-gate by default. Agents never publish
      directly — every external action passes through the Approval
      Inbox.
    - You do NOT generate marketing copy yourself. If the user wants
      copy, route them to the Creatives Agent.
    - You are concise: 3-4 sentences max for the conversational text,
      then up to 4 suggestion chips.

    Respond ONLY with a single JSON object on its own line, no prose
    around it. Shape:

      {"text": "<your reply>",
       "suggestions": [
         {"label": "Open Calendar", "href": "/calendar"},
         {"label": "Run Creatives Agent", "prompt": "Generate 3 LinkedIn variants about our Q2 release"}
       ],
       "confidence": 0.0-1.0}

    Each suggestion has EITHER a `href` (in-app deep link) OR a
    `prompt` (a follow-up they can click to ask you next). Never both.
    Suggestions are optional; include them when they materially help.
    """
).strip()


def _format_history(history: Sequence[dict] | None) -> str:
    """Render the last N user/agent exchanges into a single user-turn
    string. Cheap and good enough until the SDK runtime arrives.
    """
    if not history:
        return ""
    lines = []
    for m in history[-10:]:
        role = m.get("role", "user").upper()
        content = (m.get("content") or "").strip()
        if content:
            lines.append(f"[{role}] {content}")
    return "\n".join(lines)


async def _claude_reply(
    user_text: str, history: Sequence[dict] | None
) -> ConductorTurn:
    prior = _format_history(history)
    user_block = (
        f"PRIOR CONVERSATION:\n{prior}\n\n---\nUSER: {user_text}"
        if prior
        else f"USER: {user_text}"
    )

    try:
        raw = await complete(
            system=_SYSTEM_PROMPT,
            user=user_block,
            max_tokens=600,
            n_variants_hint=1,
        )
    except Exception:
        logger.exception("Conductor: Claude call failed; using stub.")
        return _stub_reply(user_text)

    # Try to parse JSON. Tolerant of surrounding prose.
    parsed: dict | None = None
    raw_stripped = raw.strip()
    try:
        parsed = json.loads(raw_stripped)
    except json.JSONDecodeError:
        start = raw_stripped.find("{")
        end = raw_stripped.rfind("}")
        if start != -1 and end > start:
            try:
                parsed = json.loads(raw_stripped[start : end + 1])
            except json.JSONDecodeError:
                pass

    if isinstance(parsed, dict) and "text" in parsed:
        return ConductorTurn(
            text=str(parsed["text"]),
            suggestions=parsed.get("suggestions") or [],
            confidence=float(parsed.get("confidence") or 0.75),
        )

    return ConductorTurn(text=raw_stripped, suggestions=[], confidence=0.5)


# ----- Stub path (used when ANTHROPIC_API_KEY missing) ----------------------


def _intent(user_text: str) -> str:
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


def _stub_reply(user_text: str) -> ConductorTurn:
    intent = _intent(user_text)
    if intent == "intro":
        return ConductorTurn(
            text=(
                "I'm the Conductor — the Manager-station agent. Hand me a "
                "brief or a goal and I'll route the work to the right role "
                "agent (Creatives / SMM / SEO / Paid Media / Analyst) and "
                "surface what needs your approval. "
                "[stub mode — set ANTHROPIC_API_KEY for real responses]"
            ),
            suggestions=[
                {
                    "label": "Announce Q2 release",
                    "prompt": "Announce our Q2 release on LinkedIn next Tuesday",
                },
                {"label": "Open Calendar", "href": "/calendar"},
                {"label": "Open Inbox", "href": "/inbox"},
            ],
            confidence=0.5,
        )

    routing = {
        "smm": (
            "Sounds like a publishing task — I'd route to the SMM agent. "
            "It drafts variants, queues them on the Calendar, and surfaces "
            "each post in your Approval Inbox.",
            [
                {"label": "Open Calendar", "href": "/calendar"},
                {"label": "Run Creatives Agent", "href": "/agents/creatives"},
                {"label": "Review Inbox", "href": "/inbox"},
            ],
        ),
        "seo": (
            "SEO work — the SEO agent (coming online in 9.x) would research "
            "keywords, draft an outline, write the post, and queue it for "
            "editorial review.",
            [
                {"label": "Open Brand Studio", "href": "/orgs"},
                {"label": "Open Knowledge", "href": "/orgs"},
            ],
        ),
        "paid_media": (
            "Paid-media adjustments are gated by budget caps and trust "
            "mode. Review the org's autonomy posture for `ad_spend` "
            "before the Paid Media agent acts.",
            [{"label": "Review autonomy posture", "href": "/orgs"}],
        ),
        "analyst": (
            "Analyst-style requests — daily rollups, anomaly detection, "
            "Monday-narrative reports. Live analytics pipeline lands in 9.x.",
            [{"label": "Open Dashboard", "href": "/"}],
        ),
        "creatives": (
            "I'll route to the Creatives agent — it pulls your active "
            "brand kit, retrieves relevant context from the knowledge "
            "graph, and drafts N variants. Every variant lands in the "
            "Approval Inbox first.",
            [
                {"label": "Run Creatives", "href": "/agents/creatives"},
                {"label": "Review Inbox", "href": "/inbox"},
            ],
        ),
    }
    text, suggestions = routing.get(
        intent,
        (
            "I'll decompose that into role-agent tasks once the Claude "
            "Agent SDK runtime ships (9.x). For now I can point you to "
            "the right station to work manually. "
            "[stub mode — set ANTHROPIC_API_KEY for real responses]",
            [
                {"label": "Open Creatives Station", "href": "/agents/creatives"},
                {"label": "Open Calendar", "href": "/calendar"},
                {"label": "Open Inbox", "href": "/inbox"},
            ],
        ),
    )
    return ConductorTurn(text=text, suggestions=suggestions, confidence=0.5)


# ----- Public entrypoint ----------------------------------------------------


async def reply(
    user_text: str,
    *,
    history: Sequence[dict] | None = None,
) -> ConductorTurn:
    """One-shot conductor reply.

    Uses Claude when ANTHROPIC_API_KEY is set; falls back to a
    deterministic intent stub otherwise so dev/CI work offline.
    `history` is the list of prior {role, content} messages on the
    thread; only the last 10 are sent to Claude.
    """
    if is_real_provider_configured():
        return await _claude_reply(user_text, history)
    return _stub_reply(user_text)
