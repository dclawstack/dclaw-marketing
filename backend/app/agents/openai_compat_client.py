"""OpenAI-compatible escape hatch for the Conductor agent (#369).

Lets operators without an Anthropic key drive the Conductor against any
OpenAI-shape `/v1/chat/completions` server — Ollama, Groq, Gemini's
OpenAI-compat shim, OpenRouter, Together, Fireworks, vLLM, LM Studio,
etc.

Three entry points, mirroring `anthropic_client.py`:

  - `complete(system, user, …)` → str
  - `messages_create_raw(system, messages, tools, …)` → dict in the
    same normalized shape `anthropic_client.messages_create_raw` returns
  - `messages_stream_raw(system, messages, tools, …)` → async generator
    yielding the same normalized event types

This module is intentionally pure-httpx (no openai SDK) so we don't add
a heavy dep just for a fallback path.
"""

from __future__ import annotations

import json
import logging
from typing import AsyncIterator

import httpx

from app.core.config import settings


logger = logging.getLogger(__name__)


def is_openai_compat_configured() -> bool:
    return bool(settings.openai_compat_base_url and settings.openai_compat_model)


def _base() -> str:
    return settings.openai_compat_base_url.rstrip("/")


def _model() -> str:
    return settings.openai_compat_model


def _headers() -> dict[str, str]:
    h = {"Content-Type": "application/json", "Accept": "application/json"}
    if settings.openai_compat_api_key:
        h["Authorization"] = f"Bearer {settings.openai_compat_api_key}"
    return h


def _build_messages(
    system: str,
    user_messages: list[dict],
) -> list[dict]:
    """Compose the OpenAI `messages` array. Anthropic uses a separate
    `system` field; OpenAI expects it as the first message in the
    conversation."""
    out = [{"role": "system", "content": system}] if system else []
    for m in user_messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        # If content is a list (vision blocks), flatten to text for
        # providers that don't support multimodal. Vision support on
        # OpenAI-compat is provider-specific; we keep this minimal.
        if isinstance(content, list):
            text_parts = []
            for blk in content:
                if isinstance(blk, dict) and blk.get("type") == "text":
                    text_parts.append(blk.get("text", ""))
            content = "\n".join(text_parts)
        out.append({"role": role, "content": content})
    return out


async def complete(
    *,
    system: str,
    user: str,
    max_tokens: int = 2000,
    model: str | None = None,
    n_variants_hint: int = 3,
    images: list[tuple[str, bytes]] | None = None,  # ignored on this path
) -> str:
    """Non-streaming text completion via OpenAI-shape /v1/chat/completions."""
    payload = {
        "model": model or _model(),
        "messages": _build_messages(system, [{"role": "user", "content": user}]),
        "max_tokens": max_tokens,
    }
    async with httpx.AsyncClient(timeout=300.0) as client:
        r = await client.post(
            f"{_base()}/v1/chat/completions",
            headers=_headers(),
            json=payload,
        )
        r.raise_for_status()
        data = r.json()
    choices = data.get("choices") or []
    if not choices:
        return ""
    msg = choices[0].get("message") or {}
    return msg.get("content") or ""


async def messages_create_raw(
    *,
    system: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    max_tokens: int = 2000,
    model: str | None = None,
) -> dict:
    """Non-streaming structured response, mirroring the shape
    `anthropic_client.messages_create_raw` returns:

        {"stop_reason": "tool_use" | "end_turn" | …,
         "content": [{"type": "text"|"tool_use", ...}, …]}
    """
    payload: dict = {
        "model": model or _model(),
        "messages": _build_messages(system, messages),
        "max_tokens": max_tokens,
    }
    if tools:
        payload["tools"] = [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema") or {"type": "object", "properties": {}},
                },
            }
            for t in tools
        ]

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            r = await client.post(
                f"{_base()}/v1/chat/completions",
                headers=_headers(),
                json=payload,
            )
            r.raise_for_status()
            data = r.json()
    except Exception as e:  # pragma: no cover — network/SDK hiccup
        logger.exception("OpenAI-compat messages_create_raw failed")
        return {
            "stop_reason": "end_turn",
            "content": [{"type": "text", "text": f"(provider error: {e})"}],
        }

    choices = data.get("choices") or []
    if not choices:
        return {"stop_reason": "end_turn", "content": []}
    choice = choices[0]
    msg = choice.get("message") or {}
    finish_reason = choice.get("finish_reason") or "stop"
    out_blocks: list[dict] = []

    text = msg.get("content")
    if text:
        out_blocks.append({"type": "text", "text": text})

    # OpenAI tool calls are nested under message.tool_calls[].function
    for tc in msg.get("tool_calls") or []:
        fn = tc.get("function") or {}
        args_raw = fn.get("arguments")
        try:
            args = json.loads(args_raw) if isinstance(args_raw, str) else (args_raw or {})
        except json.JSONDecodeError:
            args = {}
        out_blocks.append(
            {
                "type": "tool_use",
                "id": tc.get("id", ""),
                "name": fn.get("name", ""),
                "input": args,
            }
        )

    stop_reason = "tool_use" if finish_reason == "tool_calls" else "end_turn"
    return {"stop_reason": stop_reason, "content": out_blocks}


