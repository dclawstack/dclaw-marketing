"""Agent runtime — resolver-aware LLM dispatch (S4-A1).

This module is the new home of "call Claude (or whatever the resolver
picks) for the (org, user) at hand". The legacy `anthropic_client.complete`
remains for paths that haven't been migrated yet, but new code should
import from here so it picks up the resolver chain
(user → org → pool → env → stub) automatically.

`run_completion()` returns the assistant's text — that's it. Streaming
support arrives in S4-C3 when the Conductor full-screen page lands.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.anthropic_client import _stub_response
from app.models.model_call_log import ModelCallStatus
from app.models.model_registry import Capability, ProviderType
from app.services import model_resolver as resolver_svc
from app.services.model_call_logger import fire_and_forget, log_call

log = logging.getLogger(__name__)


async def run_completion(
    *,
    db: AsyncSession,
    org_id: UUID | None,
    user_id: UUID | None,
    caller_component: str,
    system: str,
    user: str,
    max_tokens: int = 2000,
    capability: Capability = Capability.text,
    n_variants_hint: int = 3,
) -> dict[str, Any]:
    """Run a single LLM completion through the resolver chain.

    Returns:
        {"text": str, "model_id": str|None, "provider_type": str|None,
         "resolved_by": str}
    """
    resolved = await resolver_svc.resolve(
        db, user_id=user_id, org_id=org_id, capability=capability
    )

    if resolved.resolved_by == "stub":
        text = _stub_response(system, user, n_variants_hint)
        return {
            "text": text,
            "model_id": None,
            "provider_type": None,
            "resolved_by": "stub",
        }

    started = time.monotonic()
    text: str = ""
    status = ModelCallStatus.success
    err: str | None = None
    input_tokens = output_tokens = 0

    try:
        if resolved.provider_type in (
            ProviderType.anthropic,
            None,
        ):
            from anthropic import AsyncAnthropic

            client = AsyncAnthropic(api_key=resolved.api_key)
            response = await client.messages.create(
                model=resolved.model_id or "claude-sonnet-4-6",
                system=system,
                messages=[{"role": "user", "content": user}],
                max_tokens=max_tokens,
            )
            parts: list[str] = []
            for block in response.content:
                t = getattr(block, "text", None)
                if t:
                    parts.append(t)
            text = "\n".join(parts)
            input_tokens = getattr(response.usage, "input_tokens", 0) or 0
            output_tokens = getattr(response.usage, "output_tokens", 0) or 0
        else:
            # OpenAI-compatible Chat Completions path covers OpenAI,
            # Groq, Together, Fireworks, DeepSeek, Perplexity, SambaNova,
            # HuggingFace, OpenRouter, Mistral, openai_compatible.
            import httpx

            base = resolved.base_url or ""
            headers = {
                "Authorization": f"Bearer {resolved.api_key}",
                "Content-Type": "application/json",
            }
            if resolved.provider_type == ProviderType.openrouter:
                headers["HTTP-Referer"] = "https://dclaw.io"
                headers["X-Title"] = "DClaw"
            payload = {
                "model": resolved.model_id,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "max_tokens": max_tokens,
            }
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(
                    f"{base.rstrip('/')}/chat/completions",
                    headers=headers,
                    json=payload,
                )
            if r.status_code != 200:
                raise RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
            data = r.json()
            text = (
                data["choices"][0]["message"]["content"]
                if data.get("choices")
                else ""
            )
            usage = data.get("usage", {}) or {}
            input_tokens = usage.get("prompt_tokens", 0) or 0
            output_tokens = usage.get("completion_tokens", 0) or 0
    except Exception as e:  # noqa: BLE001
        log.exception("model completion failed")
        status = ModelCallStatus.error
        err = str(e)[:500]
        text = _stub_response(system, user, n_variants_hint)
    finally:
        duration_ms = int((time.monotonic() - started) * 1000)
        if resolved.model_entry_id is not None:
            fire_and_forget(
                log_call(
                    db,
                    model_entry_id=resolved.model_entry_id,
                    organization_id=org_id,
                    caller_component=caller_component,
                    duration_ms=duration_ms,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=0.0,
                    status=status,
                    error_message=err,
                )
            )

    return {
        "text": text,
        "model_id": resolved.model_id,
        "provider_type": resolved.provider_type.value if resolved.provider_type else None,
        "resolved_by": resolved.resolved_by,
    }


# ---------- Conductor decomposition (S4-A2) --------------------------------


CONDUCTOR_DECOMPOSE_PROMPT = """
You are the Conductor agent for DClaw, a marketing automation platform.

A user brief came in. Decompose it into a list of sub-tasks, each
labelled with the role-Agent that should handle it.

Role-Agents available:
  creatives   — text/image/voice/video drafting
  smm         — social calendar + post scheduling
  seo         — keyword, content brief, AEO optimisation
  paid_media  — ad campaigns, budgets, audiences
  analyst     — reporting, anomalies, weekly digest
  inbox       — replies + DMs + comment triage
  reviewer    — final-pass compliance review

Respond ONLY with a JSON object:

  {"tasks": [
     {"agent": "creatives", "intent": "<short verb phrase>", "input": "<sub-brief>"},
     ...
   ],
   "rationale": "<1-2 sentence summary of the plan>"}

3-7 tasks max. Order matters — list dependencies first.
""".strip()


async def decompose_brief(
    *,
    db: AsyncSession,
    org_id: UUID | None,
    user_id: UUID | None,
    brief: str,
) -> dict[str, Any]:
    """Conductor → role-agent dispatch plan (S4-A2)."""
    import json

    res = await run_completion(
        db=db,
        org_id=org_id,
        user_id=user_id,
        caller_component="conductor",
        system=CONDUCTOR_DECOMPOSE_PROMPT,
        user=brief,
        max_tokens=1200,
    )
    text = res["text"].strip()
    # Tolerate code-fence wrap.
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].lstrip()
    try:
        parsed = json.loads(text)
    except Exception:  # noqa: BLE001
        parsed = {
            "tasks": [
                {"agent": "creatives", "intent": "draft content", "input": brief}
            ],
            "rationale": "Defaulted to creatives because Conductor returned non-JSON.",
        }
    return {
        "plan": parsed,
        "model_id": res.get("model_id"),
        "resolved_by": res.get("resolved_by"),
    }
