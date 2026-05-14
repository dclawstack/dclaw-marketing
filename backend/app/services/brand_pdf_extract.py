"""Brand Setup Studio — PDF → palette/fonts/voice extractor (S4-E1).

A best-effort parser that reads a brand-guideline PDF and returns a
draft BrandKit suggestion. The actual extraction is intentionally
lightweight:

  - palette  → run a simple regex for `#RRGGBB` strings; dedupe; first 6
  - fonts    → look for known font family names (Inter, Roboto, ...)
  - voice    → LLM pass: a short prompt summarising the doc tone

This isn't perfect; the UI lets the operator edit each field before
hitting "Save". Good enough for Sprint 4.
"""

from __future__ import annotations

import re
from typing import Any


_HEX_RX = re.compile(r"#([0-9A-Fa-f]{6})\b")

KNOWN_FONTS = (
    "Inter", "Roboto", "Open Sans", "Lato", "Poppins", "Montserrat",
    "Source Sans", "Source Sans Pro", "Source Sans 3", "Nunito",
    "Raleway", "Merriweather", "Playfair Display", "PT Sans", "PT Serif",
    "Helvetica", "Helvetica Neue", "Arial", "Georgia", "Times New Roman",
    "Roboto Mono", "JetBrains Mono", "Fira Code", "IBM Plex Sans",
    "IBM Plex Mono", "DM Sans", "DM Serif Display", "Manrope", "Karla",
    "Outfit", "Geist", "Geist Mono",
)


def extract_palette(text: str, *, limit: int = 6) -> list[str]:
    """Return the first `limit` unique #RRGGBB hex codes found in the text."""
    seen: list[str] = []
    for m in _HEX_RX.finditer(text):
        hex_code = f"#{m.group(1).upper()}"
        if hex_code not in seen:
            seen.append(hex_code)
        if len(seen) >= limit:
            break
    return seen


def extract_fonts(text: str) -> list[str]:
    """Return the unique font names in the text from the known list."""
    found: list[str] = []
    for name in KNOWN_FONTS:
        if re.search(rf"\b{re.escape(name)}\b", text, re.IGNORECASE):
            if name not in found:
                found.append(name)
    return found


def extract_voice_fragments(text: str) -> dict[str, Any]:
    """Heuristic voice profile from a brand-guidelines PDF.

    Sprint-4 ships the deterministic heuristic. The agent runtime
    upgrade pulls in a follow-up Claude pass; until then this gives
    the operator a reasonable starting point that they can edit.
    """
    lower = text.lower()
    sliders = {
        "formal_vs_casual": 0.5,
        "serious_vs_playful": 0.5,
        "matter_of_fact_vs_enthusiastic": 0.5,
    }
    if "casual" in lower or "friendly" in lower or "relaxed" in lower:
        sliders["formal_vs_casual"] = 0.7
    if "formal" in lower or "professional" in lower:
        sliders["formal_vs_casual"] = 0.3
    if "playful" in lower or "fun" in lower or "quirky" in lower:
        sliders["serious_vs_playful"] = 0.7
    if "serious" in lower or "authoritative" in lower:
        sliders["serious_vs_playful"] = 0.3
    if "enthusiastic" in lower or "energetic" in lower or "vibrant" in lower:
        sliders["matter_of_fact_vs_enthusiastic"] = 0.7

    do_say: list[str] = []
    dont_say: list[str] = []
    for line in text.splitlines():
        s = line.strip().lower()
        if not s:
            continue
        if s.startswith("do say") or s.startswith("say:"):
            do_say.append(line.strip()[6:].strip(": "))
        elif s.startswith("don't say") or s.startswith("avoid") or s.startswith("never say"):
            dont_say.append(line.strip().split(":", 1)[-1].strip())

    return {
        "sliders": sliders,
        "do_say_terms": [t for t in do_say if t][:10],
        "do_not_say_terms": [t for t in dont_say if t][:10],
    }


def extract_brand_kit_from_text(text: str) -> dict[str, Any]:
    """Single entry point. Returns the dict that pre-fills the
    BrandKit form on /brand-insights or wherever."""
    return {
        "palette": extract_palette(text),
        "fonts": extract_fonts(text),
        "voice": extract_voice_fragments(text),
    }
