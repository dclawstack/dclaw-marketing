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
    """Returns the user prompt with brand-style direction prepended for
    **image** generation.

    Includes palette + typography + mood. If no Brand Kit is
    configured, returns the raw prompt unchanged so the agent still
    produces *something*.
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


def compose_video_prompt(prompt: str, brand_kit: BrandKit | None) -> str:
    """Returns the user prompt with brand-style direction prepended for
    **video** generation.

    Video models typically respond better to compact prompts than
    SDXL, so we keep the prefix lean: palette and mood only — no
    typography (most video models can't render text reliably anyway).
    """
    prompt = prompt.strip()
    if brand_kit is None:
        return prompt

    fragments: list[str] = []

    palette = _palette_tokens(brand_kit.palette_json)
    if palette:
        # Compact form for video — palette first, no full sentence.
        fragments.append("palette: " + ", ".join(palette))

    mood = _mood_tokens(brand_kit.voice_json)
    if mood:
        fragments.append("mood: " + ", ".join(mood))

    if not fragments:
        return prompt

    prefix = " | ".join(fragments)
    return f"({prefix}) {prompt}"


def compose_voice_text(text: str, brand_kit: BrandKit | None) -> str:
    """For voice / TTS the brand kit's voice sliders matter more than
    palette. We do NOT mutate the text content — TTS reads what you
    give it verbatim. Instead, callers should use the returned
    ``voice_id`` hint (see :func:`pick_voice_id`).

    This function is the no-op text passthrough kept for symmetry with
    the other composers.
    """
    return text.strip()


def pick_voice_id(brand_kit: BrandKit | None, default: str) -> str:
    """Selects an ElevenLabs voice id based on the BrandKit's voice
    sliders. Returns ``default`` when no kit, or no slider is set.

    Heuristic:
      formal_casual < 0.4 → formal, choose "Antoni" (deep, calm)
      formal_casual > 0.7 → casual, choose "Rachel" (warm, energetic)
      otherwise           → default

    The brand kit can override entirely via
    ``voice_json["elevenlabs_voice_id"]``.
    """
    if brand_kit is None or not isinstance(brand_kit.voice_json, dict):
        return default
    voice_json = brand_kit.voice_json
    override = voice_json.get("elevenlabs_voice_id")
    if isinstance(override, str) and override:
        return override
    sliders = voice_json.get("sliders") or {}
    fc = sliders.get("formal_casual")
    if isinstance(fc, (int, float)):
        if fc < 0.4:
            return "ErXwobaYiN019PkySvjV"  # "Antoni" — formal/calm
        if fc > 0.7:
            return "21m00Tcm4TlvDq8ikWAM"  # "Rachel" — casual/warm
    return default


def compose_music_prompt(prompt: str, brand_kit: BrandKit | None) -> str:
    """Returns the user prompt with brand mood prepended for **music**
    generation.

    Music models (MusicGen, Suno) respond to genre + mood + tempo
    descriptors. We map brand voice sliders to those:

      formal     → "ambient, soft strings, slow tempo"
      casual     → "upbeat acoustic, warm guitar, mid tempo"
      playful    → "energetic, bright synth, fast tempo"
      serious    → "contemplative, piano, slow tempo"

    Palette and fonts don't apply to music — ignored.
    """
    prompt = prompt.strip()
    if brand_kit is None:
        return prompt

    descriptors: list[str] = []
    sliders = (brand_kit.voice_json or {}).get("sliders") or {}

    fc = sliders.get("formal_casual")
    if isinstance(fc, (int, float)):
        if fc < 0.4:
            descriptors.append("ambient, soft strings, slow tempo")
        elif fc > 0.7:
            descriptors.append("upbeat acoustic, warm guitar, mid tempo")

    pe = sliders.get("playful_serious") or sliders.get("serious_playful")
    if isinstance(pe, (int, float)):
        if pe > 0.7:
            descriptors.append("energetic, bright synth, fast tempo")
        elif pe < 0.4:
            descriptors.append("contemplative, piano, slow tempo")

    if not descriptors:
        return prompt

    return f"{', '.join(descriptors)}. {prompt}"


__all__ = [
    "compose_visual_prompt",
    "compose_video_prompt",
    "compose_voice_text",
    "compose_music_prompt",
    "pick_voice_id",
    "get_active_brand_kit",
]
