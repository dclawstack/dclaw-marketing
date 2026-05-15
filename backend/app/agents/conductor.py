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
    user_text: str,
    history: Sequence[dict] | None,
    images: list[tuple[str, bytes]] | None = None,
    doc_summaries: list[str] | None = None,
) -> ConductorTurn:
    prior = _format_history(history)
    parts: list[str] = []
    if prior:
        parts.append(f"PRIOR CONVERSATION:\n{prior}\n\n---")
    if doc_summaries:
        joined = "\n".join(f"- {s}" for s in doc_summaries)
        parts.append(f"ATTACHED DOCUMENTS:\n{joined}\n\n---")
    parts.append(f"USER: {user_text}")
    user_block = "\n".join(parts)

    try:
        raw = await complete(
            system=_SYSTEM_PROMPT,
            user=user_block,
            max_tokens=600,
            n_variants_hint=1,
            images=images,
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


_AGENT_SYSTEM_PROMPT = textwrap.dedent(
    """
    You are the Conductor — the Manager-station agent for DClaw
    Marketing, an AI-driven marketing operating system. You operate
    the entire platform via tool calls (parity with Claude Code's tool
    model). You can navigate the user to any page, query the database
    for lists/summaries, queue posts / approvals / generations, and
    coordinate role agents.

    Hard rules:
    - Outbound posting and external sends are hard-gated by the Approval
      Inbox. Tools that fire external side-effects (publish_now,
      send_email_test, create_ad_campaign, etc.) only RECORD intent —
      the human approves in the Inbox before anything goes live.
    - When the user asks to "open", "go to", or "show" a page, call
      `navigate_to`. The frontend deep-links automatically.
    - When the user asks about state ("what's pending", "what's queued"),
      call the corresponding list_* tool first, THEN reply with the
      findings.
    - If the user references an attached image or document, you can see
      it via Claude vision (images) or in the user message context (doc
      summaries) — reason about them and call tools as needed.
    - Be concise in the final natural-language reply (2–4 sentences max).
      Tool-call cards already show structured detail.
    - When you've called the tools you need, stop emitting tool_use and
      return your final text answer.
    """
).strip()


@dataclass
class ConductorAgenticTurn:
    """Result of an agentic Conductor run — final text + the trace of
    every tool call that was executed along the way. The caller is
    responsible for persisting the trace into AgentMessage rows.
    """

    text: str
    confidence: float
    tool_calls: list[dict]  # [{"name", "input", "result", "tool_use_id"}, …]


async def reply_agentic(
    user_text: str,
    *,
    history: Sequence[dict] | None,
    images: list[tuple[str, bytes]] | None = None,
    doc_summaries: list[str] | None = None,
    tool_ctx,  # ToolContext — typed loosely to avoid circular import
    max_iters: int = 6,
) -> ConductorAgenticTurn:
    """Run the Conductor in agentic tool-use mode.

    Builds an Anthropic-style `messages` list from history + user_text
    (plus image content blocks if present), invokes Claude with the
    REGISTRY tool schema, and loops: dispatch tool_use blocks → feed
    tool_result back → repeat until stop_reason != tool_use OR max_iters
    hit. Falls back to text-only `reply()` when no API key is
    configured.
    """
    from app.agents.anthropic_client import (
        is_real_provider_configured,
        messages_create_raw,
    )
    from app.agents.tools import REGISTRY

    if not is_real_provider_configured():
        # Stub mode — defer to the text-only path so dev/CI behaves
        # identically. Tool calling needs real Claude to work.
        text_turn = await reply(
            user_text,
            history=history,
            images=images,
            doc_summaries=doc_summaries,
        )
        return ConductorAgenticTurn(
            text=text_turn.text,
            confidence=text_turn.confidence,
            tool_calls=[],
        )

    # Build messages: prior turns + current user turn.
    messages: list[dict] = []
    for m in (history or [])[-10:]:
        role = m.get("role", "user")
        if role not in ("user", "assistant"):
            continue
        content = (m.get("content") or "").strip()
        if not content:
            continue
        messages.append({"role": role, "content": content})

    # Current user turn — assemble content blocks for vision + docs.
    import base64 as _b64
    user_blocks: list[dict] = []
    if images:
        for mime, raw in images:
            user_blocks.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": mime,
                        "data": _b64.b64encode(raw).decode("ascii"),
                    },
                }
            )
    text_parts: list[str] = []
    if doc_summaries:
        text_parts.append(
            "ATTACHED DOCUMENTS:\n" + "\n".join(f"- {s}" for s in doc_summaries)
        )
    text_parts.append(user_text)
    user_blocks.append({"type": "text", "text": "\n\n".join(text_parts)})
    messages.append({"role": "user", "content": user_blocks})

    tool_calls_trace: list[dict] = []
    tools_schema = REGISTRY.as_claude_schema()

    final_text = ""
    for _ in range(max_iters):
        response = await messages_create_raw(
            system=_AGENT_SYSTEM_PROMPT,
            messages=messages,
            tools=tools_schema,
            max_tokens=1200,
        )
        stop_reason = response.get("stop_reason", "end_turn")
        content = response.get("content", []) or []

        # Collect text segments emitted this turn.
        text_chunks = [b.get("text", "") for b in content if b.get("type") == "text"]
        if text_chunks:
            final_text = "\n".join(t for t in text_chunks if t).strip()

        tool_uses = [b for b in content if b.get("type") == "tool_use"]
        if not tool_uses or stop_reason != "tool_use":
            # Final answer — exit loop.
            break

        # Append the assistant turn (raw content blocks) so Claude sees
        # its own tool_use calls in the next iteration.
        messages.append({"role": "assistant", "content": content})

        # Dispatch each tool, build tool_result blocks for the next user turn.
        result_blocks: list[dict] = []
        for tu in tool_uses:
            tool_name = tu.get("name", "")
            tool = REGISTRY.get(tool_name)
            if tool is None:
                result = {"ok": False, "error": f"unknown tool: {tool_name}"}
            else:
                try:
                    result = await tool.handler(tool_ctx, **(tu.get("input") or {}))
                except TypeError as e:
                    result = {"ok": False, "error": f"tool args mismatch: {e}"}
                except Exception as e:
                    logger.exception("Conductor: tool %s failed", tool_name)
                    result = {"ok": False, "error": str(e)}
            tool_calls_trace.append(
                {
                    "tool_use_id": tu.get("id"),
                    "name": tool_name,
                    "input": tu.get("input") or {},
                    "result": result,
                }
            )
            # Anthropic tool_result blocks accept a string content.
            import json as _json
            result_blocks.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tu.get("id"),
                    "content": _json.dumps(result)[:50_000],
                }
            )

        messages.append({"role": "user", "content": result_blocks})
    else:
        # Loop exhausted without natural exit.
        if not final_text:
            final_text = (
                "(stopped after running the maximum number of tool calls — "
                "please refine your ask)"
            )

    if not final_text:
        final_text = "Done."

    return ConductorAgenticTurn(
        text=final_text,
        confidence=0.85,
        tool_calls=tool_calls_trace,
    )


async def reply(
    user_text: str,
    *,
    history: Sequence[dict] | None = None,
    images: list[tuple[str, bytes]] | None = None,
    doc_summaries: list[str] | None = None,
) -> ConductorTurn:
    """One-shot conductor reply.

    Uses Claude when ANTHROPIC_API_KEY is set; falls back to a
    deterministic intent stub otherwise so dev/CI work offline.
    `history` is the list of prior {role, content} messages on the
    thread; only the last 10 are sent to Claude. `images` is a list of
    `(mime_type, bytes)` pairs forwarded as Claude vision content
    blocks (S5-CDR-B). `doc_summaries` is a list of brief lines (one
    per non-image attachment) inlined into the user prompt.
    """
    if is_real_provider_configured():
        return await _claude_reply(
            user_text,
            history,
            images=images,
            doc_summaries=doc_summaries,
        )
    return _stub_reply(user_text)