async def messages_stream_raw(
    *,
    system: str,
    messages: list[dict],
    tools: list[dict] | None = None,
    max_tokens: int = 2000,
    model: str | None = None,
    thinking_budget_tokens: int | None = None,  # ignored on this path
) -> AsyncIterator[dict]:
    """Streaming variant — yields the same event types as
    `anthropic_client.messages_stream_raw`: text_delta, tool_use_start,
    tool_use_input, tool_use_done, message_done, error."""
    payload: dict = {
        "model": model or _model(),
        "messages": _build_messages(system, messages),
        "max_tokens": max_tokens,
        "stream": True,
    }
    if tools:
        payload["tools"] = [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema") or {"type": "object", "properties": {}},
                },
            }
            for t in tools
        ]

    # Track partial tool-call accumulations across delta events.
    pending: dict[int, dict] = {}  # index → {"id", "name", "input_json"}

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream(
                "POST",
                f"{_base()}/v1/chat/completions",
                headers=_headers(),
                json=payload,
            ) as resp:
                resp.raise_for_status()
                stop_reason = "end_turn"
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    raw = line[len("data:") :].strip()
                    if raw == "[DONE]":
                        break
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    choices = data.get("choices") or []
                    if not choices:
                        continue
                    choice = choices[0]
                    delta = choice.get("delta") or {}
                    finish_reason = choice.get("finish_reason")

                    text_piece = delta.get("content")
                    if text_piece:
                        yield {"type": "text_delta", "text": text_piece}

                    for tc in delta.get("tool_calls") or []:
                        idx = tc.get("index", 0)
                        fn = tc.get("function") or {}
                        if idx not in pending:
                            pending[idx] = {
                                "id": tc.get("id", ""),
                                "name": fn.get("name", ""),
                                "input_json": "",
                            }
                            yield {
                                "type": "tool_use_start",
                                "id": pending[idx]["id"],
                                "name": pending[idx]["name"],
                            }
                        else:
                            # Subsequent deltas may carry additional name chars
                            if fn.get("name"):
                                pending[idx]["name"] += fn["name"]
                            if tc.get("id") and not pending[idx]["id"]:
                                pending[idx]["id"] = tc["id"]
                        partial = fn.get("arguments")
                        if partial:
                            pending[idx]["input_json"] += partial
                            yield {
                                "type": "tool_use_input",
                                "id": pending[idx]["id"],
                                "partial_json": partial,
                            }

                    if finish_reason:
                        stop_reason = (
                            "tool_use" if finish_reason == "tool_calls" else "end_turn"
                        )

                # Flush completed tool_uses
                for p in pending.values():
                    try:
                        parsed = json.loads(p["input_json"]) if p["input_json"] else {}
                    except json.JSONDecodeError:
                        parsed = {}
                    yield {
                        "type": "tool_use_done",
                        "id": p["id"],
                        "name": p["name"],
                        "input": parsed,
                    }
                yield {"type": "message_done", "stop_reason": stop_reason}
    except Exception as e:  # pragma: no cover — network/SDK hiccup
        logger.exception("OpenAI-compat stream failed")
        yield {"type": "error", "error": str(e)}
        yield {"type": "message_done", "stop_reason": "error"}


__all__ = [
    "complete",
    "messages_create_raw",
    "messages_stream_raw",
    "is_openai_compat_configured",
]
