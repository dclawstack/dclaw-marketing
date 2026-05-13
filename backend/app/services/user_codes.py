"""Allocator for User.display_code (6-character lowercase hex).

Bootstrap admin is always `000000`. New users get the next sequential
value computed at insert time: max(existing) + 1, padded to 6 hex.

Race condition: two concurrent inserts could compute the same code.
Caller should be prepared to retry once on UniqueViolationError; the
unique constraint on the column is the safety net.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def next_display_code(session: AsyncSession) -> str:
    """Compute the next free 6-hex code based on the current max."""
    rows = (
        await session.execute(select(User.display_code))
    ).scalars().all()
    max_int = 0
    for code in rows:
        if not code:
            continue
        try:
            v = int(code, 16)
        except ValueError:
            continue
        if v > max_int:
            max_int = v
    return f"{max_int + 1:06x}"


__all__ = ["next_display_code"]
