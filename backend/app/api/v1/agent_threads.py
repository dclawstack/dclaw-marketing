"""Agent threads API — Conductor + role-agent conversation memory.

Endpoints:
  GET    /orgs/{org_id}/agent-threads             — list this org's threads
  POST   /orgs/{org_id}/agent-threads             — create a new thread
  GET    /orgs/{org_id}/agent-threads/{id}/messages
  POST   /orgs/{org_id}/agent-threads/{id}/messages
                                                  — append a user message;
                                                    the agent replies inline
                                                    (Phase 9 stub).
"""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import (
    analyst as analyst_agent,
    conductor as conductor_agent,
    paid_media as paid_media_agent,
    seo as seo_agent,
    smm as smm_agent,
)
from app.auth import current_active_user
from app.core.database import get_db
from app.models.agent_thread import (
    AgentKind,
    AgentMessage,
    AgentMessageRole,
    AgentThread,
)
from app.models.asset import Asset
from app.models.organization import OrganizationMembership
from app.models.user import User
from app.services import storage as storage_service


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/orgs/{org_id}/agent-threads", tags=["agent-threads"]
)


class ThreadCreate(BaseModel):
    kind: AgentKind = AgentKind.conductor
    title: str | None = Field(default=None, max_length=512)
    project_id: UUID | None = None


class ThreadRead(BaseModel):
    id: UUID
    organization_id: UUID
    project_id: UUID | None
    parent_thread_id: UUID | None
    kind: AgentKind
    title: str | None
    is_pinned: bool = False
    started_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ThreadPatch(BaseModel):
    title: str | None = Field(default=None, max_length=512)
    is_pinned: bool | None = None


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=20_000)
    # Asset UUIDs the user attached to this turn. The server resolves
    # each to its bytes/metadata and threads it into the agent prompt
    # — images become Claude vision blocks; docs become summary lines
    # in the user-prompt. (S5-CDR-B)
    attachment_asset_ids: list[UUID] | None = None


class MessageRead(BaseModel):
    id: UUID
    thread_id: UUID
    role: AgentMessageRole
    agent_kind: AgentKind | None
    content: str
    tool_name: str | None
    tool_arguments: dict | None
    tool_result: dict | None
    attachment_asset_ids: list[str] | None = None
    metadata_json: dict | None
    approval_request_id: UUID | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


async def _require_member(
    session: AsyncSession, user: User, org_id: UUID
) -> None:
    if user.is_superuser:
        return
    result = await session.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == org_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not a member."
        )


async def _get_thread_or_404(
    session: AsyncSession, org_id: UUID, thread_id: UUID
) -> AgentThread:
    result = await session.execute(
        select(AgentThread).where(
            AgentThread.id == thread_id,
            AgentThread.organization_id == org_id,
        )
    )
    t = result.scalar_one_or_none()
    if t is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found."
        )
    return t


