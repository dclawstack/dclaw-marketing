"""Async / fire-and-forget logger for model invocations (S4-M6 + M8).

Every call site that hits a model imports `log_call()` from here, fills
in token counts + cost + status, and gets back nothing — the write
happens in the background and also publishes to a Redis channel so the
SSE log stream (M8) can pick it up live.

Caller-component constants are defined here so the entire platform
uses the same set of strings.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Final
from uuid import UUID

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.model_call_log import ModelCallLog, ModelCallStatus

log = logging.getLogger(__name__)


# Caller-component constants — keep in sync with the
# Feature-Availability component map in M7.
CALLER_CONDUCTOR: Final = "conductor"
CALLER_CREATIVES: Final = "creatives_agent"
CALLER_SMM: Final = "smm_agent"
CALLER_SEO: Final = "seo_agent"
CALLER_PAID_MEDIA: Final = "paid_media_agent"
CALLER_ANALYST: Final = "analyst_agent"
CALLER_INBOX: Final = "inbox_agent"
CALLER_REVIEWER: Final = "reviewer_agent"
CALLER_KG: Final = "knowledge_graph"
CALLER_EMBEDDINGS: Final = "embeddings"
CALLER_IMAGE_GEN: Final = "image_generation"
CALLER_VOICE_GEN: Final = "voice_generation"
CALLER_VIDEO_GEN: Final = "video_generation"
CALLER_MUSIC_GEN: Final = "music_generation"
CALLER_TRANSCRIPTION: Final = "audio_transcription"
CALLER_BRAND_KIT: Final = "brand_kit_studio"
CALLER_AEO: Final = "aeo_scorer"


def _redis_channel(model_entry_id: UUID) -> str:
    return f"model_logs:{model_entry_id}"


async def log_call(
    db: AsyncSession,
    *,
    model_entry_id: UUID,
    organization_id: UUID | None,
    caller_component: str,
    duration_ms: int,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cost_usd: float = 0.0,
    status: ModelCallStatus = ModelCallStatus.success,
    error_message: str | None = None,
    request_id: str | None = None,
) -> None:
    """Persist + broadcast a single model call log row."""
    row = ModelCallLog(
        model_entry_id=model_entry_id,
        organization_id=organization_id,
        caller_component=caller_component,
        duration_ms=duration_ms,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        status=status,
        error_message=error_message,
        request_id=request_id,
    )
    db.add(row)
    try:
        await db.commit()
    except Exception:  # noqa: BLE001
        await db.rollback()
        log.exception("model_call_log persist failed")
        return

    # Publish to Redis for the SSE stream (best-effort).
    try:
        r = aioredis.from_url(settings.redis_url)
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "component": caller_component,
            "status": status.value,
            "latency_ms": duration_ms,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": cost_usd,
            "error": error_message,
        }
        await r.publish(_redis_channel(model_entry_id), json.dumps(payload))
        await r.aclose()
    except Exception:  # noqa: BLE001
        log.debug("redis publish skipped", exc_info=True)


def fire_and_forget(coro) -> None:
    """Run a coroutine without awaiting — drops the result.

    Use this on the request hot path so logging never adds latency.
    """
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
    except RuntimeError:
        # No running loop (sync caller) — run synchronously.
        asyncio.run(coro)
