"""B4 Repurposing Engine (SP3-11).

Takes one piece of source copy and rewrites it for a different channel,
honouring the platform's character limit + native shape (X thread,
LinkedIn long-form, Instagram caption, blog snippet, …).
"""

from __future__ import annotations

import hashlib
from typing import Any

from app.agents.anthropic_client import complete, is_real_provider_configured


CHANNEL_HINTS: dict[str, dict[str, Any]] = {
    "linkedin": {
        "limit": 3000,
        "shape": "single long-form post; 3-6 short paragraphs; one strong hook line up top; no hashtags unless brief asks",
    },
    "x": {
        "limit": 280,
        "shape": "single tweet OR a 3-5 part thread. If a thread, prefix each part 1/, 2/, … Each part ≤ 280 chars including the prefix.",
    },
    "x_thread": {
        "limit": 280,
        "shape": "always a 3-7 part thread; prefix each part 1/, 2/, …; each part ≤ 280 chars",
    },
    "instagram": {
        "limit": 2200,
        "shape": "carousel caption — short hook, ~6 punchy lines, 5-10 relevant hashtags grouped at the end",
    },
    "threads": {
        "limit": 500,
        "shape": "single short post or 2-part follow-up; conversational, no hashtags",
    },
    "blog": {
        "limit": 8000,
        "shape": "outline + first-pass draft: H2 / H3 headings, intro, 3-4 body sections, conclusion; markdown",
    },
    "newsletter": {
        "limit": 4000,
        "shape": "subject line (≤60 chars) on line 1, preheader (≤90 chars) on line 2, then the body with H2 section headings",
    },
    "bluesky": {
        "limit": 300,
        "shape": "one short post, conversational, no hashtags",
    },
    "tiktok_caption": {
        "limit": 150,
        "shape": "short hook + 1-2 relevant emojis + 2-3 hashtags",
    },
    "youtube_description": {
        "limit": 5000,
        "shape": "1-paragraph summary, then chapter timestamps, then 3-5 hashtags",
    },
}


SYSTEM_TEMPLATE = """You are a copy-repurposing specialist. Take the source copy below \
and rewrite it for the target channel. Honour the channel's shape and \
character limit exactly. Preserve the core message and any specific claims \
or numbers. Do not invent new facts.

TARGET CHANNEL: {channel}
SHAPE: {shape}
HARD CHARACTER LIMIT: {limit}

Output ONLY the rewritten copy. No commentary, no headers, no surrounding \
quotes. If a thread, emit each part on its own line.
"""


def _stub(channel: str, source_text: str) -> str:
    digest = hashlib.sha256(source_text.encode("utf-8")).hexdigest()[:8]
    return f"[stub repurpose · {channel} · {digest}] " + source_text[:120]


async def repurpose(
    *,
    source_text: str,
    target_channel: str,
    brand_voice: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return ``{"channel", "output", "model", "stub"}``."""
    if not source_text or not source_text.strip():
        return {"channel": target_channel, "output": "", "model": "", "stub": False}

    spec = CHANNEL_HINTS.get(target_channel, {"limit": 1000, "shape": "free-form"})
    system = SYSTEM_TEMPLATE.format(
        channel=target_channel, shape=spec["shape"], limit=spec["limit"]
    )
    if brand_voice:
        voice_line = ", ".join(
            f"{k}: {v}" for k, v in brand_voice.items() if isinstance(v, (str, int, float))
        )
        if voice_line:
            system += f"\nBRAND VOICE: {voice_line}\n"

    user = f"Source copy:\n\"\"\"\n{source_text.strip()}\n\"\"\""

    real = is_real_provider_configured()
    try:
        raw = await complete(system=system, user=user, n_variants_hint=1)
    except Exception:
        raw = ""

    if not raw or not raw.strip():
        return {
            "channel": target_channel,
            "output": _stub(target_channel, source_text),
            "model": "stub/sha256",
            "stub": True,
        }
    return {
        "channel": target_channel,
        "output": raw.strip(),
        "model": "anthropic/claude" if real else "stub/sha256",
        "stub": not real,
    }


__all__ = ["repurpose", "CHANNEL_HINTS"]