@router.post(
    "", response_model=ThreadRead, status_code=status.HTTP_201_CREATED
)
async def create_thread(
    org_id: UUID,
    body: ThreadCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> ThreadRead:
    await _require_member(session, user, org_id)
    t = AgentThread(
        organization_id=org_id,
        project_id=body.project_id,
        kind=body.kind,
        title=body.title,
        started_by_user_id=user.id,
    )
    session.add(t)
    await session.commit()
    await session.refresh(t)
    return ThreadRead.model_validate(t)


@router.get("", response_model=list[ThreadRead])
async def list_threads(
    org_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> list[ThreadRead]:
    """List threads — pinned first, then by updated_at desc (S5-CDR-F)."""
    await _require_member(session, user, org_id)
    result = await session.execute(
        select(AgentThread)
        .where(AgentThread.organization_id == org_id)
        .order_by(
            AgentThread.is_pinned.desc(),
            AgentThread.updated_at.desc(),
        )
        .limit(100)
    )
    return [ThreadRead.model_validate(t) for t in result.scalars().all()]


@router.patch("/{thread_id}", response_model=ThreadRead)
async def patch_thread(
    org_id: UUID,
    thread_id: UUID,
    body: ThreadPatch,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> ThreadRead:
    """Rename / pin / unpin a thread (S5-CDR-F)."""
    await _require_member(session, user, org_id)
    thread = await _get_thread_or_404(session, org_id, thread_id)
    if body.title is not None:
        thread.title = body.title or None
    if body.is_pinned is not None:
        thread.is_pinned = body.is_pinned
    await session.commit()
    await session.refresh(thread)
    return ThreadRead.model_validate(thread)


@router.delete(
    "/{thread_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_thread(
    org_id: UUID,
    thread_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Delete a thread (and all its messages cascade) (S5-CDR-F)."""
    await _require_member(session, user, org_id)
    thread = await _get_thread_or_404(session, org_id, thread_id)
    await session.delete(thread)
    await session.commit()


@router.get(
    "/{thread_id}/messages", response_model=list[MessageRead]
)
async def list_messages(
    org_id: UUID,
    thread_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> list[MessageRead]:
    await _require_member(session, user, org_id)
    await _get_thread_or_404(session, org_id, thread_id)
    result = await session.execute(
        select(AgentMessage)
        .where(AgentMessage.thread_id == thread_id)
        .order_by(AgentMessage.created_at.asc())
    )
    return [MessageRead.model_validate(m) for m in result.scalars().all()]


@router.post(
    "/{thread_id}/messages",
    response_model=list[MessageRead],
    status_code=status.HTTP_201_CREATED,
)
async def post_message(
    org_id: UUID,
    thread_id: UUID,
    body: MessageCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> list[MessageRead]:
    """Append a user message; the agent replies synchronously (Phase 9
    stub). Returns BOTH the new user message and the agent's reply.
    """
    await _require_member(session, user, org_id)
    thread = await _get_thread_or_404(session, org_id, thread_id)

    # 0. Resolve attachments (S5-CDR-B). Each Asset must belong to the
    #    same org as the thread, else we 403. Images become Claude
    #    vision blocks; non-images become summary lines in the user
    #    prompt and are queued for KG ingestion (see follow-up).
    attachment_ids: list[str] | None = None
    images: list[tuple[str, bytes]] = []
    doc_summaries: list[str] = []
    if body.attachment_asset_ids:
        asset_rows = (
            await session.execute(
                select(Asset).where(
                    Asset.id.in_(body.attachment_asset_ids),
                )
            )
        ).scalars().all()
        found_ids = {a.id for a in asset_rows}
        missing = set(body.attachment_asset_ids) - found_ids
        if missing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Attachment(s) not found: {sorted(str(m) for m in missing)}",
            )
        for a in asset_rows:
            if a.organization_id is not None and a.organization_id != org_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Attachment belongs to a different organization.",
                )
        attachment_ids = [str(a.id) for a in asset_rows]
        for a in asset_rows:
            if a.kind == "image" and a.mime_type:
                try:
                    raw = await storage_service.get_object_bytes(
                        a.storage_key, bucket=a.bucket
                    )
                    images.append((a.mime_type, raw))
                except Exception:  # pragma: no cover — storage hiccup
                    doc_summaries.append(
                        f"image (failed to fetch): {a.original_filename or a.id}"
                    )
            else:
                doc_summaries.append(
                    f"{a.kind} attachment: "
                    f"{a.original_filename or a.id} "
                    f"({a.mime_type or 'unknown mime'}, "
                    f"{a.size_bytes or '?'} bytes)"
                )

    # 1. User message
    user_msg = AgentMessage(
        thread_id=thread.id,
        role=AgentMessageRole.user,
        content=body.content,
        attachment_asset_ids=attachment_ids,
    )
    session.add(user_msg)
    await session.flush()

    # 2. Agent reply — fetch the thread's prior turns so the agent has
    #    context (last 10 turns are passed to Claude).
    prior = await session.execute(
        select(AgentMessage)
        .where(AgentMessage.thread_id == thread.id)
        .order_by(AgentMessage.created_at.asc())
    )
    history = [
        {"role": m.role.value, "content": m.content}
        for m in prior.scalars().all()
        if m.id != user_msg.id
    ]

    # Route by AgentKind to the right role-agent module (Phase 9.2).
    # Only the conductor consumes images/docs today — role-agents get
    # the same support in subsequent issues (see S5-CDR-C tool fleet).
    _ROUTER = {
        AgentKind.conductor: conductor_agent.reply,
        AgentKind.smm: smm_agent.reply,
        AgentKind.seo: seo_agent.reply,
        AgentKind.paid_media: paid_media_agent.reply,
        AgentKind.analyst: analyst_agent.reply,
    }
    runner = _ROUTER.get(thread.kind)
    tool_msgs: list[AgentMessage] = []
    if runner is None:
        # Unknown / not-yet-implemented kind (e.g. inbox agent).
        agent_msg = AgentMessage(
            thread_id=thread.id,
            role=AgentMessageRole.agent,
            agent_kind=thread.kind,
            content=(
                f"The {thread.kind.value} agent stub isn't online yet. "
                "Bring requests to the Conductor at /conductor for now."
            ),
            metadata_json={"confidence": 0.4},
        )
    else:
        if thread.kind == AgentKind.conductor:
            # Agentic loop: Claude calls into REGISTRY tools, we
            # persist each tool call as its own role=tool row so the
            # UI can render tool-call cards inline. (S5-CDR-C)
            from app.agents.conductor import reply_agentic
            from app.agents.tools.registry import ToolContext

            tool_ctx = ToolContext(
                org_id=org_id,
                user_id=user.id,
                session=session,
            )
            agentic = await reply_agentic(
                body.content,
                history=history,
                images=images or None,
                doc_summaries=doc_summaries or None,
                tool_ctx=tool_ctx,
            )
            # Persist tool-call rows in dispatch order.
            for call in agentic.tool_calls:
                tool_msg = AgentMessage(
                    thread_id=thread.id,
                    role=AgentMessageRole.tool,
                    agent_kind=thread.kind,
                    content="",
                    tool_name=call.get("name") or "",
                    tool_arguments=call.get("input") or {},
                    tool_result=call.get("result") or {},
                    metadata_json={
                        "tool_use_id": call.get("tool_use_id"),
                    },
                )
                session.add(tool_msg)
                tool_msgs.append(tool_msg)
            agent_msg = AgentMessage(
                thread_id=thread.id,
                role=AgentMessageRole.agent,
                agent_kind=thread.kind,
                content=agentic.text,
                metadata_json={
                    "confidence": agentic.confidence,
                    "suggestions": [],
                    "tool_call_count": len(agentic.tool_calls),
                },
            )
        else:
            turn = await runner(body.content, history=history)
            agent_msg = AgentMessage(
                thread_id=thread.id,
                role=AgentMessageRole.agent,
                agent_kind=thread.kind,
                content=turn.text,
                metadata_json={
                    "confidence": turn.confidence,
                    "suggestions": turn.suggestions or [],
                },
            )
    session.add(agent_msg)

    # Touch updated_at on the thread.
    thread.updated_at = user_msg.created_at
    await session.commit()
    await session.refresh(user_msg)
    await session.refresh(agent_msg)
    for tm in tool_msgs:
        await session.refresh(tm)

    return [
        MessageRead.model_validate(user_msg),
        *(MessageRead.model_validate(tm) for tm in tool_msgs),
        MessageRead.model_validate(agent_msg),
    ]


# ============================================================
# S5-CDR-D — Streaming response endpoint
# ============================================================

class StreamMessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=20_000)
    attachment_asset_ids: list[UUID] | None = None
    # Claude extended-thinking budget (0/None disables). Caller toggles
    # this from the ModelSettingsPanel.
    thinking_budget_tokens: int | None = Field(default=None, ge=0, le=64_000)
    # Research mode (S5-CDR-E): quick | light | deep. Controls how
    # aggressively the agent uses web_search / fetch_url tools.
    research_mode: str | None = Field(default=None)


@router.post("/{thread_id}/messages/stream")
async def post_message_stream(
    org_id: UUID,
    thread_id: UUID,
    body: StreamMessageCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Server-Sent Events stream for a Conductor turn (S5-CDR-D).

    Same semantics as POST /messages, but token-by-token. Yields SSE
    events: `text_delta`, `thinking_delta`, `tool_call_start`,
    `tool_call_result`, `agent_msg_start`, `done`, `error`. After the
    final `done`, the persisted message rows are saved to the DB and
    referenced in the `done` payload so the client can `refresh()`
    cleanly.
    """
    import json as _json
    from app.agents.conductor import reply_agentic_streaming
    from app.agents.tools.registry import ToolContext

    await _require_member(session, user, org_id)
    thread = await _get_thread_or_404(session, org_id, thread_id)

    # Resolve attachments — same logic as the non-streaming endpoint.
    attachment_ids: list[str] | None = None
    images: list[tuple[str, bytes]] = []
    doc_summaries: list[str] = []
    if body.attachment_asset_ids:
        asset_rows = (
            await session.execute(
                select(Asset).where(Asset.id.in_(body.attachment_asset_ids))
            )
        ).scalars().all()
        found = {a.id for a in asset_rows}
        missing = set(body.attachment_asset_ids) - found
        if missing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Attachment(s) not found: {sorted(str(m) for m in missing)}",
            )
        for a in asset_rows:
            if a.organization_id is not None and a.organization_id != org_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Attachment belongs to a different organization.",
                )
        attachment_ids = [str(a.id) for a in asset_rows]
        for a in asset_rows:
            if a.kind == "image" and a.mime_type:
                try:
                    raw = await storage_service.get_object_bytes(
                        a.storage_key, bucket=a.bucket
                    )
                    images.append((a.mime_type, raw))
                except Exception:
                    doc_summaries.append(
                        f"image (failed to fetch): {a.original_filename or a.id}"
                    )
            else:
                doc_summaries.append(
                    f"{a.kind} attachment: {a.original_filename or a.id} "
                    f"({a.mime_type or 'unknown mime'}, {a.size_bytes or '?'} bytes)"
                )

    # Persist user message FIRST so the agentic loop has stable history.
    user_msg = AgentMessage(
        thread_id=thread.id,
        role=AgentMessageRole.user,
        content=body.content,
        attachment_asset_ids=attachment_ids,
    )
    session.add(user_msg)
    await session.commit()
    await session.refresh(user_msg)

    # Pull history (including the just-persisted user msg's earlier
    # turns — the user_msg itself is the current turn, so exclude it).
    prior_rows = (
        await session.execute(
            select(AgentMessage)
            .where(AgentMessage.thread_id == thread.id)
            .order_by(AgentMessage.created_at.asc())
        )
    ).scalars().all()
    history = [
        {"role": m.role.value, "content": m.content}
        for m in prior_rows
        if m.id != user_msg.id
    ]

    tool_ctx = ToolContext(org_id=org_id, user_id=user.id, session=session)

    async def event_source():
        # SSE opener — flush the user-msg id immediately so the client
        # can render the optimistic bubble as a persisted row.
        yield _sse("user_msg_persisted", {"id": str(user_msg.id)})

        accumulated_tool_calls: list[dict] = []
        final_text: str = ""
        thinking_blob: str = ""
        try:
            if thread.kind == AgentKind.conductor:
                async for ev in reply_agentic_streaming(
                    body.content,
                    history=history,
                    images=images or None,
                    doc_summaries=doc_summaries or None,
                    tool_ctx=tool_ctx,
                    thinking_budget_tokens=body.thinking_budget_tokens,
                    research_mode=body.research_mode,
                ):
                    if ev.get("event") == "done":
                        final_text = ev.get("final_text", "")
                        accumulated_tool_calls = ev.get("tool_calls") or []
                        thinking_blob = ev.get("thinking", "")
                        break
                    yield _sse(ev.get("event", "delta"), {k: v for k, v in ev.items() if k != "event"})
            else:
                # Non-conductor agents fall back to single-shot reply.
                from app.agents import (
                    analyst as analyst_agent,
                    paid_media as paid_media_agent,
                    seo as seo_agent,
                    smm as smm_agent,
                )
                non_conductor_runners = {
                    AgentKind.smm: smm_agent.reply,
                    AgentKind.seo: seo_agent.reply,
                    AgentKind.paid_media: paid_media_agent.reply,
                    AgentKind.analyst: analyst_agent.reply,
                }
                runner = non_conductor_runners.get(thread.kind)
                if runner is None:
                    final_text = (
                        f"The {thread.kind.value} agent stub isn't online yet. "
                        "Bring requests to the Conductor at /conductor for now."
                    )
                    yield _sse("agent_msg_start", {})
                    yield _sse("text_delta", {"text": final_text})
                else:
                    turn = await runner(body.content, history=history)
                    final_text = turn.text
                    yield _sse("agent_msg_start", {})
                    yield _sse("text_delta", {"text": final_text})
        except Exception as e:  # pragma: no cover — defensive
            logger.exception("Streaming generator failed")
            yield _sse("error", {"error": str(e)})

        # Persist tool-call + agent rows + return their ids in the done event.
        tool_row_ids: list[str] = []
        for call in accumulated_tool_calls:
            tool_msg = AgentMessage(
                thread_id=thread.id,
                role=AgentMessageRole.tool,
                agent_kind=thread.kind,
                content="",
                tool_name=call.get("name") or "",
                tool_arguments=call.get("input") or {},
                tool_result=call.get("result") or {},
                metadata_json={"tool_use_id": call.get("tool_use_id")},
            )
            session.add(tool_msg)
            await session.flush()
            tool_row_ids.append(str(tool_msg.id))

        agent_metadata: dict = {
            "confidence": 0.85,
            "suggestions": [],
            "tool_call_count": len(accumulated_tool_calls),
        }
        if thinking_blob:
            agent_metadata["thinking"] = thinking_blob[:60_000]

        agent_msg = AgentMessage(
            thread_id=thread.id,
            role=AgentMessageRole.agent,
            agent_kind=thread.kind,
            content=final_text or "Done.",
            metadata_json=agent_metadata,
        )
        session.add(agent_msg)
        thread.updated_at = user_msg.created_at
        await session.commit()
        await session.refresh(agent_msg)

        yield _sse(
            "done",
            {
                "user_msg_id": str(user_msg.id),
                "tool_msg_ids": tool_row_ids,
                "agent_msg_id": str(agent_msg.id),
                "tool_call_count": len(accumulated_tool_calls),
            },
        )

    return StreamingResponse(
        event_source(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
        },
    )


def _sse(event: str, data: dict) -> str:
    """Encode one SSE frame. `event:` line + `data:` JSON + blank line."""
    import json as _json
    return f"event: {event}\ndata: {_json.dumps(data)}\n\n"
