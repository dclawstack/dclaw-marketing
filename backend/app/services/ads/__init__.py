"""Ads platform adapters (Phase 7.x).

Per-provider campaign-create primitives — the smallest useful surface
across Meta, Google, and LinkedIn. A full bidding/creative/audience
matrix lands later in the Ads UI work; this layer is the foundation
the Paid Media agent + the /ads UI sit on top of.

Each adapter returns an ``AdCreateResult``:

  provider     : str  — "meta" | "linkedin" | "google"
  external_id  : str  — provider's campaign id
  permalink    : str | None  — provider's manage-this-campaign URL
  raw          : dict — full provider response for audit
  stub         : bool — True when we short-circuited because the
                       provider has no token configured
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class AdCreateResult:
    provider: str
    external_id: str
    permalink: str | None
    raw: dict = field(default_factory=dict)
    stub: bool = False


__all__ = ["AdCreateResult"]
