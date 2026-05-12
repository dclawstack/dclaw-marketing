"""Kanban CRUD against Project.kanban_json (SP3-20).

JSON-blob backed for v0.2.x — no migration needed. A follow-up will
promote the tasks into their own ProjectTask table when we need filters,
joins, attribution, etc.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.organization import OrganizationMembership
from app.models.project import Project
from app.models.user import User


router = APIRouter(tags=["kanban"])


_VALID_STATUSES = {"todo", "in_progress", "blocked", "done"}


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    status: str = Field(default="todo")
    assignee_user_id: str | None = None
    due_date: str | None = None
    notes: str | None = Field(default=None, max_length=2000)


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    status: str | None = None
    assignee_user_id: str | None = None
    due_date: str | None = None
    notes: str | None = Field(default=None, max_length=2000)


class TaskRead(BaseModel):
    id: str
    title: str
    status: str
    assignee_user_id: str | None = None
    due_date: str | None = None
    notes: str | None = None
    created_at: str
    updated_at: str

    model_config = ConfigDict(extra="allow")


async def _require_project_member(
    session: AsyncSession, user: User, project: Project
) -> None:
    if user.is_superuser:
        return
    m = (
        await session.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.organization_id == project.organization_id,
            )
        )
    ).scalar_one_or_none()
    if m is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this project's organization.",
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tasks(project: Project) -> list[dict]:
    blob = project.kanban_json or {}
    return list(blob.get("tasks") or [])


def _persist(project: Project, tasks: list[dict]) -> None:
    project.kanban_json = {"tasks": tasks}


@router.get("/projects/{project_id}/tasks", response_model=list[TaskRead])
async def list_tasks(
    project_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    await _require_project_member(session, user, project)
    return _tasks(project)


@router.post(
    "/projects/{project_id}/tasks",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    project_id: UUID,
    body: TaskCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    await _require_project_member(session, user, project)

    if body.status not in _VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"status must be one of {sorted(_VALID_STATUSES)}",
        )

    tasks = _tasks(project)
    new_task = {
        "id": str(uuid.uuid4()),
        "title": body.title,
        "status": body.status,
        "assignee_user_id": body.assignee_user_id,
        "due_date": body.due_date,
        "notes": body.notes,
        "created_at": _now(),
        "updated_at": _now(),
    }
    tasks.append(new_task)
    _persist(project, tasks)
    await session.commit()
    await session.refresh(project)
    return new_task


@router.patch(
    "/projects/{project_id}/tasks/{task_id}", response_model=TaskRead
)
async def update_task(
    project_id: UUID,
    task_id: str,
    body: TaskUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    await _require_project_member(session, user, project)

    tasks = _tasks(project)
    for t in tasks:
        if t.get("id") == task_id:
            patch = body.model_dump(exclude_unset=True)
            if "status" in patch and patch["status"] not in _VALID_STATUSES:
                raise HTTPException(
                    status_code=400,
                    detail=f"status must be one of {sorted(_VALID_STATUSES)}",
                )
            t.update(patch)
            t["updated_at"] = _now()
            _persist(project, tasks)
            await session.commit()
            return t
    raise HTTPException(status_code=404, detail="Task not found in project.")


@router.delete(
    "/projects/{project_id}/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_task(
    project_id: UUID,
    task_id: str,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    project = await session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found.")
    await _require_project_member(session, user, project)

    tasks = _tasks(project)
    remaining = [t for t in tasks if t.get("id") != task_id]
    if len(remaining) == len(tasks):
        raise HTTPException(status_code=404, detail="Task not found in project.")
    _persist(project, remaining)
    await session.commit()
    return None
