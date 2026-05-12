"""Phase 3.1 — image-gen adapter unit tests (stub path).

These don't need a database, so we override the autouse ``setup_db``
fixture from ``conftest.py`` with a no-op for this module.
"""

from __future__ import annotations

import pytest
import pytest_asyncio

from app.services.image_gen import GeneratedImage, ImageProvider, generate_image


@pytest_asyncio.fixture(autouse=True)
async def setup_db():  # noqa: D401 — override conftest autouse
    yield


@pytest.mark.asyncio
async def test_stub_returns_requested_count():
    images = await generate_image("a purple cat in a tophat", n=3)
    assert len(images) == 3
    assert all(isinstance(img, GeneratedImage) for img in images)
    assert all(img.provider == ImageProvider.stub for img in images)


@pytest.mark.asyncio
async def test_stub_is_deterministic():
    a = await generate_image("identical prompt", n=2)
    b = await generate_image("identical prompt", n=2)
    assert [i.url for i in a] == [i.url for i in b]
    assert [i.seed for i in a] == [i.seed for i in b]


@pytest.mark.asyncio
async def test_stub_produces_data_uri():
    images = await generate_image("anything", n=1)
    assert images[0].url.startswith("data:image/svg+xml;base64,")


@pytest.mark.asyncio
async def test_aspect_ratio_passthrough():
    # Stub doesn't render different aspects, but the call must not crash.
    for ar in ("1:1", "16:9", "9:16", "4:5"):
        out = await generate_image("test", n=1, aspect_ratio=ar)
        assert len(out) == 1
