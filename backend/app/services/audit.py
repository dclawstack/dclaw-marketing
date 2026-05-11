"""Audit service — single entry point for emitting AuditEvent rows.

Use this from routes and from Celery tasks. Avoid creating AuditEvent
instances by hand elsewhere — going through this helper makes it
possible to add side effects later (real-time stream, anomaly alerts,
RLHF dataset capture) in one place.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_event import AuditActorKind, AuditEvent, AuditResult


async def write_audit_event(
    session: AsyncSession,
    *,
    action_type: str,
    organization_id: UUID | None = None,
    actor_kind: AuditActorKind = AuditActorKind.user,
    actor_user_id: UUID | None = None,
    actor_agent: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    payload: dict[str, Any] | None = None,
    result: AuditResult = AuditResult.success,
    error_message: str | None = None,
    approval_request_id: UUID | None = None,
    request: Request | None = None,
) -> AuditEvent:
    """Write one immutable AuditEvent and return it.

    Caller is responsible for `await session.commit()` — the helper
    only adds + flushes so it composes inside a larger transaction.
    """
    ip = None
    ua = None
    if request is not None:
        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent")

    event = AuditEvent(
        organization_id=organization_id,
        actor_kind=actor_kind,
        actor_user_id=actor_user_id,
        actor_agent=actor_agent,
        action_type=action_type,
        target_type=target_type,
        target_id=target_id,
        payload_json=payload,
        result=result,
        error_message=error_message,
        ip_address=ip,
        user_agent=ua,
        approval_request_id=approval_request_id,
    )
    session.add(event)
    await session.flush()
    return event


__all__ = ["write_audit_event"]
