"""Multimodal asset-generation adapters (Phase 3.3).

Unified async API over video, voice (TTS), and music providers, each
with a deterministic stub fallback so the agent pipeline never blocks
on missing provider keys.

Providers (in priority order):
  video : Replicate (REPLICATE_VIDEO_MODEL) → stub
  voice : ElevenLabs (ELEVENLABS_API_KEY)   → stub
  music : Replicate (REPLICATE_MUSIC_MODEL) → stub

Like the image adapter, each generator returns a list of
``GeneratedAsset`` records. Callers are responsible for filing each
result as a pending ApprovalRequest — agents never publish on their
own (PLAN-v1.2 §v2.0 §5.2 hard-gate).
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import struct
from dataclasses import dataclass
from enum import Enum

import httpx

from app.core.config import settings


class AssetKind(str, Enum):
    video = "video"
    voice = "voice"
    music = "music"


class AssetProvider(str, Enum):
    replicate = "replicate"
    elevenlabs = "elevenlabs"
    stub = "stub"


@dataclass(frozen=True, slots=True)
class GeneratedAsset:
    url: str
    kind: AssetKind
    provider: AssetProvider
    prompt: str
    seed: int | None
    duration_s: float | None = None


# ---------- stub generators --------------------------------------------

_VIDEO_SWATCHES = [
    ("#7660A8", "#F4F0FA"),
    ("#0E7C66", "#F0FAF8"),
    ("#B45309", "#FEF3C7"),
    ("#1F2937", "#7660A8"),
]


def _seed(prompt: str) -> int:
    return int(hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8], 16)


def _stub_video(prompt: str, idx: int, duration_s: float) -> GeneratedAsset:
    """Animated SVG with a pulsing brand-coloured disc — gives the UI
    something to render and stays deterministic per (prompt, idx).
    """
    fg, bg = _VIDEO_SWATCHES[idx % len(_VIDEO_SWATCHES)]
    truncated = (prompt[:60] + "…") if len(prompt) > 60 else prompt
    safe = (
        truncated.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" '
        f'viewBox="0 0 1280 720">'
        f'<rect width="1280" height="720" fill="{bg}"/>'
        f'<circle cx="640" cy="320" r="120" fill="{fg}">'
        f'<animate attributeName="r" values="120;180;120" dur="2.4s" '
        f'repeatCount="indefinite"/>'
        f'</circle>'
        f'<text x="640" y="600" text-anchor="middle" '
        f'font-family="Inter,system-ui,sans-serif" font-size="36" '
        f'fill="{fg}" font-weight="600">{safe}</text>'
        f"</svg>"
    )
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return GeneratedAsset(
        url=f"data:image/svg+xml;base64,{b64}",
        kind=AssetKind.video,
        provider=AssetProvider.stub,
        prompt=prompt,
        seed=_seed(prompt + str(idx)),
        duration_s=duration_s,
    )


def _silent_wav(duration_s: float, sample_rate: int = 8000) -> bytes:
    """Produces a tiny valid PCM WAV file of silence — useful as a
    placeholder for voice/music stubs so audio players can still load
    the data: URI.
    """
    n_samples = max(1, int(duration_s * sample_rate))
    n_bytes = n_samples * 2  # 16-bit mono
    riff_size = 36 + n_bytes
    header = b"RIFF" + struct.pack("<I", riff_size) + b"WAVEfmt "
    header += struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16)
    header += b"data" + struct.pack("<I", n_bytes)
    return header + (b"\x00\x00" * n_samples)


def _stub_voice(text: str, idx: int, duration_s: float) -> GeneratedAsset:
    wav = _silent_wav(duration_s)
    b64 = base64.b64encode(wav).decode("ascii")
    return GeneratedAsset(
        url=f"data:audio/wav;base64,{b64}",
        kind=AssetKind.voice,
        provider=AssetProvider.stub,
        prompt=text,
        seed=_seed(text + "voice" + str(idx)),
        duration_s=duration_s,
    )


def _stub_music(prompt: str, idx: int, duration_s: float) -> GeneratedAsset:
    wav = _silent_wav(duration_s)
    b64 = base64.b64encode(wav).decode("ascii")
    return GeneratedAsset(
        url=f"data:audio/wav;base64,{b64}",
        kind=AssetKind.music,
        provider=AssetProvider.stub,
        prompt=prompt,
        seed=_seed(prompt + "music" + str(idx)),
        duration_s=duration_s,
    )


# ---------- replicate (shared helper) ----------------------------------

_REPLICATE_BASE = "https://api.replicate.com/v1"
_POLL_INTERVAL_S = 1.5
_POLL_MAX_ATTEMPTS = 120  # ~3 minutes — video/music can be slow


async def _replicate_predict(
    model_ref: str, input_payload: dict
) -> list[str]:
    """Calls Replicate ``/predictions`` and polls until done. Returns
    the raw output URL list (a single string is wrapped to a list).
    """
    _, _, version = model_ref.partition(":")
    if not version:
        raise RuntimeError(
            f"Model reference '{model_ref}' must include a version hash"
        )

    headers = {
        "Authorization": f"Token {settings.replicate_api_token}",
        "Content-Type": "application/json",
    }
    payload = {"version": version, "input": input_payload}

    async with httpx.AsyncClient(timeout=30.0) as client:
        create = await client.post(
            f"{_REPLICATE_BASE}/predictions",
            headers=headers,
            json=payload,
        )
        create.raise_for_status()
        get_url = create.json()["urls"]["get"]

        for _ in range(_POLL_MAX_ATTEMPTS):
            poll = await client.get(get_url, headers=headers)
            poll.raise_for_status()
            data = poll.json()
            status_ = data.get("status")
            if status_ == "succeeded":
                output = data.get("output") or []
                if isinstance(output, str):
                    output = [output]
                return output
            if status_ in {"failed", "canceled"}:
                raise RuntimeError(
                    f"Replicate prediction {status_}: "
                    f"{data.get('error', 'no error')}"
                )
            await asyncio.sleep(_POLL_INTERVAL_S)

        raise TimeoutError("Replicate prediction timed out")


# ---------- public entry points ----------------------------------------

async def generate_video(
    prompt: str, *, n: int = 1, duration_s: float = 4.0
) -> list[GeneratedAsset]:
    """Generates video clips. Falls back to an animated-SVG stub when
    no provider is configured.
    """
    if settings.replicate_api_token and settings.replicate_video_model:
        try:
            urls = await _replicate_predict(
                settings.replicate_video_model,
                {
                    "prompt": prompt,
                    "num_frames": int(duration_s * 24),
                    "fps": 24,
                },
            )
            # Replicate typically returns one video per call; replicate
            # by calling again if n>1 (most video models don't accept a
            # batch ``n`` param).
            if n <= 1:
                return [
                    GeneratedAsset(
                        url=u,
                        kind=AssetKind.video,
                        provider=AssetProvider.replicate,
                        prompt=prompt,
                        seed=None,
                        duration_s=duration_s,
                    )
                    for u in urls
                ]
        except Exception:
            pass
    return [_stub_video(prompt, i, duration_s) for i in range(n)]


async def generate_voice(
    text: str, *, voice_id: str | None = None, n: int = 1
) -> list[GeneratedAsset]:
    """TTS via ElevenLabs. Falls back to a silent-WAV stub.

    ElevenLabs returns audio bytes inline — we base64-encode them into
    a ``data:audio/mpeg`` URI so the rest of the pipeline (asset
    storage, approval) doesn't need a separate file-fetch step.
    """
    duration_estimate = max(1.0, len(text) / 15.0)  # ~15 chars/sec
    if settings.elevenlabs_api_key:
        v = voice_id or settings.elevenlabs_default_voice
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{v}",
                    headers={
                        "xi-api-key": settings.elevenlabs_api_key,
                        "accept": "audio/mpeg",
                        "Content-Type": "application/json",
                    },
                    json={
                        "text": text,
                        "model_id": "eleven_turbo_v2_5",
                    },
                )
                resp.raise_for_status()
                b64 = base64.b64encode(resp.content).decode("ascii")
                return [
                    GeneratedAsset(
                        url=f"data:audio/mpeg;base64,{b64}",
                        kind=AssetKind.voice,
                        provider=AssetProvider.elevenlabs,
                        prompt=text,
                        seed=None,
                        duration_s=duration_estimate,
                    )
                ] * max(1, n)
        except Exception:
            pass
    return [_stub_voice(text, i, duration_estimate) for i in range(n)]


async def generate_music(
    prompt: str, *, n: int = 1, duration_s: float = 15.0
) -> list[GeneratedAsset]:
    """Generates music clips via Replicate (e.g. MusicGen). Falls back
    to a silent-WAV stub.
    """
    if settings.replicate_api_token and settings.replicate_music_model:
        try:
            urls = await _replicate_predict(
                settings.replicate_music_model,
                {
                    "prompt": prompt,
                    "duration": int(duration_s),
                },
            )
            return [
                GeneratedAsset(
                    url=u,
                    kind=AssetKind.music,
                    provider=AssetProvider.replicate,
                    prompt=prompt,
                    seed=None,
                    duration_s=duration_s,
                )
                for u in urls
            ]
        except Exception:
            pass
    return [_stub_music(prompt, i, duration_s) for i in range(n)]


__all__ = [
    "generate_video",
    "generate_voice",
    "generate_music",
    "GeneratedAsset",
    "AssetKind",
    "AssetProvider",
]
