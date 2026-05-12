"""Anthropic SDK wrapper.

Exposes a single coroutine `complete(system, user, max_tokens, model)`
that returns the assistant text. Falls back to a deterministic stub
when no API key is configured (so dev + CI work without external
creds and tests are repeatable).
"""

from __future__ import annotations

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
) -> str:
    """Return Claude's text completion for a single user turn.

    n_variants_hint is only used by the stub path to know how many
    variants to fabricate. Real Claude follows the user prompt's
    instructions.
    """
    if not is_real_provider_configured():
        return _stub_response(system, user, n_variants_hint)

    try:
        from anthropic import AsyncAnthropic
        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model=model,
            system=system,
            messages=[{"role": "user", "content": user}],
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


__all__ = ["complete", "is_real_provider_configured", "DEFAULT_MODEL"]
