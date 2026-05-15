"""Research tools — live web search + URL fetch (S5-CDR-E).

`web_search` and `fetch_url` give the Conductor real-world awareness for
marketing context (competitor moves, trending topics, fresh keyword
data). When no provider key is configured, both tools return
deterministic stubs so dev/CI work offline.

Provider order for web_search:
  1. Tavily (TAVILY_API_KEY) — preferred, optimized for LLM RAG
  2. Brave Search (BRAVE_SEARCH_API_KEY) — fallback
  3. Stub — zero results + a clear "no provider configured" hint
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.agents.tools.registry import ToolContext, tool
from app.core.config import settings


logger = logging.getLogger(__name__)


async def _tavily_search(query: str, num_results: int) -> list[dict] | None:
    if not settings.tavily_api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": settings.tavily_api_key,
                    "query": query,
                    "max_results": num_results,
                    "search_depth": "basic",
                    "include_answer": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results") or []
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("content", "")[:600],
                    "score": float(r.get("score") or 0.0),
                    "provider": "tavily",
                }
                for r in results
            ]
    except Exception:
        logger.exception("Tavily search failed")
        return None


async def _brave_search(query: str, num_results: int) -> list[dict] | None:
    if not settings.brave_search_api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": num_results},
                headers={
                    "X-Subscription-Token": settings.brave_search_api_key,
                    "Accept": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()
            web_results = (data.get("web") or {}).get("results") or []
            return [
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": (r.get("description") or "")[:600],
                    "score": 0.0,
                    "provider": "brave",
                }
                for r in web_results
            ]
    except Exception:
        logger.exception("Brave search failed")
        return None


@tool(
    name="web_search",
    description=(
        "Search the live web for fresh information. Use for competitor "
        "intel, news, trending topics, anything the user expects to be "
        "up-to-date. Results are best-effort and include source URLs the "
        "final answer should cite. Cap `num_results` at 10."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "minLength": 2},
            "num_results": {"type": "integer", "minimum": 1, "maximum": 10, "default": 5},
        },
        "required": ["query"],
    },
    category="research",
)
async def web_search(ctx: ToolContext, *, query: str, num_results: int = 5) -> dict:
    num_results = max(1, min(10, int(num_results)))
    for provider in (_tavily_search, _brave_search):
        results = await provider(query, num_results)
        if results is not None:
            return {
                "ok": True,
                "query": query,
                "count": len(results),
                "results": results,
            }
    return {
        "ok": True,
        "query": query,
        "count": 0,
        "results": [],
        "note": (
            "No search provider configured (set TAVILY_API_KEY or "
            "BRAVE_SEARCH_API_KEY). Returning empty result set."
        ),
    }


@tool(
    name="fetch_url",
    description=(
        "Fetch a URL and return its main text content. Use after "
        "web_search to read the most promising result(s) in full. "
        "Truncates to 8 kB of extracted text."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "url": {"type": "string", "format": "uri"},
        },
        "required": ["url"],
    },
    category="research",
)
async def fetch_url(ctx: ToolContext, *, url: str) -> dict:
    if not (url.startswith("http://") or url.startswith("https://")):
        return {"ok": False, "error": "url must be http(s)"}
    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers={
                "User-Agent": "DClawConductor/1.0 (+marketing-platform)",
            },
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            text = resp.text
    except httpx.HTTPError as e:
        return {"ok": False, "error": str(e)}

    # Cheap HTML→text: strip tags + collapse whitespace. For richer
    # extraction we'd reach for trafilatura/readability; this is good
    # enough for citation snippets.
    import re
    if "html" in content_type.lower() or text.lstrip().startswith("<"):
        text = re.sub(r"<script[\s\S]*?</script>", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

    return {
        "ok": True,
        "url": url,
        "content_type": content_type,
        "text": text[:8_000],
        "truncated": len(text) > 8_000,
    }


def _research_provider_status() -> dict[str, Any]:
    """Surface configured-or-not state for the model-settings panel.

    Not registered as a tool — used by the API layer to tell the
    frontend which provider is live so the research-mode toggle can
    show a hint when the user picks Light/Deep without a provider
    configured.
    """
    return {
        "tavily": bool(settings.tavily_api_key),
        "brave": bool(settings.brave_search_api_key),
    }
