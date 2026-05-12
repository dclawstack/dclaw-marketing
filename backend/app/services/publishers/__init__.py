"""Per-channel publishers (Phase 5).

Each publisher knows how to:
1. Authenticate to its platform (using credentials stored on the
   SocialAccount row),
2. Publish a single post (text + asset URLs), and
3. Return a normalised ``PublishResult`` the worker can persist.

The Celery worker dispatches to the right publisher based on
``ScheduledPost.channel``. Publishers run in the SYNC worker context,
so they use ``httpx.Client`` not ``AsyncClient``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PublishResult:
    provider: str
    """Identifier of the platform that handled the publish."""

    remote_id: str
    """Platform-specific id of the new post (URI, post id, etc.)."""

    permalink: str | None
    """Public URL where the post is viewable, if available."""

    raw: dict
    """Full provider response, JSON-safe."""


__all__ = ["PublishResult"]
