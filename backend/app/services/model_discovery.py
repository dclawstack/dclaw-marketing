"""Model auto-discovery (S4-M3) + health-check probes (S4-M5).

For each `ModelProvider` we know how to:

1. **Discover** the catalog of models the provider exposes →
   `discover_models_for_provider()` returns a list of
   `{model_id, display_name, capabilities, context_window?, max_output_tokens?}`
   dicts. The Celery task in `app.worker.tasks.model_discovery` writes
   these as `ModelEntry` rows.

2. **Probe health** of the provider as a whole →
   `probe_provider_health()` returns `(HealthStatus, error_message_or_None)`.
   The Celery beat (every 5 min) updates `ModelProvider.health_status`.

For the v1 PR we ship the *strategy table* and a default best-effort
implementation per provider using `httpx`. Where the provider needs a
heavy SDK (boto3 for Bedrock, the google.cloud SDK for Vertex), the
default falls back to `unknown` and the operator must run discovery
manually until those SDKs are wired in — the registry CRUD still works,
just discovery skips. This keeps the PR small while unblocking the rest
of the Model Registry surface.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Iterable
from urllib.parse import urljoin

import httpx

from app.models.model_registry import (
    Capability,
    HealthStatus,
    ModelProvider,
    ProviderType,
)
from app.services.model_registry import (
    BASE_URLS,
    KNOWN_MODELS,
    capabilities_for_model_id,
)
from app.services.secret_box import try_unseal

log = logging.getLogger(__name__)


@dataclass
class DiscoveredModel:
    model_id: str
    display_name: str
    capabilities: list[str]
    context_window: int | None = None
    max_output_tokens: int | None = None
    # Pricing dict (S5 #365). Shapes:
    #   {"prompt": "0.000003", "completion": "0.000015", "currency": "USD"}
    #   {"is_free": True}
    #   None — unknown
    pricing: dict | None = None


def _parse_pricing_from_openrouter(obj: dict, model_id: str) -> dict | None:
    """Extract per-token pricing from an OpenRouter model row.

    OpenRouter ships rates as strings in USD-per-token, e.g.
    `{"prompt": "0.000003", "completion": "0.000015"}`. We forward the
    raw rate but also detect free-tier models so the UI can short-
    circuit to a green chip. (S5 #365)
    """
    if model_id.endswith(":free"):
        return {"is_free": True}
    pr = obj.get("pricing") if isinstance(obj, dict) else None
    if not isinstance(pr, dict):
        return None

    def _as_float(v) -> float | None:
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    prompt = _as_float(pr.get("prompt"))
    completion = _as_float(pr.get("completion"))
    # If both zero, treat as free.
    if prompt == 0 and completion == 0:
        return {"is_free": True}
    out: dict = {"currency": "USD"}
    if pr.get("prompt") is not None:
        out["prompt"] = pr["prompt"]
    if pr.get("completion") is not None:
        out["completion"] = pr["completion"]
    if pr.get("request") is not None:
        out["request"] = pr["request"]
    if pr.get("image") is not None:
        out["image"] = pr["image"]
    return out or None


def _api_key(p: ModelProvider) -> str | None:
    if not p.encrypted_api_key:
        return None
    return try_unseal(p.encrypted_api_key)


def _base_url(p: ModelProvider) -> str:
    return p.base_url or BASE_URLS.get(p.provider_type, "")


# ---------- discovery: OpenAI-compatible / Anthropic / etc. ----------------


def _get_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: float = 15.0,
) -> dict | None:
    try:
        r = httpx.get(url, headers=headers or {}, timeout=timeout)
        if r.status_code != 200:
            log.warning("discover %s -> %s", url, r.status_code)
            return None
        return r.json()
    except httpx.HTTPError as e:
        log.warning("discover %s -> %s", url, e)
        return None


def _openai_compatible_discover(
    base: str, key: str | None, extra_headers: dict[str, str] | None = None
) -> list[DiscoveredModel]:
    headers = {"Accept": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    if extra_headers:
        headers.update(extra_headers)
    data = _get_json(urljoin(base.rstrip("/") + "/", "models"), headers=headers)
    if not data:
        return []
    rows = data.get("data") or data.get("models") or []
    out: list[DiscoveredModel] = []
    for r in rows:
        if isinstance(r, str):
            mid = r
            obj = {}
        else:
            obj = r
            mid = obj.get("id") or obj.get("model") or obj.get("name")
        if not mid:
            continue
        # OpenRouter has architecture.modality
        caps: list[str] = []
        arch = obj.get("architecture") if isinstance(obj, dict) else None
        if arch and isinstance(arch.get("modality"), str):
            mod = arch["modality"]
            if "text->image" in mod:
                caps.append(Capability.image_generation.value)
            if "text->video" in mod:
                caps.append(Capability.text_to_video.value)
            if "text->audio" in mod or "text->speech" in mod:
                caps.append(Capability.text_to_speech.value)
            if "audio->text" in mod or "speech->text" in mod:
                caps.append(Capability.audio_transcription.value)
            if "text->text" in mod:
                caps.append(Capability.text.value)
            if "image->text" in mod:
                caps.append(Capability.image_understanding.value)
                if Capability.text.value not in caps:
                    caps.append(Capability.text.value)
        if not caps:
            caps = capabilities_for_model_id(mid)
        out.append(
            DiscoveredModel(
                model_id=mid,
                display_name=obj.get("name", mid) if isinstance(obj, dict) else mid,
                capabilities=caps,
                context_window=(
                    obj.get("context_length") or obj.get("context_window")
                    if isinstance(obj, dict)
                    else None
                ),
                pricing=_parse_pricing_from_openrouter(obj, mid) if isinstance(obj, dict) else None,
            )
        )
    return out


def _known_list(t: ProviderType) -> list[DiscoveredModel]:
    return [
        DiscoveredModel(
            model_id=m["model_id"],
            display_name=m["display_name"],
            capabilities=list(m["capabilities"]),
            context_window=m.get("context_window"),
            max_output_tokens=m.get("max_output_tokens"),
        )
        for m in KNOWN_MODELS.get(t, [])
    ]


def _ollama_discover(base: str) -> list[DiscoveredModel]:
    data = _get_json(urljoin(base.rstrip("/") + "/", "api/tags"))
    if not data:
        return []
    rows = data.get("models", [])
    out: list[DiscoveredModel] = []
    for r in rows:
        mid = r.get("name") or r.get("model")
        if not mid:
            continue
        # Use heuristic since Ollama tag list has no capability metadata
        out.append(
            DiscoveredModel(
                model_id=mid,
                display_name=mid,
                capabilities=capabilities_for_model_id(mid),
            )
        )
    return out


def _openai_org_header(p: ModelProvider) -> dict[str, str] | None:
    cfg = p.extra_config_json or {}
    org_id = cfg.get("org_id")
    if org_id:
        return {"OpenAI-Organization": org_id}
    return None


def _openrouter_extra_headers() -> dict[str, str]:
    return {"HTTP-Referer": "https://dclaw.io", "X-Title": "DClaw"}


def discover_models_for_provider(p: ModelProvider) -> list[DiscoveredModel]:
    """Top-level dispatcher per provider type."""
    base = _base_url(p)
    key = _api_key(p)

    t = p.provider_type
    if t == ProviderType.anthropic:
        return _known_list(t)
    if t == ProviderType.openai:
        return _openai_compatible_discover(base, key, _openai_org_header(p))
    if t == ProviderType.google_gemini:
        return _known_list(t)
    if t in (ProviderType.google_vertex_ai, ProviderType.aws_bedrock):
        # Native SDKs not wired into this PR; use known list for now.
        return _known_list(t)
    if t == ProviderType.azure_openai:
        # Azure uses ?api-version=...
        version = (p.extra_config_json or {}).get("api_version", "2024-12-01-preview")
        url = urljoin(base.rstrip("/") + "/", f"openai/models?api-version={version}")
        headers = {"api-key": key or "", "Accept": "application/json"}
        data = _get_json(url, headers=headers)
        if not data:
            return []
        out: list[DiscoveredModel] = []
        for r in data.get("data", []):
            mid = r.get("id") or r.get("model")
            if not mid:
                continue
            out.append(
                DiscoveredModel(
                    model_id=mid,
                    display_name=mid,
                    capabilities=capabilities_for_model_id(mid),
                )
            )
        return out
    if t == ProviderType.mistral:
        return _openai_compatible_discover(base, key)
    if t == ProviderType.cohere:
        return _known_list(t)
    if t == ProviderType.voyage_ai:
        return _known_list(t)
    if t == ProviderType.huggingface:
        return _openai_compatible_discover(base, key)
    if t == ProviderType.openrouter:
        return _openai_compatible_discover(base, key, _openrouter_extra_headers())
    if t in (
        ProviderType.groq,
        ProviderType.together_ai,
        ProviderType.fireworks_ai,
        ProviderType.deepseek,
        ProviderType.perplexity,
        ProviderType.sambanova,
        ProviderType.openai_compatible,
    ):
        return _openai_compatible_discover(base, key)
    if t == ProviderType.ollama:
        return _ollama_discover(base)
    if t in (
        ProviderType.replicate,
        ProviderType.elevenlabs,
        ProviderType.runway,
        ProviderType.suno,
        ProviderType.deepgram,
        ProviderType.cartesia,
        ProviderType.fal_ai,
    ):
        return _known_list(t)
    return []


# ---------- health probes ---------------------------------------------------


def _http_probe(
    url: str,
    headers: dict[str, str] | None = None,
    expected_status: int = 200,
    body_contains: str | None = None,
    timeout: float = 10.0,
    method: str = "GET",
) -> tuple[HealthStatus, str | None]:
    try:
        if method == "POST":
            r = httpx.post(url, headers=headers or {}, timeout=timeout, json={})
        else:
            r = httpx.get(url, headers=headers or {}, timeout=timeout)
        if r.status_code != expected_status:
            return HealthStatus.unhealthy, f"HTTP {r.status_code}: {r.text[:200]}"
        if body_contains and body_contains not in r.text:
            return HealthStatus.unhealthy, "expected body content missing"
        return HealthStatus.healthy, None
    except httpx.HTTPError as e:
        return HealthStatus.unhealthy, str(e)[:500]


def probe_provider_health(p: ModelProvider) -> tuple[HealthStatus, str | None]:
    """Lightweight credential check that doesn't spend tokens."""
    if not p.is_active:
        return HealthStatus.disabled, None

    base = _base_url(p)
    key = _api_key(p)
    t = p.provider_type
    auth_h = {"Authorization": f"Bearer {key}"} if key else {}

    if t == ProviderType.anthropic:
        if not key:
            return HealthStatus.unhealthy, "API key missing"
        return _http_probe(
            urljoin("https://api.anthropic.com", "/v1/models"),
            headers={"x-api-key": key, "anthropic-version": "2023-06-01"},
        )
    if t == ProviderType.ollama:
        return _http_probe(base.rstrip("/") + "/", body_contains="Ollama is running")
    if t == ProviderType.elevenlabs:
        return _http_probe(base.rstrip("/") + "/models", headers={"xi-api-key": key or ""})
    if t == ProviderType.cartesia:
        return _http_probe(base.rstrip("/") + "/voices", headers={"X-API-Key": key or ""})
    if t == ProviderType.deepgram:
        return _http_probe(base.rstrip("/") + "/projects", headers={"Authorization": f"Token {key}"} if key else {})
    if t == ProviderType.replicate:
        # Replicate has no list-models endpoint open to PAT — use account
        return _http_probe(
            "https://api.replicate.com/v1/account", headers=auth_h
        )
    if t == ProviderType.fal_ai:
        return _http_probe("https://fal.run/health")
    if t == ProviderType.google_gemini:
        if not key:
            return HealthStatus.unhealthy, "API key missing"
        return _http_probe(
            f"{base.rstrip('/')}/models?key={key}"
        )
    if t in (
        ProviderType.openai,
        ProviderType.azure_openai,
        ProviderType.openrouter,
        ProviderType.groq,
        ProviderType.together_ai,
        ProviderType.fireworks_ai,
        ProviderType.deepseek,
        ProviderType.perplexity,
        ProviderType.sambanova,
        ProviderType.huggingface,
        ProviderType.mistral,
        ProviderType.openai_compatible,
    ):
        extra = _openai_org_header(p) if t == ProviderType.openai else None
        extra = extra or {}
        if t == ProviderType.openrouter:
            extra.update(_openrouter_extra_headers())
        return _http_probe(
            urljoin(base.rstrip("/") + "/", "models"),
            headers={**auth_h, **extra},
        )
    if t == ProviderType.cohere:
        return _http_probe("https://api.cohere.com/v2/models", headers=auth_h)
    if t == ProviderType.voyage_ai:
        return _http_probe("https://api.voyageai.com/v1/models", headers=auth_h)
    if t == ProviderType.runway:
        return _http_probe(base.rstrip("/") + "/models", headers=auth_h)
    if t == ProviderType.suno:
        # No public status endpoint; treat as unknown until a call happens.
        return HealthStatus.unknown, "no public status endpoint"
    if t in (ProviderType.google_vertex_ai, ProviderType.aws_bedrock):
        return HealthStatus.unknown, "SDK probe not yet wired"
    return HealthStatus.unknown, "probe not implemented"
