"""H2 SEO blog pipeline (SP3-17).

Three-step pipeline: keyword discovery → outline → draft. Each step is
deterministic + stub-mode by default; once the SEO Agent ships, each
function can be swapped for an LLM call gated on Hard-gate approvals.
"""

from __future__ import annotations

import re
from typing import Any


_STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "your", "into",
    "have", "has", "are", "but", "not", "you", "our", "all", "any",
    "what", "how", "why", "who", "when", "where", "as", "is", "it",
    "be", "to", "of", "in", "on", "at", "or", "an", "a", "by",
}


def _normalize(text: str) -> list[str]:
    return [
        w.lower()
        for w in re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", text or "")
        if w.lower() not in _STOPWORDS
    ]


def suggest_keywords(
    brand_context: dict[str, Any] | None = None,
    count: int = 8,
) -> list[dict]:
    """Pull keyword candidates from brand voice + audience descriptors.

    Returns: [{"keyword": str, "score": int 1-100, "rationale": str}, ...]
    Score is a heuristic (term frequency in the supplied context) — once
    GSC + SERP scraping land we'll merge with real volume + difficulty.
    """
    ctx = brand_context or {}
    text_parts = [
        ctx.get("voice_summary") or "",
        ctx.get("audience") or "",
        ctx.get("offer") or "",
        " ".join(ctx.get("pillars") or []),
        " ".join(ctx.get("competitors") or []),
    ]
    tokens = _normalize(" ".join(text_parts))
    if not tokens:
        # Hand back a safe default ladder so the UI doesn't render empty.
        return [
            {
                "keyword": kw,
                "score": 50 - i * 5,
                "rationale": "default seed (no brand context yet)",
            }
            for i, kw in enumerate([
                "marketing automation",
                "lead nurture",
                "content distribution",
                "newsletter growth",
                "ICP messaging",
                "brand voice",
                "SEO content",
                "demand capture",
            ][:count])
        ]

    # Build bigram candidates: stronger SEO signal than unigrams.
    bigrams: dict[str, int] = {}
    for i in range(len(tokens) - 1):
        bg = f"{tokens[i]} {tokens[i + 1]}"
        bigrams[bg] = bigrams.get(bg, 0) + 1

    ranked = sorted(bigrams.items(), key=lambda kv: kv[1], reverse=True)[:count]
    max_score = ranked[0][1] if ranked else 1
    return [
        {
            "keyword": kw,
            "score": int(60 + (40 * v / max_score)),
            "rationale": f"appears {v}× in brand context",
        }
        for kw, v in ranked
    ]


def build_outline(keyword: str, target_word_count: int = 1200) -> dict:
    """Skeleton outline for a single keyword.

    Returns: {"title", "meta_description", "sections": [{"heading", "bullets": [...]}]}
    """
    kw = (keyword or "").strip() or "this topic"
    title = f"The {kw.title()} Playbook: How to Move from Theory to Pipeline"
    meta = (
        f"A practical guide to {kw}: what works, what fails, and a "
        "playbook you can ship this quarter."
    )
    sections = [
        {
            "heading": f"What {kw} actually is (vs. what teams think it is)",
            "bullets": [
                "Plain-language definition with a one-sentence litmus test",
                "Three common misconceptions and the data that contradicts them",
            ],
        },
        {
            "heading": f"When {kw} pays back — and when it's a distraction",
            "bullets": [
                "ICP fit: who benefits, who doesn't",
                "Maturity prereqs: stack, headcount, baseline traffic",
                "Failure modes: where teams burn months for nothing",
            ],
        },
        {
            "heading": f"The {kw} stack we recommend in 2026",
            "bullets": [
                "Free-tier path (under $50/mo)",
                "Scale path (between $500–$2k/mo)",
                "Enterprise path (above $5k/mo)",
            ],
        },
        {
            "heading": "Step-by-step rollout in 30 / 60 / 90 days",
            "bullets": [
                "Days 0–30: discovery, baseline, first ship",
                "Days 31–60: instrumentation, first measured win",
                "Days 61–90: scale + handoff",
            ],
        },
        {
            "heading": "Five metrics that prove it's working",
            "bullets": [
                "Leading: activation events / qualified visits",
                "Lagging: pipeline created, CAC payback",
                "Reporting cadence: weekly review, monthly readout",
            ],
        },
        {
            "heading": "Templates + downloadables",
            "bullets": [
                "Implementation checklist",
                "30/60/90 board template",
                "Reporting one-pager",
            ],
        },
    ]
    return {
        "keyword": kw,
        "title": title,
        "meta_description": meta,
        "target_word_count": target_word_count,
        "sections": sections,
    }


def draft_post(
    keyword: str,
    outline: dict | None = None,
    brand_context: dict | None = None,
) -> str:
    """Markdown draft. Walks the outline; one paragraph per bullet."""
    plan = outline or build_outline(keyword)
    voice = (brand_context or {}).get("voice_summary", "direct, practical, no fluff")

    lines: list[str] = []
    lines.append(f"# {plan['title']}\n")
    lines.append(f"*Meta:* {plan['meta_description']}\n")
    lines.append(
        f"_Drafted in the brand voice: {voice}. Hand-gate review required before publish._\n"
    )

    for section in plan["sections"]:
        lines.append(f"\n## {section['heading']}\n")
        for bullet in section["bullets"]:
            lines.append(
                f"\n{bullet}. The team most often gets this wrong by skipping the "
                f"hard prerequisite work — they want the result without the audit. "
                f"In our experience, the leaders who got this right spent two weeks "
                f"on the boring stuff first, and the next six weeks shipping. "
                f"Pulling forward the diligence is the leverage move.\n"
            )

    lines.append("\n## What to do next\n")
    lines.append(
        "1. Copy the 30/60/90 template at the bottom of this post.\n"
        "2. Pick the smallest possible first ship for your stack tier.\n"
        "3. Book your week-2 review on the calendar before you start.\n"
    )

    return "".join(lines)
