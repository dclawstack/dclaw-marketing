"""AEO — Answer Engine Optimisation scoring (S4-K1/K2).

Scores a page for AI-search discoverability (ChatGPT browse / Perplexity
/ Claude web / Google AI Overview). The scoring rubric is intentionally
simple in Sprint 4 — a flat checklist with weights — so we can ship
quickly. Sprint 5 will swap the heuristic for an LLM-judged version.

Rubric:
  * direct_answer       (20) — first paragraph answers the H1 question
  * question_h1         (10) — H1 is phrased as a question
  * faq_present         (15) — at least one <h2>FAQ</h2> or "Q: / A:" pair
  * structured_data     (15) — JSON-LD or schema.org tags present
  * tldr_block          (10) — TL;DR / Summary / Key takeaways block
  * concise_paragraphs  (10) — average paragraph <= 80 words
  * citations           (10) — 3+ outbound citations to reputable sources
  * uniqueness          (10) — no duplicated paragraph blocks

Returns:
  {"score": 0-100, "weak_spots": [{"name": ..., "passes": bool,
    "weight": int, "note": "..."}], "details": {...}}
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_WORD_RX = re.compile(r"\S+")


@dataclass
class Check:
    name: str
    weight: int
    passes: bool
    note: str


def _h1(text: str) -> str | None:
    m = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.IGNORECASE | re.DOTALL)
    if m:
        return re.sub(r"<[^>]+>", "", m.group(1)).strip()
    # markdown
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def _paragraphs(text: str) -> list[str]:
    # Split on double newlines after stripping tags so this works for
    # both HTML and Markdown.
    plain = re.sub(r"<[^>]+>", " ", text)
    paras = [p.strip() for p in re.split(r"\n\s*\n", plain) if p.strip()]
    return paras


def score_page(text: str) -> dict[str, Any]:
    h1 = _h1(text) or ""
    paras = _paragraphs(text)
    lower = text.lower()

    direct_answer = bool(paras) and h1 and (
        any(
            kw in paras[0].lower()
            for kw in ("answer", "is ", "are ", "yes,", "no,")
        )
    )
    question_h1 = bool(h1) and (
        h1.strip().endswith("?")
        or any(h1.lower().startswith(w) for w in ("how ", "what ", "why ", "when ", "where ", "is ", "are "))
    )
    faq_present = (
        "<h2>faq" in lower
        or "## faq" in lower
        or bool(re.search(r"\bq:\s.*\ba:\s", lower, re.DOTALL))
    )
    structured_data = (
        '"@context"' in text
        and "schema.org" in lower
    )
    tldr_block = any(
        kw in lower for kw in ("tl;dr", "tldr", "key takeaway", "summary:")
    )
    concise_paragraphs = bool(paras) and (
        sum(len(_WORD_RX.findall(p)) for p in paras) / max(1, len(paras))
        <= 80
    )
    citations = len(re.findall(r"https?://", text)) >= 3
    uniqueness = len(set(paras)) >= max(1, int(0.9 * len(paras)))

    checks: list[Check] = [
        Check("direct_answer", 20, bool(direct_answer),
              "H1 question is answered in the first paragraph."),
        Check("question_h1", 10, bool(question_h1),
              "H1 is phrased as a question."),
        Check("faq_present", 15, bool(faq_present),
              "Page has an FAQ section AI search engines can quote."),
        Check("structured_data", 15, bool(structured_data),
              "JSON-LD / schema.org structured data present."),
        Check("tldr_block", 10, bool(tldr_block),
              "Top-of-page TL;DR / Key takeaways block."),
        Check("concise_paragraphs", 10, bool(concise_paragraphs),
              "Average paragraph ≤ 80 words."),
        Check("citations", 10, bool(citations),
              "≥ 3 outbound citations."),
        Check("uniqueness", 10, bool(uniqueness),
              "No near-duplicate paragraph blocks."),
    ]
    score = sum(c.weight for c in checks if c.passes)
    weak_spots = [
        {"name": c.name, "passes": c.passes, "weight": c.weight, "note": c.note}
        for c in checks
        if not c.passes
    ]
    return {
        "score": score,
        "weak_spots": weak_spots,
        "details": {c.name: c.passes for c in checks},
    }


def build_fix_prompt(text: str, score_result: dict[str, Any]) -> str:
    """K4 — LLM-driven fix prompt: hand this to the Creatives Agent
    to rewrite the page closing the failed checks."""
    failed = ", ".join(s["name"] for s in score_result["weak_spots"])
    if not failed:
        return ""
    return (
        f"Rewrite the page below to close these AEO weak spots: {failed}.\n"
        "Preserve the overall message + brand voice. Output the rewritten "
        "page only, no preamble.\n\n---\n"
        f"{text}"
    )
