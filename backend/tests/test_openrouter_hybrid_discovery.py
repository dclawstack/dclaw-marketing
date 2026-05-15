"""Unit tests for the OpenRouter hybrid discovery supplement (S5 #366)."""

from app.services.model_discovery import (
    _frontend_caps_from_modalities,
    _frontend_pricing,
    _openrouter_frontend_supplement,
)


# ---- _frontend_caps_from_modalities --------------------------------------


def test_caps_embeddings():
    caps = _frontend_caps_from_modalities(["embeddings"], ["text", "image"], "x")
    assert caps == ["embedding"]


def test_caps_text_with_image_input_becomes_text_plus_vision():
    caps = _frontend_caps_from_modalities(["text"], ["text", "image"], "vendor/m")
    assert "text" in caps
    assert "image_understanding" in caps


def test_caps_image_generation():
    caps = _frontend_caps_from_modalities(["image"], ["text"], "vendor/m")
    assert "image_generation" in caps


def test_caps_video():
    caps = _frontend_caps_from_modalities(["video"], ["text"], "vendor/m")
    assert "text_to_video" in caps


def test_caps_speech():
    caps = _frontend_caps_from_modalities(["speech"], ["text"], "vendor/m")
    assert "text_to_speech" in caps


def test_caps_transcription():
    caps = _frontend_caps_from_modalities(["transcription"], ["audio"], "vendor/m")
    assert "audio_transcription" in caps


def test_caps_rerank():
    caps = _frontend_caps_from_modalities(["rerank"], ["text"], "vendor/m")
    assert "reranking" in caps


def test_caps_empty_falls_back_to_id_heuristic():
    # Empty modalities → uses capabilities_for_model_id which catches "embed"
    caps = _frontend_caps_from_modalities([], [], "nvidia/some-embed-model")
    assert "embedding" in caps


# ---- _frontend_pricing ----------------------------------------------------


def test_pricing_is_free_flag():
    assert _frontend_pricing({"is_free": True}) == {"is_free": True}


def test_pricing_paid_passes_through():
    out = _frontend_pricing(
        {"pricing": {"prompt": "0.000003", "completion": "0.000015"}}
    )
    assert out == {
        "currency": "USD",
        "prompt": "0.000003",
        "completion": "0.000015",
    }


def test_pricing_all_zero_marks_free():
    out = _frontend_pricing({"pricing": {"prompt": "0", "completion": "0"}})
    assert out == {"is_free": True}


def test_pricing_none_when_endpoint_null():
    assert _frontend_pricing(None) is None
    assert _frontend_pricing({}) is None
    assert _frontend_pricing({"pricing": None}) is None


# ---- _openrouter_frontend_supplement (network mocked) --------------------


def test_supplement_dedupes_against_public(monkeypatch):
    """Models already returned by the public endpoint should be skipped."""
    fake_payload = {
        "data": [
            {
                "slug": "anthropic/claude-3.5-sonnet",  # already in public set
                "name": "Claude 3.5 Sonnet",
                "output_modalities": ["text"],
                "context_length": 200000,
            },
            {
                "slug": "nvidia/llama-nemotron-embed-vl-1b-v2",
                "name": "NVIDIA Llama Nemotron Embed VL 1B V2",
                "output_modalities": ["embeddings"],
                "input_modalities": ["text", "image"],
                "context_length": 131072,
                "endpoint": {
                    "is_free": True,
                    "model_variant_slug": "nvidia/llama-nemotron-embed-vl-1b-v2:free",
                },
            },
            {
                "slug": "openai/text-embedding-3-large",
                "name": "OpenAI text-embedding-3-large",
                "output_modalities": ["embeddings"],
                "input_modalities": ["text"],
                "endpoint": {
                    "pricing": {"prompt": "0.00000013", "completion": "0"},
                    "model_variant_slug": None,
                },
            },
        ]
    }
    from app.services import model_discovery as md

    monkeypatch.setattr(md, "_get_json", lambda url, **_kw: fake_payload)

    skip = {"anthropic/claude-3.5-sonnet"}
    out = _openrouter_frontend_supplement(skip)
    ids = [m.model_id for m in out]
    assert "anthropic/claude-3.5-sonnet" not in ids  # deduped
    assert "nvidia/llama-nemotron-embed-vl-1b-v2:free" in ids  # variant slug used
    assert "openai/text-embedding-3-large" in ids
    # Capabilities and pricing made it through.
    nvidia = next(m for m in out if "nvidia" in m.model_id)
    assert nvidia.capabilities == ["embedding"]
    assert nvidia.pricing == {"is_free": True}
    openai_embed = next(m for m in out if "text-embedding-3-large" in m.model_id)
    assert openai_embed.capabilities == ["embedding"]
    assert openai_embed.pricing["prompt"] == "0.00000013"


def test_supplement_returns_empty_on_network_failure(monkeypatch):
    """If _get_json returns None (HTTP error / timeout), supplement is empty."""
    from app.services import model_discovery as md

    monkeypatch.setattr(md, "_get_json", lambda url, **_kw: None)
    assert _openrouter_frontend_supplement(set()) == []


def test_supplement_skips_malformed_rows(monkeypatch):
    """Rows without `slug` or that aren't dicts are skipped silently."""
    from app.services import model_discovery as md

    monkeypatch.setattr(
        md,
        "_get_json",
        lambda url, **_kw: {
            "data": [
                "not a dict",
                {},  # no slug
                {"slug": "vendor/good", "output_modalities": ["text"]},
            ]
        },
    )
    out = _openrouter_frontend_supplement(set())
    assert [m.model_id for m in out] == ["vendor/good"]
