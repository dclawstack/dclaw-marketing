"""Anthropic SDK wrapper.

Exposes a single coroutine `complete(system, user, max_tokens, model)`
that returns the assistant text. Falls back to a deterministic stub
when no API key is configured (so dev + CI work without external
creds and tests are repeatable). When the user passes `images=[(mime,
bytes)…]`, the wrapper builds proper Claude vision content blocks so
the Conductor can reason about attached images (S5-CDR-B).
"""

from __future__ import annotations

import base64
import hashlib
import logging

from app.core.config import settings


logger = logging.getLogger(__name__)

# Model routing per PLAN-v1.2 §v2.0 §A.5: Sonnet for role-Agents.
DEFAULT_MODEL = "claude-sonnet-4-6"


def is_real_provider_configured() -> bool:
    return bool(settings.anthropic_api_key)


def _stub_response(system: str, user: str, n_variants: int = 3) -> str:
    """Deterministic stub for CI/dev. Returns N synthetic variants
    keyed off a SHA-256 of system+user so the same input gives the
    same output across runs.
    """
    digest = hashlib.sha256((system + "\n--\n" + user).encode("utf-8")).hexdigest()[:8]
    lines = []
    for i in range(n_variants):
        lines.append(
            f"VARIANT {i + 1}: [stub generation {digest}-{i}] "
            f"This is a deterministic synthetic post for the brief — replace "
            f"by setting ANTHROPIC_API_KEY in the environment."
        )
    return "\n\n".join(lines)


async def complete(
    *,
    system: str,
    user: str,
    max_tokens: int = 2000,
    model: str = DEFAULT_MODEL,
    n_variants_hint: int = 3,
    images: list[tuple[str, bytes]] | None = None,
) -> str:
    """Return Claude's text completion for a single user turn.

    n_variants_hint is only used by the stub path to know how many
    variants to fabricate. Real Claude follows the user prompt's
    instructions. When `images` is provided, each `(mime_type, bytes)`
    pair becomes a Claude vision content block prepended to the user
    text — the stub path notes their count in the synthetic reply so
    tests can verify routing without burning credits.
    """
    if not is_real_provider_configured():
        if images:
            user = (
                f"[{len(images)} image attachment(s) — stub mode]\n\n"
                + user
            )
        return _stub_response(system, user, n_variants_hint)

    try:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=settings.anthropic_api_key)

        if images:
            content_blocks: list[dict] = []
            for mime, raw in images:
                # Claude vision supports JPEG/PNG/GIF/WebP via base64.
                content_blocks.append(
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": mime,
                            "data": base64.b64encode(raw).decode("ascii"),
                        },
                    }
                )
            content_blocks.append({"type": "text", "text": user})
            messages = [{"role": "user", "content": content_blocks}]
        else:
            messages = [{"role": "user", "content": user}]

        response = await client.messages.create(
            model=model,
            system=system,
            messages=messages,
            max_tokens=max_tokens,
        )
        # Flatten content blocks into plain text
        parts = []
        for block in response.content:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        return "\n".join(parts)
    except Exception:
        logger.exception("Anthropic call failed; falling back to stub.")
        return _stub_response(system, user, n_variants_hint)


async def messages_create_raw(
    *,
    system: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    max_tokens: int = 2000,
    model: str = DEFAULT_MODEL,
) -> dict:
    """Low-level wrapper around Anthropic `messages.create` that exposes
    the full structured response (content blocks + stop_reason).

    Returns a plain dict so callers don't need to import the SDK types:

        {
          "stop_reason": "tool_use" | "end_turn" | "max_tokens" | …,
          "content": [
            {"type": "text", "text": "…"},
            {"type": "tool_use", "id": "toolu_…", "name": "list_…", "input": {…}},
          ],
        }

    The stub fallback returns a simple end_turn text response so callers
    can still exercise the loop in dev/CI without an API key. (S5-CDR-C)
    """
    if not is_real_provider_configured():
        last_user_text = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                c = m.get("content")
                if isinstance(c, str):
                    last_user_text = c
                elif isinstance(c, list):
                    for blk in c:
                        if isinstance(blk, dict) and blk.get("type") == "text":
                            last_user_text = blk.get("text", "")
                            break
                break
        # Deterministic stub — same digest scheme as `complete()`.
        text = _stub_response(system, last_user_text, n_variants=1)
        return {
            "stop_reason": "end_turn",
            "content": [{"type": "text", "text": text}],
        }

    try:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        kwargs: dict = {
            "model": model,
            "system": system,
            "messages": messages,
            "max_tokens": max_tokens,
        }
        if tools:
            kwargs["tools"] = tools
        response = await client.messages.create(**kwargs)
        # Normalize content into plain dicts. Anthropic SDK returns
        # pydantic-style blocks — pull the fields we care about.
        out_blocks: list[dict] = []
        for block in response.content:
            btype = getattr(block, "type", None)
            if btype == "text":
                out_blocks.append({"type": "text", "text": getattr(block, "text", "")})
            elif btype == "tool_use":
                out_blocks.append(
                    {
                        "type": "tool_use",
                        "id": getattr(block, "id", ""),
                        "name": getattr(block, "name", ""),
                        "input": getattr(block, "input", {}) or {},
                    }
                )
            # Other block types (image / thinking — for S5-CDR-D) are
            # ignored here; the streaming path handles them separately.
        return {
            "stop_reason": getattr(response, "stop_reason", "end_turn") or "end_turn",
            "content": out_blocks,
        }
    except Exception:
        logger.exception("Anthropic messages_create_raw failed; using stub.")
        text = _stub_response(system, "", n_variants=1)
        return {
            "stop_reason": "end_turn",
            "content": [{"type": "text", "text": text}],
        }


__all__ = [
    "complete",
    "messages_create_raw",
    "is_real_provider_configured",
    "DEFAULT_MODEL",
]
