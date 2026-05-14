"""`dont_say` lint pass (S4-B3).

Reads `BrandKit.do_not_say_terms` (a list of banned phrases) and scans
generated text for matches. The agent runtime calls
`lint_text(brand_kit, text)` before surfacing output; on a hit the
runtime issues a `[refine]` retry, and only escalates the original
output to the reviewer queue if the second pass still trips.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


@dataclass
class LintHit:
    term: str
    span: tuple[int, int]


def lint_text(banned_terms: Iterable[str] | None, text: str) -> list[LintHit]:
    """Case-insensitive whole-word scan; returns hit positions."""
    if not banned_terms or not text:
        return []
    hits: list[LintHit] = []
    for term in banned_terms:
        if not term:
            continue
        pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
        for m in pattern.finditer(text):
            hits.append(LintHit(term=term, span=(m.start(), m.end())))
    return hits


def build_refine_prompt(text: str, hits: list[LintHit]) -> str:
    """Prompt the model uses on a [refine] retry."""
    terms = sorted({h.term for h in hits})
    return (
        f"The previous draft contains these brand-banned phrases: "
        f"{', '.join(terms)}.\n\n"
        f"Rewrite the draft below so that none of them appear, while "
        f"preserving meaning and tone.\n\n---\n{text}"
    )
