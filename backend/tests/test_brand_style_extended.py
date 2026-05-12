"""Phase 3.5 — extended brand-style composer unit tests.

The Phase 3.4 module covered ``compose_visual_prompt``. This adds
tests for the new ``compose_video_prompt``, ``compose_music_prompt``,
and ``pick_voice_id`` helpers.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest_asyncio

from app.agents.brand_style import (
    compose_music_prompt,
    compose_video_prompt,
    compose_voice_text,
    pick_voice_id,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


def _kit(**fields):
    return SimpleNamespace(
        palette_json=fields.get("palette"),
        fonts_json=fields.get("fonts"),
        voice_json=fields.get("voice"),
    )


# ---------- compose_video_prompt -------------------------------------


def test_video_no_kit_returns_raw():
    assert compose_video_prompt("a glowing claw", None) == "a glowing claw"


def test_video_compact_palette_prefix():
    kit = _kit(palette={"primary": "#7660A8", "secondary": "#B0A4CE"})
    out = compose_video_prompt("a glowing claw", kit)
    # Video uses a compact pipe-separated prefix wrapped in parens
    assert out.startswith("(palette: ")
    assert "#7660A8" in out
    assert out.endswith("a glowing claw")


def test_video_omits_fonts():
    kit = _kit(fonts={"display": "Poppins"})
    out = compose_video_prompt("text here", kit)
    # Video composer ignores fonts — most video models can't render
    # text reliably anyway.
    assert "Poppins" not in out


def test_video_mood_from_sliders():
    kit = _kit(voice={"sliders": {"formal_casual": 0.85, "playful_serious": 0.85}})
    out = compose_video_prompt("hello", kit)
    assert "mood" in out
    assert "casual" in out.lower() or "playful" in out.lower()


# ---------- compose_music_prompt -------------------------------------


def test_music_no_kit_returns_raw():
    assert compose_music_prompt("lo-fi", None) == "lo-fi"


def test_music_formal_to_ambient():
    kit = _kit(voice={"sliders": {"formal_casual": 0.2}})
    out = compose_music_prompt("ad break", kit)
    assert "ambient" in out.lower()
    assert "slow tempo" in out.lower()
    assert out.endswith("ad break")


def test_music_casual_to_upbeat():
    kit = _kit(voice={"sliders": {"formal_casual": 0.85}})
    out = compose_music_prompt("ad break", kit)
    assert "upbeat" in out.lower()
    assert "warm guitar" in out.lower()


def test_music_playful_to_energetic():
    kit = _kit(voice={"sliders": {"playful_serious": 0.9}})
    out = compose_music_prompt("ad break", kit)
    assert "energetic" in out.lower()


def test_music_serious_to_contemplative():
    kit = _kit(voice={"sliders": {"playful_serious": 0.2}})
    out = compose_music_prompt("ad break", kit)
    assert "contemplative" in out.lower()


def test_music_ignores_palette_and_fonts():
    kit = _kit(
        palette={"primary": "#7660A8"},
        fonts={"display": "Poppins"},
        voice={"sliders": {"formal_casual": 0.2}},
    )
    out = compose_music_prompt("test", kit)
    assert "#7660A8" not in out
    assert "Poppins" not in out


# ---------- pick_voice_id --------------------------------------------


def test_pick_voice_id_default_when_no_kit():
    assert pick_voice_id(None, "default-x") == "default-x"


def test_pick_voice_id_explicit_override_wins():
    kit = _kit(voice={"elevenlabs_voice_id": "custom-123", "sliders": {"formal_casual": 0.1}})
    assert pick_voice_id(kit, "default-x") == "custom-123"


def test_pick_voice_id_formal_picks_antoni():
    kit = _kit(voice={"sliders": {"formal_casual": 0.2}})
    vid = pick_voice_id(kit, "default-x")
    assert vid == "ErXwobaYiN019PkySvjV"  # Antoni


def test_pick_voice_id_casual_picks_rachel():
    kit = _kit(voice={"sliders": {"formal_casual": 0.85}})
    vid = pick_voice_id(kit, "default-x")
    assert vid == "21m00Tcm4TlvDq8ikWAM"  # Rachel


def test_pick_voice_id_balanced_returns_default():
    kit = _kit(voice={"sliders": {"formal_casual": 0.5}})
    assert pick_voice_id(kit, "default-x") == "default-x"


# ---------- compose_voice_text (passthrough) -------------------------


def test_compose_voice_text_strips_whitespace():
    assert compose_voice_text("  hello  ", None) == "hello"


def test_compose_voice_text_passes_through_with_kit():
    kit = _kit(voice={"sliders": {"formal_casual": 0.1}})
    assert compose_voice_text("Hello world.", kit) == "Hello world."
