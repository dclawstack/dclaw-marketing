"""Brand-style prompt composer (Phase 3.4).

Takes a raw image / video prompt from a user (or another agent) and
prepends the active Brand Kit's visual identity — palette,
typography, mood from the voice sliders — so generated visuals stay
on-brand without the requester having to repeat it every time.

The composer is a pure prompt-rewrite — no LLM call required. Kept
deliberately small so it stays easy to reason about and test.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.brand_kit import BrandKit


def _palette_tokens(palette: dict | None) -> list[str]:
    if not palette:
        return []
    tokens: list[str] = []
    for key in ("primary", "secondary", "accent"):
        value = palette.get(key)
        if isinstance(value, str) and value:
            tokens.append(f"{key} {value}")
    return tokens


def _font_token(fonts: dict | None) -> str | None:
    if not fonts:
        return None
    display = fonts.get("display") or fonts.get("body")
    return str(display) if display else None


def _mood_tokens(voice: dict | None) -> list[str]:
    if not voice:
        return []
    sliders = voice.get("sliders") or {}
    mood: list[str] = []

    fc = sliders.get("formal_casual")
    if isinstance(fc, (int, float)):
        mood.append("formal, editorial" if fc < 0.4 else
                    "casual, conversational" if fc > 0.7 else
                    "balanced, approachable")

    pe = sliders.get("playful_serious") or sliders.get("serious_playful")
    if isinstance(pe, (int, float)):
        # Higher value treated as more playful.
        if pe > 0.7:
            mood.append("playful, energetic")
        elif pe < 0.4:
            mood.append("serious, grounded")

    return mood


async def get_active_brand_kit(
    session: AsyncSession, organization_id: UUID
) -> BrandKit | None:
    result = await session.execute(
        select(BrandKit).where(
            BrandKit.organization_id == organization_id,
            BrandKit.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


def compose_visual_prompt(prompt: str, brand_kit: BrandKit | None) -> str:
    """Returns the user prompt with brand-style direction prepended.

    If no Brand Kit is configured, returns the raw prompt unchanged so
    the agent still produces *something*.
    """
    prompt = prompt.strip()
    if brand_kit is None:
        return prompt

    fragments: list[str] = []

    palette = _palette_tokens(brand_kit.palette_json)
    if palette:
        fragments.append(
            "On-brand colour palette: " + ", ".join(palette) + "."
        )

    font = _font_token(brand_kit.fonts_json)
    if font:
        fragments.append(
            f"Use the {font} typeface for any visible text."
        )

    mood = _mood_tokens(brand_kit.voice_json)
    if mood:
        fragments.append("Mood: " + ", ".join(mood) + ".")

    if not fragments:
        return prompt

    prefix = " ".join(fragments)
    return f"{prefix}\n\n{prompt}"


__all__ = ["compose_visual_prompt", "get_active_brand_kit"]
