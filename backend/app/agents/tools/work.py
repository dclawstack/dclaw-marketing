"""Work tools — inbox approvals and calendar scheduling."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select

from app.agents.tools.registry import ToolContext, tool
from app.models.approval_request import ApprovalRequest, ApprovalStatus
from app.models.scheduled_post import (
    ScheduledPost,
    ScheduledPostChannel,
    ScheduledPostStatus,
)


# ---------------- Inbox approvals --------------------------------------

@tool(
    name="list_inbox_items",
    description=(
        "List pending Approval Inbox items for this org. Use when the "
        "user asks what's waiting in the inbox / what needs approval. "
        "Returns at most 25 newest pending items."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["pending", "approved", "rejected", "auto_approved"],
                "default": "pending",
            },
            "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 25},
        },
    },
    category="work",
)
async def list_inbox_items(
    ctx: ToolContext,
    *,
    status: str = "pending",
    limit: int = 25,
) -> dict:
    try:
        status_enum = ApprovalStatus(status)
    except ValueError:
        return {"ok": False, "error": f"unknown status: {status}"}

    rows = (
        await ctx.session.execute(
            select(ApprovalRequest)
            .where(
                ApprovalRequest.organization_id == ctx.org_id,
                ApprovalRequest.status == status_enum,
            )
            .order_by(ApprovalRequest.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()

    return {
        "ok": True,
        "count": len(rows),
        "items": [
            {
                "id": str(r.id),
                "action_type": r.action_type,
                "status": r.status.value,
                "requested_by_agent": r.requested_by_agent,
                "created_at": r.created_at.isoformat(),
                "payload_preview": str(r.payload_json)[:200] if r.payload_json else None,
            }
            for r in rows
        ],
    }


@tool(
    name="approve_inbox_item",
    description=(
        "Mark a pending Approval Inbox item as approved. Side-effecty: "
        "this can unblock downstream actions (e.g. publishing). The "
        "Conductor itself only approves on direct, unambiguous user "
        "instructions referring to a specific item id."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "approval_request_id": {"type": "string", "description": "ApprovalRequest UUID"},
            "comment": {"type": "string"},
        },
        "required": ["approval_request_id"],
    },
    requires_approval=True,
    category="work",
)
async def approve_inbox_item(
    ctx: ToolContext,
    *,
    approval_request_id: str,
    comment: str = "",
) -> dict:
    try:
        rid = UUID(approval_request_id)
    except ValueError:
        return {"ok": False, "error": "approval_request_id is not a UUID"}
    row = (
        await ctx.session.execute(
            select(ApprovalRequest).where(
                ApprovalRequest.id == rid,
                ApprovalRequest.organization_id == ctx.org_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        return {"ok": False, "error": "approval request not found"}
    if row.status != ApprovalStatus.pending:
        return {"ok": False, "error": f"already {row.status.value}"}
    from datetime import datetime as _dt, timezone as _tz
    row.status = ApprovalStatus.approved
    row.decided_by_user_id = ctx.user_id
    row.decided_at = _dt.now(_tz.utc)
    if comment:
        row.decision_reason = comment
    await ctx.session.commit()
    return {"ok": True, "id": str(row.id), "status": row.status.value}


@tool(
    name="reject_inbox_item",
    description="Mark a pending Approval Inbox item as rejected with an optional reason.",
    input_schema={
        "type": "object",
        "properties": {
            "approval_request_id": {"type": "string"},
            "reason": {"type": "string"},
        },
        "required": ["approval_request_id"],
    },
    requires_approval=True,
    category="work",
)
async def reject_inbox_item(
    ctx: ToolContext,
    *,
    approval_request_id: str,
    reason: str = "",
) -> dict:
    try:
        rid = UUID(approval_request_id)
    except ValueError:
        return {"ok": False, "error": "approval_request_id is not a UUID"}
    row = (
        await ctx.session.execute(
            select(ApprovalRequest).where(
                ApprovalRequest.id == rid,
                ApprovalRequest.organization_id == ctx.org_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        return {"ok": False, "error": "approval request not found"}
    if row.status != ApprovalStatus.pending:
        return {"ok": False, "error": f"already {row.status.value}"}
    from datetime import datetime as _dt, timezone as _tz
    row.status = ApprovalStatus.rejected
    row.decided_by_user_id = ctx.user_id
    row.decided_at = _dt.now(_tz.utc)
    if reason:
        row.decision_reason = reason
    await ctx.session.commit()
    return {"ok": True, "id": str(row.id), "status": row.status.value}


# ---------------- Calendar --------------------------------------------

@tool(
    name="list_calendar_events",
    description=(
        "List scheduled posts (calendar events) for this org. Returns the "
        "next 25 by scheduled_at. Use when the user asks what's coming "
        "up / when something is going out."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": [s.value for s in ScheduledPostStatus],
            },
            "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 25},
        },
    },
    category="work",
)
async def list_calendar_events(
    ctx: ToolContext,
    *,
    status: str | None = None,
    limit: int = 25,
) -> dict:
    q = select(ScheduledPost).where(ScheduledPost.organization_id == ctx.org_id)
    if status:
        try:
            q = q.where(ScheduledPost.status == ScheduledPostStatus(status))
        except ValueError:
            return {"ok": False, "error": f"unknown status: {status}"}
    rows = (
        await ctx.session.execute(q.order_by(ScheduledPost.scheduled_at.asc()).limit(limit))
    ).scalars().all()
    return {
        "ok": True,
        "count": len(rows),
        "items": [
            {
                "id": str(r.id),
                "channel": r.channel.value,
                "status": r.status.value,
                "scheduled_at": r.scheduled_at.isoformat(),
                "copy_preview": (r.copy or "")[:140],
            }
            for r in rows
        ],
    }


@tool(
    name="schedule_post",
    description=(
        "Queue a new scheduled post on the calendar. Creates the post in "
        "'queued' status; it routes through the Approval Inbox before any "
        "external publish. Pass `channel`, `copy`, `scheduled_at` "
        "(ISO 8601). The Conductor never publishes directly."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "channel": {
                "type": "string",
                "enum": [c.value for c in ScheduledPostChannel],
            },
            "copy": {"type": "string", "minLength": 1, "maxLength": 8000},
            "scheduled_at": {
                "type": "string",
                "description": "ISO 8601 datetime (e.g. 2026-05-20T14:00:00Z).",
            },
            "asset_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional Asset UUIDs to attach.",
            },
            "tags": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["channel", "copy", "scheduled_at"],
    },
    requires_approval=True,
    category="work",
)
async def schedule_post(
    ctx: ToolContext,
    *,
    channel: str,
    copy: str,
    scheduled_at: str,
    asset_ids: list[str] | None = None,
    tags: list[str] | None = None,
) -> dict:
    try:
        chan = ScheduledPostChannel(channel)
    except ValueError:
        return {"ok": False, "error": f"unknown channel: {channel}"}
    try:
        when = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
    except ValueError:
        return {"ok": False, "error": "scheduled_at must be ISO 8601"}

    post = ScheduledPost(
        organization_id=ctx.org_id,
        channel=chan,
        copy=copy,
        scheduled_at=when,
        asset_ids=asset_ids,
        tags=tags,
        status=ScheduledPostStatus.queued,
        created_by_user_id=ctx.user_id,
    )
    ctx.session.add(post)
    await ctx.session.commit()
    await ctx.session.refresh(post)
    return {
        "ok": True,
        "id": str(post.id),
        "channel": post.channel.value,
        "status": post.status.value,
        "scheduled_at": post.scheduled_at.isoformat(),
    }


@tool(
    name="reschedule_event",
    description="Update the scheduled_at of an existing queued ScheduledPost.",
    input_schema={
        "type": "object",
        "properties": {
            "post_id": {"type": "string"},
            "scheduled_at": {"type": "string", "description": "ISO 8601"},
        },
        "required": ["post_id", "scheduled_at"],
    },
    category="work",
)
async def reschedule_event(
    ctx: ToolContext,
    *,
    post_id: str,
    scheduled_at: str,
) -> dict:
    try:
        pid = UUID(post_id)
        when = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    row = (
        await ctx.session.execute(
            select(ScheduledPost).where(
                ScheduledPost.id == pid,
                ScheduledPost.organization_id == ctx.org_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        return {"ok": False, "error": "post not found"}
    if row.status != ScheduledPostStatus.queued:
        return {"ok": False, "error": f"can only reschedule queued posts (was {row.status.value})"}
    row.scheduled_at = when
    await ctx.session.commit()
    return {"ok": True, "id": str(row.id), "scheduled_at": row.scheduled_at.isoformat()}


@tool(
    name="publish_now",
    description=(
        "Mark a queued ScheduledPost for immediate publishing. This is a "
        "HARD-GATED action — the post will appear in the Approval Inbox "
        "first; nothing goes live without explicit human approval. The "
        "Conductor only invokes this on direct, unambiguous user "
        "instructions referring to a specific post id."
    ),
    input_schema={
        "type": "object",
        "properties": {"post_id": {"type": "string"}},
        "required": ["post_id"],
    },
    requires_approval=True,
    category="work",
)
async def publish_now(ctx: ToolContext, *, post_id: str) -> dict:
    # Per the Inbox hard-gate rule, this tool does NOT flip status here;
    # it returns an "approval queued" receipt that the chat surface can
    # render. Real publishing only happens after Approval.
    try:
        pid = UUID(post_id)
    except ValueError:
        return {"ok": False, "error": "post_id is not a UUID"}
    row = (
        await ctx.session.execute(
            select(ScheduledPost).where(
                ScheduledPost.id == pid,
                ScheduledPost.organization_id == ctx.org_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        return {"ok": False, "error": "post not found"}
    return {
        "ok": True,
        "queued_for_approval": True,
        "post_id": str(row.id),
        "message": "Routed to Approval Inbox. Awaiting human sign-off.",
    }
