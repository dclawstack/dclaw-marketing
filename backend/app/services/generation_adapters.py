"""Generation MCP adapters (S4-B1).

Thin httpx shells for the multimedia providers. Each one takes a
ResolvedModel (provider + key + model_id) and a request payload, calls
the upstream, and returns whatever the upstream returns — the caller
is responsible for plugging the response into the platform's
asset / approval pipeline.

For Sprint-4 we ship adapters with the canonical-shaped request body
per provider. Tests with real keys land in S4-D smoke harness.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.models.model_registry import ProviderType
from app.services.model_resolver import ResolvedModel

log = logging.getLogger(__name__)


class GenerationError(RuntimeError):
    pass


async def _post(
    url: str,
    *,
    headers: dict[str, str],
    json: dict[str, Any],
    timeout: float = 120.0,
) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=timeout) as c:
        r = await c.post(url, headers=headers, json=json)
    if r.status_code >= 300:
        raise GenerationError(f"{r.status_code}: {r.text[:300]}")
    return r.json()


# ---------- Replicate ------------------------------------------------------


async def replicate_image(
    resolved: ResolvedModel, *, prompt: str, version: str | None = None
) -> dict[str, Any]:
    if resolved.provider_type != ProviderType.replicate:
        raise GenerationError("expected provider_type=replicate")
    body = {
        "version": version or "black-forest-labs/flux-schnell:latest",
        "input": {"prompt": prompt},
    }
    return await _post(
        "https://api.replicate.com/v1/predictions",
        headers={
            "Authorization": f"Bearer {resolved.api_key}",
            "Content-Type": "application/json",
        },
        json=body,
    )


# ---------- Runway ---------------------------------------------------------


async def runway_video(
    resolved: ResolvedModel,
    *,
    prompt: str,
    duration_seconds: int = 5,
) -> dict[str, Any]:
    if resolved.provider_type != ProviderType.runway:
        raise GenerationError("expected provider_type=runway")
    body = {
        "model": resolved.model_id or "gen4_turbo",
        "promptText": prompt,
        "duration": duration_seconds,
    }
    return await _post(
        f"{(resolved.base_url or 'https://api.runwayml.com/v1').rstrip('/')}/text_to_video",
        headers={
            "Authorization": f"Bearer {resolved.api_key}",
            "X-Runway-Version": "2024-11-06",
            "Content-Type": "application/json",
        },
        json=body,
    )


# ---------- Suno ----------------------------------------------------------


async def suno_music(
    resolved: ResolvedModel, *, prompt: str, instrumental: bool = False
) -> dict[str, Any]:
    if resolved.provider_type != ProviderType.suno:
        raise GenerationError("expected provider_type=suno")
    body = {"prompt": prompt, "make_instrumental": instrumental}
    return await _post(
        f"{(resolved.base_url or 'https://api.suno.ai/v1').rstrip('/')}/generate",
        headers={
            "Authorization": f"Bearer {resolved.api_key}",
            "Content-Type": "application/json",
        },
        json=body,
    )


# ---------- ElevenLabs (TTS) ----------------------------------------------


async def elevenlabs_tts(
    resolved: ResolvedModel,
    *,
    text: str,
    voice_id: str = "21m00Tcm4TlvDq8ikWAM",
) -> bytes:
    if resolved.provider_type != ProviderType.elevenlabs:
        raise GenerationError("expected provider_type=elevenlabs")
    body = {
        "text": text,
        "model_id": resolved.model_id or "eleven_multilingual_v2",
    }
    async with httpx.AsyncClient(timeout=60.0) as c:
        r = await c.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={
                "xi-api-key": resolved.api_key or "",
                "Content-Type": "application/json",
            },
            json=body,
        )
    if r.status_code >= 300:
        raise GenerationError(f"{r.status_code}: {r.text[:300]}")
    return r.content


# ---------- Cartesia (low-latency TTS) ------------------------------------


async def cartesia_tts(
    resolved: ResolvedModel, *, text: str, voice_id: str = "default"
) -> bytes:
    if resolved.provider_type != ProviderType.cartesia:
        raise GenerationError("expected provider_type=cartesia")
    body = {
        "model_id": resolved.model_id or "sonic-2",
        "transcript": text,
        "voice": {"mode": "id", "id": voice_id},
        "output_format": {
            "container": "wav",
            "encoding": "pcm_s16le",
            "sample_rate": 24000,
        },
    }
    async with httpx.AsyncClient(timeout=60.0) as c:
        r = await c.post(
            "https://api.cartesia.ai/tts/bytes",
            headers={
                "X-API-Key": resolved.api_key or "",
                "Content-Type": "application/json",
            },
            json=body,
        )
    if r.status_code >= 300:
        raise GenerationError(f"{r.status_code}: {r.text[:300]}")
    return r.content


# ---------- Deepgram (STT) -----------------------------------------------


async def deepgram_transcribe(
    resolved: ResolvedModel, *, audio_bytes: bytes, mime: str = "audio/wav"
) -> dict[str, Any]:
    if resolved.provider_type != ProviderType.deepgram:
        raise GenerationError("expected provider_type=deepgram")
    async with httpx.AsyncClient(timeout=120.0) as c:
        r = await c.post(
            "https://api.deepgram.com/v1/listen?model=nova-3&smart_format=true",
            headers={
                "Authorization": f"Token {resolved.api_key}",
                "Content-Type": mime,
            },
            content=audio_bytes,
        )
    if r.status_code >= 300:
        raise GenerationError(f"{r.status_code}: {r.text[:300]}")
    return r.json()
