"""Shared scaffolding for role-agent stubs (Phase 9.2+).

Each role agent (SMM, SEO, Paid Media, Analyst) is a thin wrapper
around `run_role_agent(...)` that supplies its own system prompt.
The shared runner:
  1. Calls Claude with [system, history + user_text]
  2. Tolerantly parses a JSON object `{text, suggestions, confidence}`
  3. Falls back to a deterministic stub when no API key is configured

Suggestion shape (matches the Conductor):
  {"label": "Open Calendar", "href": "/calendar"}
  {"label": "Plan a 4-week …", "prompt": "Plan a 4-week …"}
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
class RoleAgentTurn:
    text: str
    suggestions: list[dict]
    confidence: float = 0.7


SHARED_OUTPUT_RULES = textwrap.dedent(
    """
    Respond ONLY with a single JSON object on its own line, no prose
    around it. Shape:

      {"text": "<your reply>",
       "suggestions": [
         {"label": "Open Calendar", "href": "/calendar"},
         {"label": "Draft 3 LinkedIn variants", "prompt": "Draft 3 LinkedIn variants on Q2 release"}
       ],
       "confidence": 0.0-1.0}

    Each suggestion has EITHER `href` (in-app deep link) OR `prompt`
    (a follow-up the user can click). Never both. 3-4 sentences max
    for text, up to 4 suggestion chips.
    """
).strip()


def _format_history(history: Sequence[dict] | None) -> str:
    if not history:
        return ""
    lines = []
    for m in history[-10:]:
        role = m.get("role", "user").upper()
        content = (m.get("content") or "").strip()
        if content:
            lines.append(f"[{role}] {content}")
    return "\n".join(lines)


def _parse(raw: str) -> RoleAgentTurn:
    s = raw.strip()
    parsed: dict | None = None
    try:
        parsed = json.loads(s)
    except json.JSONDecodeError:
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end > start:
            try:
                parsed = json.loads(s[start : end + 1])
            except json.JSONDecodeError:
                pass
    if isinstance(parsed, dict) and "text" in parsed:
        return RoleAgentTurn(
            text=str(parsed["text"]),
            suggestions=parsed.get("suggestions") or [],
            confidence=float(parsed.get("confidence") or 0.75),
        )
    return RoleAgentTurn(text=s, suggestions=[], confidence=0.5)


async def run_role_agent(
    *,
    system_prompt: str,
    user_text: str,
    history: Sequence[dict] | None,
    stub_fallback: RoleAgentTurn,
) -> RoleAgentTurn:
    """Run a role agent. Stubs out when no API key.

    `stub_fallback` is what we return when ANTHROPIC_API_KEY is
    missing — keeps the conversation flowing on dev/CI without
    needing a key.
    """
    if not is_real_provider_configured():
        return stub_fallback

    prior = _format_history(history)
    user_block = (
        f"PRIOR CONVERSATION:\n{prior}\n\n---\nUSER: {user_text}"
        if prior
        else f"USER: {user_text}"
    )

    try:
        raw = await complete(
            system=system_prompt,
            user=user_block,
            max_tokens=700,
            n_variants_hint=1,
        )
        return _parse(raw)
    except Exception:
        logger.exception("Role agent: Claude call failed; using stub.")
        return stub_fallback
