"""Image-generation provider adapter (Phase 3.1).

Provides a unified async ``generate_image()`` over multiple providers:

- ``replicate``: real provider, called via httpx if REPLICATE_API_TOKEN
  is set. Polls until the prediction completes, returns the resulting
  image URLs.
- ``stub``: deterministic fallback used when no API token is
  configured (or in CI). Produces ``data:image/svg+xml`` data URLs so
  the rest of the pipeline (asset upload, approval requests) works
  unchanged.

Per PLAN-v1.2 §v2.0 §4.3 — Creatives Agent never publishes; it produces
draft assets that land in the Approval Inbox.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
from dataclasses import dataclass
from enum import Enum

import httpx

from app.core.config import settings


class ImageProvider(str, Enum):
    replicate = "replicate"
    stub = "stub"


@dataclass(frozen=True, slots=True)
class GeneratedImage:
    url: str
    """Either a remote URL (replicate) or a data: URI (stub)."""
    provider: ImageProvider
    prompt: str
    seed: int | None


# ---------- stub provider ----------------------------------------------

_STUB_SWATCHES = [
    ("#7660A8", "#F4F0FA"),
    ("#1F2937", "#7660A8"),
    ("#0E7C66", "#F0FAF8"),
    ("#B45309", "#FEF3C7"),
]


def _stub_image(prompt: str, idx: int) -> GeneratedImage:
    """Builds a deterministic SVG showing the prompt — the same prompt
    always renders the same image, which makes tests stable.
    """
    fg, bg = _STUB_SWATCHES[idx % len(_STUB_SWATCHES)]
    truncated = (prompt[:80] + "…") if len(prompt) > 80 else prompt
    safe = (
        truncated.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1024" height="1024" '
        f'viewBox="0 0 1024 1024">'
        f'<rect width="1024" height="1024" fill="{bg}"/>'
        f'<circle cx="512" cy="380" r="200" fill="{fg}" opacity="0.85"/>'
        f'<text x="512" y="780" text-anchor="middle" '
        f'font-family="Inter,system-ui,sans-serif" font-size="32" '
        f'fill="{fg}" font-weight="600">{safe}</text>'
        f"</svg>"
    )
    b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return GeneratedImage(
        url=f"data:image/svg+xml;base64,{b64}",
        provider=ImageProvider.stub,
        prompt=prompt,
        seed=int(hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:8], 16),
    )


# ---------- replicate provider -----------------------------------------

_REPLICATE_BASE = "https://api.replicate.com/v1"
_POLL_INTERVAL_S = 1.5
_POLL_MAX_ATTEMPTS = 80  # ~2 minutes


async def _replicate_generate(
    prompt: str, n: int, aspect_ratio: str
) -> list[GeneratedImage]:
    headers = {
        "Authorization": f"Token {settings.replicate_api_token}",
        "Content-Type": "application/json",
    }
    # The model identifier ends with ``:<version_hash>``; Replicate's
    # /predictions endpoint takes the version hash, not the slug.
    _, _, version = settings.replicate_image_model.partition(":")
    if not version:
        raise RuntimeError(
            "REPLICATE_IMAGE_MODEL must include a version hash "
            "(e.g. 'stability-ai/sdxl:39ed52f...')"
        )

    payload = {
        "version": version,
        "input": {
            "prompt": prompt,
            "num_outputs": n,
            "width": _aspect_to_width(aspect_ratio),
            "height": _aspect_to_height(aspect_ratio),
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        create_resp = await client.post(
            f"{_REPLICATE_BASE}/predictions",
            headers=headers,
            json=payload,
        )
        create_resp.raise_for_status()
        prediction = create_resp.json()
        get_url = prediction["urls"]["get"]

        # Poll until completed.
        for _ in range(_POLL_MAX_ATTEMPTS):
            poll = await client.get(get_url, headers=headers)
            poll.raise_for_status()
            data = poll.json()
            status_ = data.get("status")
            if status_ == "succeeded":
                outputs = data.get("output") or []
                if isinstance(outputs, str):
                    outputs = [outputs]
                return [
                    GeneratedImage(
                        url=u,
                        provider=ImageProvider.replicate,
                        prompt=prompt,
                        seed=None,
                    )
                    for u in outputs
                ]
            if status_ in {"failed", "canceled"}:
                raise RuntimeError(
                    f"Replicate prediction {status_}: "
                    f"{data.get('error', 'no error message')}"
                )
            await asyncio.sleep(_POLL_INTERVAL_S)

        raise TimeoutError("Replicate prediction timed out")


def _aspect_to_width(aspect: str) -> int:
    return {
        "1:1": 1024,
        "16:9": 1344,
        "9:16": 768,
        "4:5": 896,
    }.get(aspect, 1024)


def _aspect_to_height(aspect: str) -> int:
    return {
        "1:1": 1024,
        "16:9": 768,
        "9:16": 1344,
        "4:5": 1120,
    }.get(aspect, 1024)


# ---------- public entry point -----------------------------------------

async def generate_image(
    prompt: str,
    *,
    n: int = 3,
    aspect_ratio: str = "1:1",
) -> list[GeneratedImage]:
    """Returns ``n`` generated images for the given prompt.

    Falls back to a deterministic stub when no provider is configured —
    callers can rely on this always returning at least one image, so
    the UX never breaks on a missing token.
    """
    if settings.replicate_api_token:
        try:
            return await _replicate_generate(prompt, n, aspect_ratio)
        except Exception:
            # Fall through to stub rather than crash the agent run.
            pass
    return [_stub_image(prompt, i) for i in range(n)]


__all__ = ["generate_image", "GeneratedImage", "ImageProvider"]
