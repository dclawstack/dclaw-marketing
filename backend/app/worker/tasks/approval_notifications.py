"""Pending-approval pings to Slack / Discord — Phase 6 / §6.11.

Every 5 minutes, look at ApprovalRequest rows with status=pending that
have been waiting longer than the per-Org ``approval_ping_threshold_seconds``
(default 15 min) and haven't been pinged yet. For each, post a
notification to the Org's connected slack and/or discord channel via
the MCP adapters from #182-#184.

Marks each request as pinged via an AuditEvent so we never duplicate
notifications across runs.

Per-Org config in ``Organization.constraints_json``::

    {
      "approvals_notify": {
        "slack_channel": "#approvals",          // optional
        "discord_channel_id": "1234567890",      // optional
        "threshold_seconds": 900                  // default 15 min
      }
    }
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import engine
from app.models.approval_request import ApprovalRequest, ApprovalStatus
from app.models.audit_event import AuditActorKind, AuditEvent, AuditResult
from app.models.connection import Connection, ConnectionStatus
from app.models.organization import Organization
from app.worker.celery_app import celery_app


_PING_ACTION_TYPE = "approval.notified"
_DEFAULT_THRESHOLD_S = 900  # 15 min


async def _already_pinged(
    session: AsyncSession, request_id
) -> bool:
    row = await session.execute(
        select(AuditEvent.id).where(
            AuditEvent.action_type == _PING_ACTION_TYPE,
            AuditEvent.target_id == str(request_id),
        )
    )
    return row.scalar_one_or_none() is not None


async def _post_slack(
    session: AsyncSession,
    *,
    organization_id,
    channel: str,
    summary: str,
    request_id,
) -> None:
    """Best-effort — caller swallows errors."""
    from app.services.mcp import slack as slack_mcp

    await slack_mcp.post_message(
        session,
        organization_id=organization_id,
        channel=channel,
        text=(
            f":warning: Approval pending — {summary[:200]}\n"
            f"id: {request_id}"
        ),
    )


async def _post_discord(
    session: AsyncSession,
    *,
    organization_id,
    channel_id: str,
    summary: str,
    request_id,
) -> None:
    from app.services.mcp import discord as discord_mcp

    await discord_mcp.post_message(
        session,
        organization_id=organization_id,
        channel_id=channel_id,
        content=(
            f"⚠️ Approval pending — {summary[:200]}\nid: {request_id}"
        ),
    )


async def _has_connection(
    session: AsyncSession, organization_id, server_id: str
) -> bool:
    r = await session.execute(
        select(Connection.id).where(
            Connection.organization_id == organization_id,
            Connection.server_id == server_id,
            Connection.status == ConnectionStatus.active,
        )
    )
    return r.scalar_one_or_none() is not None


async def _run() -> dict:
    now = datetime.now(tz=timezone.utc)
    counts = {"pinged_slack": 0, "pinged_discord": 0, "scanned": 0}
    async with AsyncSession(engine, expire_on_commit=False) as session:
        orgs = (
            await session.execute(select(Organization))
        ).scalars().all()
        for org in orgs:
            cfg = (org.constraints_json or {}).get("approvals_notify") or {}
            threshold = int(
                cfg.get("threshold_seconds", _DEFAULT_THRESHOLD_S)
            )
            cutoff = now - timedelta(seconds=threshold)
            pending = (
                await session.execute(
                    select(ApprovalRequest).where(
                        ApprovalRequest.organization_id == org.id,
                        ApprovalRequest.status == ApprovalStatus.pending,
                        ApprovalRequest.created_at <= cutoff,
                    )
                )
            ).scalars().all()
            for req in pending:
                counts["scanned"] += 1
                if await _already_pinged(session, req.id):
                    continue
                summary = (
                    req.summary
                    or f"{req.action_type} on {req.target_type or '?'}"
                )

                slack_channel = cfg.get("slack_channel")
                discord_channel = cfg.get("discord_channel_id")
                pinged_this_one = False

                if slack_channel and await _has_connection(
                    session, org.id, "slack"
                ):
                    try:
                        await _post_slack(
                            session,
                            organization_id=org.id,
                            channel=slack_channel,
                            summary=summary,
                            request_id=req.id,
                        )
                        counts["pinged_slack"] += 1
                        pinged_this_one = True
                    except Exception:  # pragma: no cover — best-effort
                        pass

                if discord_channel and await _has_connection(
                    session, org.id, "discord"
                ):
                    try:
                        await _post_discord(
                            session,
                            organization_id=org.id,
                            channel_id=discord_channel,
                            summary=summary,
                            request_id=req.id,
                        )
                        counts["pinged_discord"] += 1
                        pinged_this_one = True
                    except Exception:  # pragma: no cover
                        pass

                if pinged_this_one:
                    session.add(
                        AuditEvent(
                            organization_id=org.id,
                            actor_kind=AuditActorKind.system,
                            action_type=_PING_ACTION_TYPE,
                            target_type="approval_request",
                            target_id=str(req.id),
                            payload_json={
                                "channels": [
                                    c
                                    for c, set_ in [
                                        ("slack", bool(slack_channel)),
                                        ("discord", bool(discord_channel)),
                                    ]
                                    if set_
                                ],
                            },
                            result=AuditResult.success,
                        )
                    )
        await session.commit()
    counts["at"] = now.isoformat()
    return counts


@celery_app.task(
    name="app.worker.tasks.approval_notifications.notify_pending_approvals"
)
def notify_pending_approvals() -> dict:
    return asyncio.run(_run())


__all__ = ["notify_pending_approvals"]
