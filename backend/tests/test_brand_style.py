"""Phase 3.4 — brand-style composer unit tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest_asyncio

from app.agents.brand_style import compose_visual_prompt


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    yield


def _kit(**fields):
    """Build a minimal BrandKit-shaped object — only the fields the
    composer actually reads. We use SimpleNamespace so the test
    doesn't touch the DB or the real model class.
    """
    return SimpleNamespace(
        palette_json=fields.get("palette"),
        fonts_json=fields.get("fonts"),
        voice_json=fields.get("voice"),
    )


def test_no_kit_returns_unchanged():
    out = compose_visual_prompt("a glowing claw", None)
    assert out == "a glowing claw"


def test_palette_is_prepended():
    kit = _kit(palette={"primary": "#7660A8", "secondary": "#9384BD"})
    out = compose_visual_prompt("a glowing claw", kit)
    assert "primary #7660A8" in out
    assert "secondary #9384BD" in out
    assert out.endswith("a glowing claw")


def test_font_directive_is_prepended():
    kit = _kit(fonts={"display": "Poppins", "body": "Inter"})
    out = compose_visual_prompt("a label", kit)
    assert "Poppins" in out


def test_voice_sliders_become_mood():
    kit = _kit(voice={"sliders": {"formal_casual": 0.9, "playful_serious": 0.8}})
    out = compose_visual_prompt("hello", kit)
    assert "casual" in out.lower() or "playful" in out.lower()


def test_empty_brand_kit_returns_raw():
    # All JSON fields None — composer should NOT add any prefix.
    kit = _kit()
    assert compose_visual_prompt("raw prompt", kit) == "raw prompt"
