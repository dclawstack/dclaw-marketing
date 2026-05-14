"""Model Registry service layer — provider metadata + helpers.

Defines per-provider defaults (base URL, default capabilities, auth shape)
that the API + auto-discovery worker (M3) + health-check beat (M5) use.

Reading this file should be enough to know:
- which providers exist
- which input fields each provider's CRUD form needs
- which capability tags are baked-in for known model IDs
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.model_registry import Capability, ProviderType


# Static base-URL defaults per provider type. Used by health-check + discovery
# when the operator hasn't overridden in `ModelProvider.base_url`. Providers
# whose base URL is locked in the UI also fall through here.
BASE_URLS: dict[ProviderType, str] = {
    ProviderType.anthropic: "https://api.anthropic.com",
    ProviderType.openai: "https://api.openai.com/v1",
    ProviderType.google_gemini: "https://generativelanguage.googleapis.com/v1beta",
    ProviderType.mistral: "https://api.mistral.ai/v1",
    ProviderType.cohere: "https://api.cohere.com/v2",
    ProviderType.voyage_ai: "https://api.voyageai.com/v1",
    ProviderType.huggingface: "https://router.huggingface.co/v1",
    ProviderType.openrouter: "https://openrouter.ai/api/v1",
    ProviderType.groq: "https://api.groq.com/openai/v1",
    ProviderType.together_ai: "https://api.together.xyz/v1",
    ProviderType.fireworks_ai: "https://api.fireworks.ai/inference/v1",
    ProviderType.deepseek: "https://api.deepseek.com/v1",
    ProviderType.perplexity: "https://api.perplexity.ai",
    ProviderType.replicate: "https://api.replicate.com/v1",
    ProviderType.elevenlabs: "https://api.elevenlabs.io/v1",
    ProviderType.runway: "https://api.runwayml.com/v1",
    ProviderType.suno: "https://api.suno.ai/v1",
    ProviderType.deepgram: "https://api.deepgram.com/v1",
    ProviderType.cartesia: "https://api.cartesia.ai",
    ProviderType.fal_ai: "https://fal.run",
    ProviderType.ollama: "http://localhost:11434",
}


@dataclass(frozen=True)
class ProviderSpec:
    """UI + behaviour metadata for a provider type."""

    type: ProviderType
    label: str
    tier: int  # 1=Native, 2=Aggregator, 3=Multimedia, 4=Self-hosted
    fields: list[str] = field(default_factory=list)  # form fields it needs
    base_url_locked: bool = False  # if True, UI hides base URL input
    default_base_url: str | None = None
    description: str = ""


PROVIDER_SPECS: list[ProviderSpec] = [
    ProviderSpec(ProviderType.anthropic, "Anthropic", 1,
                 ["api_key"], description="Claude Opus/Sonnet/Haiku"),
    ProviderSpec(ProviderType.openai, "OpenAI", 1,
                 ["api_key", "org_id"], description="GPT, embeddings, image gen, TTS, Whisper"),
    ProviderSpec(ProviderType.google_gemini, "Google Gemini", 1,
                 ["api_key"], description="Gemini 2.x, Imagen, text-embedding-005"),
    ProviderSpec(ProviderType.google_vertex_ai, "Google Vertex AI", 1,
                 ["project_id", "region", "service_account_json"], description="Gemini on GCP"),
    ProviderSpec(ProviderType.azure_openai, "Azure OpenAI", 1,
                 ["base_url", "api_key", "api_version"], description="OpenAI models on Azure"),
    ProviderSpec(ProviderType.aws_bedrock, "AWS Bedrock", 1,
                 ["region", "access_key_id", "secret_access_key", "use_iam_role"],
                 description="Claude/Llama/Mistral/Titan on AWS"),
    ProviderSpec(ProviderType.mistral, "Mistral", 1,
                 ["api_key"], base_url_locked=True,
                 default_base_url=BASE_URLS[ProviderType.mistral]),
    ProviderSpec(ProviderType.cohere, "Cohere", 1, ["api_key"]),
    ProviderSpec(ProviderType.voyage_ai, "Voyage AI", 1, ["api_key"]),
    ProviderSpec(ProviderType.huggingface, "HuggingFace", 1,
                 ["api_key"], base_url_locked=True,
                 default_base_url=BASE_URLS[ProviderType.huggingface]),
    ProviderSpec(ProviderType.openrouter, "OpenRouter", 2,
                 ["api_key"], base_url_locked=True,
                 default_base_url=BASE_URLS[ProviderType.openrouter]),
    ProviderSpec(ProviderType.groq, "Groq", 2,
                 ["api_key"], base_url_locked=True,
                 default_base_url=BASE_URLS[ProviderType.groq]),
    ProviderSpec(ProviderType.together_ai, "Together AI", 2,
                 ["api_key"], base_url_locked=True,
                 default_base_url=BASE_URLS[ProviderType.together_ai]),
    ProviderSpec(ProviderType.fireworks_ai, "Fireworks AI", 2,
                 ["api_key"], base_url_locked=True,
                 default_base_url=BASE_URLS[ProviderType.fireworks_ai]),
    ProviderSpec(ProviderType.deepseek, "DeepSeek", 2,
                 ["api_key"], base_url_locked=True,
                 default_base_url=BASE_URLS[ProviderType.deepseek]),
    ProviderSpec(ProviderType.perplexity, "Perplexity", 2,
                 ["api_key"], base_url_locked=True,
                 default_base_url=BASE_URLS[ProviderType.perplexity]),
    ProviderSpec(ProviderType.sambanova, "SambaNova", 2,
                 ["base_url", "api_key"]),
    ProviderSpec(ProviderType.replicate, "Replicate", 3,
                 ["api_key", "extra_model_ids"]),
    ProviderSpec(ProviderType.elevenlabs, "ElevenLabs", 3, ["api_key"]),
    ProviderSpec(ProviderType.runway, "Runway", 3, ["api_key"]),
    ProviderSpec(ProviderType.suno, "Suno", 3, ["api_key"]),
    ProviderSpec(ProviderType.deepgram, "Deepgram", 3, ["api_key"]),
    ProviderSpec(ProviderType.cartesia, "Cartesia", 3, ["api_key"]),
    ProviderSpec(ProviderType.fal_ai, "fal.ai", 3, ["api_key"]),
    ProviderSpec(ProviderType.ollama, "Ollama", 4,
                 ["base_url"], default_base_url=BASE_URLS[ProviderType.ollama]),
    ProviderSpec(ProviderType.openai_compatible, "OpenAI-compatible (generic)", 4,
                 ["base_url", "api_key", "api_version"],
                 description="Any vLLM / LM-Studio / custom OpenAI Chat server"),
]


def get_provider_spec(t: ProviderType) -> ProviderSpec:
    for s in PROVIDER_SPECS:
        if s.type == t:
            return s
    raise KeyError(t)


# Hardcoded known-model lists with pinned capabilities. Discovery (M3)
# uses these for providers without listable model endpoints.
KNOWN_MODELS: dict[ProviderType, list[dict]] = {
    ProviderType.anthropic: [
        {"model_id": "claude-opus-4-7", "display_name": "Claude Opus 4.7",
         "capabilities": [Capability.text.value, Capability.function_calling.value,
                          Capability.image_understanding.value, Capability.reasoning.value],
         "context_window": 200_000, "max_output_tokens": 8192},
        {"model_id": "claude-sonnet-4-6", "display_name": "Claude Sonnet 4.6",
         "capabilities": [Capability.text.value, Capability.function_calling.value,
                          Capability.image_understanding.value],
         "context_window": 200_000, "max_output_tokens": 8192},
        {"model_id": "claude-haiku-4-5", "display_name": "Claude Haiku 4.5",
         "capabilities": [Capability.text.value, Capability.function_calling.value,
                          Capability.image_understanding.value],
         "context_window": 200_000, "max_output_tokens": 8192},
    ],
    ProviderType.google_gemini: [
        {"model_id": "gemini-2.0-flash", "display_name": "Gemini 2.0 Flash",
         "capabilities": [Capability.text.value, Capability.image_understanding.value,
                          Capability.function_calling.value]},
        {"model_id": "gemini-2.0-pro", "display_name": "Gemini 2.0 Pro",
         "capabilities": [Capability.text.value, Capability.image_understanding.value,
                          Capability.function_calling.value, Capability.reasoning.value]},
        {"model_id": "imagen-3.0", "display_name": "Imagen 3",
         "capabilities": [Capability.image_generation.value]},
        {"model_id": "text-embedding-005", "display_name": "Text Embedding 005",
         "capabilities": [Capability.embedding.value]},
    ],
    ProviderType.cohere: [
        {"model_id": "command-a-03-2025", "display_name": "Command A",
         "capabilities": [Capability.text.value, Capability.function_calling.value]},
        {"model_id": "command-r-plus", "display_name": "Command R+",
         "capabilities": [Capability.text.value, Capability.function_calling.value]},
        {"model_id": "embed-v4.0", "display_name": "Embed v4",
         "capabilities": [Capability.embedding.value, Capability.multimodal_embedding.value]},
        {"model_id": "rerank-v3.5", "display_name": "Rerank v3.5",
         "capabilities": [Capability.reranking.value]},
    ],
    ProviderType.voyage_ai: [
        {"model_id": "voyage-4-large", "display_name": "Voyage 4 Large",
         "capabilities": [Capability.embedding.value]},
        {"model_id": "voyage-4", "display_name": "Voyage 4",
         "capabilities": [Capability.embedding.value]},
        {"model_id": "voyage-4-lite", "display_name": "Voyage 4 Lite",
         "capabilities": [Capability.embedding.value]},
        {"model_id": "voyage-multimodal-3", "display_name": "Voyage Multimodal 3",
         "capabilities": [Capability.embedding.value, Capability.multimodal_embedding.value]},
        {"model_id": "rerank-2", "display_name": "Rerank 2",
         "capabilities": [Capability.reranking.value]},
    ],
    ProviderType.elevenlabs: [
        {"model_id": "eleven_multilingual_v2", "display_name": "Multilingual v2",
         "capabilities": [Capability.text_to_speech.value]},
        {"model_id": "eleven_flash_v2_5", "display_name": "Flash v2.5",
         "capabilities": [Capability.text_to_speech.value]},
        {"model_id": "scribe_v1", "display_name": "Scribe v1",
         "capabilities": [Capability.audio_transcription.value]},
    ],
    ProviderType.runway: [
        {"model_id": "gen3a_turbo", "display_name": "Gen-3 Alpha Turbo",
         "capabilities": [Capability.text_to_video.value]},
        {"model_id": "gen4_turbo", "display_name": "Gen-4 Turbo",
         "capabilities": [Capability.text_to_video.value]},
    ],
    ProviderType.suno: [
        {"model_id": "chirp-v4", "display_name": "Chirp v4",
         "capabilities": [Capability.text_to_music.value]},
    ],
    ProviderType.deepgram: [
        {"model_id": "nova-3", "display_name": "Nova 3",
         "capabilities": [Capability.audio_transcription.value]},
    ],
    ProviderType.cartesia: [
        {"model_id": "sonic-2", "display_name": "Sonic 2",
         "capabilities": [Capability.text_to_speech.value]},
    ],
    ProviderType.fal_ai: [
        {"model_id": "fal-ai/flux-pro", "display_name": "Flux Pro",
         "capabilities": [Capability.image_generation.value]},
        {"model_id": "fal-ai/kling-video", "display_name": "Kling Video",
         "capabilities": [Capability.text_to_video.value]},
    ],
    ProviderType.replicate: [
        {"model_id": "black-forest-labs/flux-schnell",
         "display_name": "Flux Schnell",
         "capabilities": [Capability.image_generation.value]},
        {"model_id": "openai/whisper", "display_name": "Whisper (Replicate)",
         "capabilities": [Capability.audio_transcription.value]},
        {"model_id": "meta/musicgen", "display_name": "MusicGen",
         "capabilities": [Capability.text_to_music.value]},
    ],
    ProviderType.aws_bedrock: [
        {"model_id": "anthropic.claude-3-5-sonnet-20241022-v2:0",
         "display_name": "Claude 3.5 Sonnet (Bedrock)",
         "capabilities": [Capability.text.value, Capability.function_calling.value,
                          Capability.image_understanding.value]},
        {"model_id": "meta.llama3-70b-instruct-v1:0",
         "display_name": "Llama 3 70B",
         "capabilities": [Capability.text.value, Capability.function_calling.value]},
        {"model_id": "amazon.titan-embed-text-v2:0",
         "display_name": "Titan Embed",
         "capabilities": [Capability.embedding.value]},
    ],
}


def capabilities_for_model_id(model_id: str) -> list[str]:
    """Heuristic capability tagger for OpenAI-compatible model IDs (M4).

    Applied when no richer metadata is available. Pattern → capabilities
    assigned. Operator can manually override; manual edits survive
    re-sync via the `capabilities_locked` flag.
    """
    mid = model_id.lower()
    caps: list[str] = []

    def has(*patterns: str) -> bool:
        return any(p in mid for p in patterns)

    if has("embed", "e5", "bge", "nomic", "minilm", "sentence"):
        caps.append(Capability.embedding.value)
        return caps
    if has("rerank"):
        caps.append(Capability.reranking.value)
        return caps
    if has("dall-e", "dalle", "image-gen", "flux", "sdxl",
           "stable-diffusion", "playground"):
        caps.append(Capability.image_generation.value)
        return caps
    if has("whisper", "stt", "transcrib", "asr"):
        caps.append(Capability.audio_transcription.value)
        return caps
    if has("tts", "voice", "eleven", "cartesia", "voxtral"):
        caps.append(Capability.text_to_speech.value)
        return caps
    if has("video", "runway", "wan", "kling", "mochi", "cogvideo"):
        caps.append(Capability.text_to_video.value)
        return caps
    if has("music", "suno", "musicgen", "udio"):
        caps.append(Capability.text_to_music.value)
        return caps
    if has("vision", "4o", "llava", "minicpm", "pixtral", "gemini",
           "qwen-vl", "internvl"):
        caps.extend([Capability.image_understanding.value, Capability.text.value])
        return caps
    if has("sonar", "perplexity"):
        caps.extend([Capability.text.value, Capability.web_search.value])
        return caps
    if has("o1", "o3", "o4", "deepseek-r1", "qwq"):
        caps.extend([Capability.text.value, Capability.function_calling.value,
                     Capability.reasoning.value])
        return caps
    return [Capability.text.value, Capability.function_calling.value]
