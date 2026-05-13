"""Slug generator for User + Organization.

Format: `{prefix}-{first4(name)}-{random6hex}`.
- prefix: 'u' for user, 'o' for org, 's' for superadmin (reserved for bootstrap)
- name: lowercased, alpha-numeric only, first 4 chars; pad with '0' if shorter
- random6hex: 24-bit random, 6 lowercase hex chars

Caller retries on UniqueViolation. With 16M-keyspace per name-bucket
collisions are vanishingly rare but the unique index is the safety net.
"""

from __future__ import annotations

import re
import secrets
from typing import Literal

Prefix = Literal["u", "o", "s"]

_NON_ALNUM_RX = re.compile(r"[^a-z0-9]+")


def _first4(name: str | None) -> str:
    """Lowercase, strip non-alnum, take first 4 chars; pad with '0' if < 4."""
    if not name:
        return "user"
    cleaned = _NON_ALNUM_RX.sub("", name.lower())
    if not cleaned:
        return "user"
    if len(cleaned) >= 4:
        return cleaned[:4]
    return cleaned + "0" * (4 - len(cleaned))


def random_hex6() -> str:
    """6 lowercase hex chars (24-bit random)."""
    return secrets.token_hex(3)


def make_slug(prefix: Prefix, name: str | None) -> str:
    """One-shot slug build. Caller is responsible for uniqueness retries.

    Pass the user's full_name (or email local-part) for users; the org name
    for orgs. The bootstrap superadmin uses a hardcoded slug elsewhere
    (s-admn-000000) and does not go through this function.
    """
    return f"{prefix}-{_first4(name)}-{random_hex6()}"


__all__ = ["make_slug", "random_hex6", "Prefix"]
