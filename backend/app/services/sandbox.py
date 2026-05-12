"""Sandbox / dry-run mode (Phase 11.5 — I2 in PLAN-v1.2).

When an Org's <code>constraints_json.sandbox_mode</code> flag is True,
every <em>outbound</em> action short-circuits to a stub:

  • Publishers (Bluesky / LinkedIn / X / Instagram / future channels)
    return a synthetic PublishResult marked <code>raw.sandbox=True</code>.
  • Email delivery (deliver_approved_email worker) skips the Resend
    call and stamps a synthetic <code>msg_sandbox_*</code> id.

Inbound and read-only paths are unaffected — agents still draft, the
Approval Inbox still works, generation endpoints still call the gen
providers (their output sits gated for review anyway).

We intentionally scope to outbound only. The goal is to make onboarding
demos and CI runs safe — no accidental public posts — without blocking
the dev experience of "see what the agent drafted".
"""

from __future__ import annotations

import hashlib
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.models.organization import Organization
from app.services.publishers import PublishResult


_FLAG = "sandbox_mode"


# ---------- read accessors -------------------------------------------


async def is_sandbox_mode(
    session: AsyncSession, organization_id: UUID
) -> bool:
    org = await session.get(Organization, organization_id)
    return _read_flag(org)


def is_sandbox_mode_sync(
    session: Session, organization_id: UUID
) -> bool:
    org = session.get(Organization, organization_id)
    return _read_flag(org)


def _read_flag(org: Organization | None) -> bool:
    if org is None or not isinstance(org.constraints_json, dict):
        return False
    return bool(org.constraints_json.get(_FLAG, False))


# ---------- write accessors -------------------------------------------


async def set_sandbox_mode(
    session: AsyncSession, organization_id: UUID, enabled: bool
) -> bool:
    """Flip the flag. Returns the new value, or raises if the org
    doesn't exist.
    """
    org = await session.get(Organization, organization_id)
    if org is None:
        raise LookupError(f"Organization {organization_id} not found")
    constraints = dict(org.constraints_json or {})
    constraints[_FLAG] = bool(enabled)
    org.constraints_json = constraints
    await session.flush()
    return bool(enabled)


# ---------- stub-result helpers --------------------------------------


def sandbox_publish_result(channel: str, text: str) -> PublishResult:
    """Used by the worker dispatcher to short-circuit a publish call
    when the Org is in sandbox mode.
    """
    digest = hashlib.sha256(
        (channel + "::" + text[:512]).encode("utf-8")
    ).hexdigest()[:18]
    return PublishResult(
        provider=channel,
        remote_id=f"sandbox-{digest}",
        permalink=None,
        raw={
            "stub": True,
            "sandbox": True,
            "channel": channel,
            "note": "Org is in sandbox / dry-run mode — no real call made.",
        },
    )


__all__ = [
    "is_sandbox_mode",
    "is_sandbox_mode_sync",
    "set_sandbox_mode",
    "sandbox_publish_result",
]
