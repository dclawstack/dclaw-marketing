"""Phase 3.3 — asset-gen adapter unit tests (stub path)."""

from __future__ import annotations

import base64
import struct

import pytest
import pytest_asyncio

from app.services.asset_gen import (
    AssetKind,
    AssetProvider,
    generate_music,
    generate_video,
    generate_voice,
)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():  # override the autouse fixture in conftest.py
    yield


def _decode_data_uri(uri: str) -> tuple[str, bytes]:
    assert uri.startswith("data:")
    mime, _, b64 = uri[len("data:") :].partition(";base64,")
    return mime, base64.b64decode(b64)


@pytest.mark.asyncio
async def test_video_stub_returns_count_and_brand_svg():
    assets = await generate_video("a glowing claw in space", n=3, duration_s=4.0)
    assert len(assets) == 3
    for a in assets:
        assert a.kind == AssetKind.video
        assert a.provider == AssetProvider.stub
        mime, payload = _decode_data_uri(a.url)
        assert mime == "image/svg+xml"
        # Brand palette must appear so the UI renders in-brand.
        assert b"#7660A8" in payload or b"#0E7C66" in payload or b"#B45309" in payload or b"#1F2937" in payload


@pytest.mark.asyncio
async def test_voice_stub_returns_valid_wav():
    assets = await generate_voice("hello world from dclaw")
    assert len(assets) == 1
    mime, wav = _decode_data_uri(assets[0].url)
    assert mime == "audio/wav"
    # RIFF/WAVE header sanity check
    assert wav[:4] == b"RIFF"
    assert wav[8:12] == b"WAVE"
    # Sample rate is little-endian uint32 at offset 24
    sample_rate = struct.unpack("<I", wav[24:28])[0]
    assert sample_rate == 8000


@pytest.mark.asyncio
async def test_music_stub_duration_passthrough():
    assets = await generate_music("lo-fi hip hop", n=2, duration_s=8.0)
    assert len(assets) == 2
    assert all(a.duration_s == 8.0 for a in assets)
    assert all(a.kind == AssetKind.music for a in assets)


@pytest.mark.asyncio
async def test_stubs_are_deterministic():
    a = await generate_video("identical", n=2, duration_s=4.0)
    b = await generate_video("identical", n=2, duration_s=4.0)
    assert [x.url for x in a] == [x.url for x in b]
    assert [x.seed for x in a] == [x.seed for x in b]
