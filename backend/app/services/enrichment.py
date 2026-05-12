"""E2 Lead enrichment fan-out (SP3-12).

Pluggable provider chain. Each provider is a small adapter that takes a
Lead's email/domain/linkedin and returns a partial profile. The merge
respects "first non-null wins" so the human-edited fields aren't
overwritten by a later provider.

Stub-friendly: when no API keys are configured, each provider returns a
deterministic stub so dev / CI still exercises the merge path.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from app.core.config import settings


@dataclass
class EnrichmentResult:
    provider: str
    data: dict[str, Any] = field(default_factory=dict)
    stub: bool = False
    error: str | None = None


# ---------- adapters ---------------------------------------------------------


async def _apollo(email: str) -> EnrichmentResult:
    """Apollo.io people-match. Stub when no key."""
    if not getattr(settings, "apollo_api_key", ""):
        h = hashlib.sha256(("apollo:" + email).encode()).hexdigest()[:8]
        return EnrichmentResult(
            provider="apollo",
            data={
                "title": f"Stub Title {h[:3]}",
                "company": f"Stub Co {h[3:6]}",
                "linkedin_url": f"https://linkedin.com/in/stub-{h}",
            },
            stub=True,
        )
    # Real call would go here; for v1 we keep the stub path canonical.
    return EnrichmentResult(provider="apollo", data={}, stub=True)


async def _clearbit(email: str) -> EnrichmentResult:
    if not getattr(settings, "clearbit_api_key", ""):
        h = hashlib.sha256(("clearbit:" + email).encode()).hexdigest()[:8]
        return EnrichmentResult(
            provider="clearbit",
            data={
                "company_domain": email.split("@", 1)[-1] if "@" in email else None,
                "industry": f"Stub Industry {h[:3]}",
                "employee_count": int(h, 16) % 5000 + 10,
            },
            stub=True,
        )
    return EnrichmentResult(provider="clearbit", data={}, stub=True)


async def _pdl(email: str) -> EnrichmentResult:
    if not getattr(settings, "pdl_api_key", ""):
        h = hashlib.sha256(("pdl:" + email).encode()).hexdigest()[:8]
        return EnrichmentResult(
            provider="pdl",
            data={
                "location_country": "US",
                "skills": ["marketing", "growth", "saas"][: (int(h[0], 16) % 3) + 1],
            },
            stub=True,
        )
    return EnrichmentResult(provider="pdl", data={}, stub=True)


PROVIDERS = (_apollo, _clearbit, _pdl)


# ---------- merger -----------------------------------------------------------


def _merge_first_wins(target: dict, src: dict) -> None:
    for k, v in src.items():
        if v is None:
            continue
        if k in target and target[k] not in (None, "", [], {}):
            continue
        target[k] = v


async def enrich_lead_email(email: str) -> dict[str, Any]:
    """Run the full provider chain on a single email. Returns a merged
    profile dict + a list of per-provider audit entries.

    Result shape:
      {
        "merged": {...},
        "audit": [{"provider": "apollo", "stub": True, "fields": [...]}, ...],
      }
    """
    merged: dict[str, Any] = {}
    audit: list[dict[str, Any]] = []
    for adapter in PROVIDERS:
        try:
            res = await adapter(email)
        except Exception as exc:  # pragma: no cover — defensive
            audit.append(
                {"provider": getattr(adapter, "__name__", "?"), "error": str(exc)}
            )
            continue
        if res.error:
            audit.append({"provider": res.provider, "error": res.error})
            continue
        keys_added = [k for k in res.data if k not in merged or merged[k] in (None, "")]
        _merge_first_wins(merged, res.data)
        audit.append(
            {
                "provider": res.provider,
                "stub": res.stub,
                "fields": keys_added,
            }
        )
    return {"merged": merged, "audit": audit}


__all__ = ["enrich_lead_email", "EnrichmentResult", "PROVIDERS"]
