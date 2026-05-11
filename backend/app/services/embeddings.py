"""Embedding service — turns text into vectors.

Pluggable provider — default is OpenAI text-embedding-3-small. When
no API key is configured, returns a deterministic stub vector so
tests + dev environments work without external creds.
"""

from __future__ import annotations

import hashlib
import logging

from app.core.config import settings


logger = logging.getLogger(__name__)

# 1536-dim default — matches DocumentChunk.embedding column. Override
# via settings.openai_embedding_model in the future.
EMBEDDING_DIM = 1536
DEFAULT_MODEL = "openai/text-embedding-3-small"


def _stub_embedding(text: str) -> list[float]:
    """Deterministic pseudo-embedding for dev/test environments.

    Hashes the text and seeds a float vector. Not semantically
    meaningful — only used when no real embedding provider is
    configured. Same input → same vector (so retrieval-by-text gives
    stable results in tests).
    """
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    # Repeat the 32-byte digest until we have EMBEDDING_DIM floats
    repeats = (EMBEDDING_DIM // 32) + 1
    raw = (digest * repeats)[:EMBEDDING_DIM]
    # Normalize to [-1, 1]
    return [(b - 128) / 128.0 for b in raw]


def is_real_provider_configured() -> bool:
    return bool(settings.openai_api_key)


async def embed_text(text: str, *, model: str = DEFAULT_MODEL) -> tuple[list[float], str]:
    """Embed a single text. Returns (vector, model_used).

    Defers to OpenAI if openai_api_key is set, otherwise the stub.
    """
    if not is_real_provider_configured():
        return _stub_embedding(text), "stub/sha256"

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        openai_model = model.split("/", 1)[-1] if "/" in model else model
        res = await client.embeddings.create(input=text, model=openai_model)
        return res.data[0].embedding, model
    except Exception:
        logger.exception("OpenAI embedding failed; falling back to stub.")
        return _stub_embedding(text), "stub/sha256-fallback"


async def embed_texts(
    texts: list[str], *, model: str = DEFAULT_MODEL
) -> tuple[list[list[float]], str]:
    """Batch embed. OpenAI accepts arrays in a single request — cheaper
    + lower latency than one-by-one.
    """
    if not texts:
        return [], "stub/sha256"

    if not is_real_provider_configured():
        return [_stub_embedding(t) for t in texts], "stub/sha256"

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        openai_model = model.split("/", 1)[-1] if "/" in model else model
        res = await client.embeddings.create(input=texts, model=openai_model)
        return [d.embedding for d in res.data], model
    except Exception:
        logger.exception("OpenAI batch embedding failed; falling back to stub.")
        return [_stub_embedding(t) for t in texts], "stub/sha256-fallback"


def embed_text_sync(text: str, *, model: str = DEFAULT_MODEL) -> tuple[list[float], str]:
    """Sync version for use inside Celery tasks (which are sync)."""
    if not is_real_provider_configured():
        return _stub_embedding(text), "stub/sha256"
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        openai_model = model.split("/", 1)[-1] if "/" in model else model
        res = client.embeddings.create(input=text, model=openai_model)
        return res.data[0].embedding, model
    except Exception:
        logger.exception("OpenAI embedding (sync) failed; falling back to stub.")
        return _stub_embedding(text), "stub/sha256-fallback"


def embed_texts_sync(
    texts: list[str], *, model: str = DEFAULT_MODEL
) -> tuple[list[list[float]], str]:
    if not texts:
        return [], "stub/sha256"
    if not is_real_provider_configured():
        return [_stub_embedding(t) for t in texts], "stub/sha256"
    try:
        from openai import OpenAI
        client = OpenAI(api_key=settings.openai_api_key)
        openai_model = model.split("/", 1)[-1] if "/" in model else model
        res = client.embeddings.create(input=texts, model=openai_model)
        return [d.embedding for d in res.data], model
    except Exception:
        logger.exception("OpenAI batch (sync) failed; falling back to stub.")
        return [_stub_embedding(t) for t in texts], "stub/sha256-fallback"


__all__ = [
    "EMBEDDING_DIM",
    "DEFAULT_MODEL",
    "embed_text",
    "embed_texts",
    "embed_text_sync",
    "embed_texts_sync",
    "is_real_provider_configured",
]
