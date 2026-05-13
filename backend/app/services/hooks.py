"""B6 Hook & Headline Lab.

Given a draft (any length), return N hook / headline candidates ranked
by an LLM call. Provider-or-stub: when no Anthropic key is configured,
returns a deterministic SHA-based set so dev / CI still works.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from app.agents.anthropic_client import complete


_VARIANT_PATTERN = re.compile(r"^\s*\d+[\.\)]\s*(.+)\s*$", re.MULTILINE)


SYSTEM_PROMPT = """You are a hook and headline generator for marketing copy.

Given a draft, return EXACTLY {n} hook / headline candidates. Each must:
- be 12 words or fewer
- use the brand voice if provided
- vary across patterns (question / contrarian / stat / benefit / specificity / curiosity / urgency)
- avoid emojis, ALL CAPS, and clickbait

Output format: numbered list, one hook per line. Nothing else.

  1. <hook>
  2. <hook>
  3. <hook>

DO NOT include any preface, footer, or commentary.
"""


def _stub_hooks(text: str, n: int) -> list[str]:
    """Deterministic stub hooks for offline dev / CI."""
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    bases = [
        "Why your team keeps missing the deadline",
        "The 30-second test your strategy will fail",
        "Stop optimising. Start shipping.",
        "What pricing pages get wrong",
        "Three numbers that change how you launch",
        "The contrarian read on growth in 2026",
        "Your funnel isn't broken — it's bored",
        "How to write copy that doesn't sound like copy",
        "The headline pattern that converts 2.3× better",
        "Tuesday 10:42am: when your campaign actually starts",
    ]
    out: list[str] = []
    for i in range(n):
        b = bases[i % len(bases)]
        suffix = h[i * 2 : i * 2 + 4]
        out.append(f"{b} ({suffix})")
    return out


def _parse_variants(raw: str, n: int) -> list[str]:
    matches = _VARIANT_PATTERN.findall(raw)
    items = [m.strip() for m in matches if m.strip()]
    if not items:
        # Fallback: split on newlines, accept any non-empty line.
        items = [line.strip() for line in raw.splitlines() if line.strip()]
    return items[:n]


async def generate_hooks(
    *,
    draft_text: str,
    n: int = 30,
    brand_voice: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Returns ``{"hooks": [...], "model": "...", "stub": bool}``."""
    if not draft_text or not draft_text.strip():
        return {"hooks": [], "model": "", "stub": False}

    n = max(1, min(int(n), 60))

    system = SYSTEM_PROMPT.format(n=n)
    if brand_voice:
        voice_line = ", ".join(
            f"{k}: {v}" for k, v in brand_voice.items() if isinstance(v, (str, int, float))
        )
        if voice_line:
            system += f"\nBRAND VOICE: {voice_line}\n"

    user = f"Draft:\n\"\"\"\n{draft_text.strip()}\n\"\"\"\n\nReturn {n} hooks."

    from app.agents.anthropic_client import is_real_provider_configured

    real_provider = is_real_provider_configured()
    try:
        raw = await complete(system=system, user=user, n_variants_hint=n)
        stub = not real_provider
    except Exception:
        raw = ""
        stub = True

    if not raw:
        return {"hooks": _stub_hooks(draft_text, n), "model": "stub", "stub": True}

    hooks = _parse_variants(raw, n)
    if len(hooks) < max(3, n // 3):
        # Sparse / malformed — fall back to stub for usefulness.
        return {"hooks": _stub_hooks(draft_text, n), "model": "stub-fallback", "stub": True}

    return {
        "hooks": hooks,
        "model": "anthropic/claude" if real_provider else "stub/sha256",
        "stub": stub,
    }


__all__ = ["generate_hooks"]
