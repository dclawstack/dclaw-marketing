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

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
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
    started_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


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
    await _require_member(session, user, org_id)
    result = await session.execute(
        select(AgentThread)
        .where(AgentThread.organization_id == org_id)
        .order_by(AgentThread.updated_at.desc())
        .limit(100)
    )
    return [ThreadRead.model_validate(t) for t in result.scalars().all()]


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
            turn = await runner(
                body.content,
                history=history,
                images=images or None,
                doc_summaries=doc_summaries or None,
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

    return [
        MessageRead.model_validate(user_msg),
        MessageRead.model_validate(agent_msg),
    ]
