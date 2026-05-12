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
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import conductor as conductor_agent
from app.auth import current_active_user
from app.core.database import get_db
from app.models.agent_thread import (
    AgentKind,
    AgentMessage,
    AgentMessageRole,
    AgentThread,
)
from app.models.organization import OrganizationMembership
from app.models.user import User


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

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    content: str = Field(min_length=1, max_length=20_000)


class MessageRead(BaseModel):
    id: UUID
    thread_id: UUID
    role: AgentMessageRole
    agent_kind: AgentKind | None
    content: str
    tool_name: str | None
    tool_arguments: dict | None
    tool_result: dict | None
    metadata_json: dict | None
    approval_request_id: UUID | None
    created_at: datetime

    class Config:
        from_attributes = True


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

    # 1. User message
    user_msg = AgentMessage(
        thread_id=thread.id,
        role=AgentMessageRole.user,
        content=body.content,
    )
    session.add(user_msg)
    await session.flush()

    # 2. Agent reply
    if thread.kind == AgentKind.conductor:
        turn = conductor_agent.reply(body.content)
        agent_msg = AgentMessage(
            thread_id=thread.id,
            role=AgentMessageRole.agent,
            agent_kind=AgentKind.conductor,
            content=turn.text,
            metadata_json={
                "confidence": turn.confidence,
                "suggestions": turn.suggestions or [],
            },
        )
    else:
        # Role-agent threads — Phase 9.x adds real per-agent stubs.
        agent_msg = AgentMessage(
            thread_id=thread.id,
            role=AgentMessageRole.agent,
            agent_kind=thread.kind,
            content=(
                "I'll respond more substantively once the Phase 9.x "
                f"{thread.kind.value} agent stub lands. For now the "
                "Conductor (/agent) is the place to bring requests."
            ),
            metadata_json={"confidence": 0.4},
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
