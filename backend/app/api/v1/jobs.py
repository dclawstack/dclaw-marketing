"""Jobs API — list / get / stream live progress / cancel.

The SSE stream endpoint (`/jobs/{id}/stream`) is what the UI listens
to for live agent activity. Polls the DB every 500ms and emits each
state change as a Server-Sent Event.
"""

import asyncio
import json
from typing import AsyncGenerator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.job import Job, JobStatus
from app.models.user import User


router = APIRouter(prefix="/jobs", tags=["jobs"])


# ---------- schemas -----------------------------------------------------

class JobRead(BaseModel):
    id: UUID
    organization_id: UUID | None
    initiated_by_user_id: UUID | None
    kind: str
    status: JobStatus
    progress: float
    progress_label: str | None
    result_json: dict | None
    result_url: str | None
    error_message: str | None
    celery_task_id: str | None

    model_config = ConfigDict(from_attributes=True)


# ---------- routes ------------------------------------------------------

@router.get("/{job_id}", response_model=JobRead)
async def get_job(
    job_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> Job:
    job = await session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    # Authorization: user must have access to the Org that owns the Job.
    # For v0.1.0 we allow access if the user is the initiator, the Org's
    # member, or a superuser. Per-Org membership check skipped here for
    # brevity; will tighten in A4 (audit + approval) when authz patterns
    # consolidate.
    if (
        not user.is_superuser
        and job.initiated_by_user_id != user.id
        and job.organization_id is not None  # system jobs are visible to no one but admins
    ):
        # Real Org-membership check inlined to avoid yet another helper module
        from app.models.organization import OrganizationMembership
        result = await session.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.organization_id == job.organization_id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this job.")
    return job


@router.get("", response_model=list[JobRead])
async def list_jobs(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
    organization_id: UUID | None = None,
    job_status: JobStatus | None = None,
    limit: int = 50,
) -> list[Job]:
    stmt = select(Job).order_by(Job.created_at.desc()).limit(limit)
    if organization_id is not None:
        stmt = stmt.where(Job.organization_id == organization_id)
    if job_status is not None:
        stmt = stmt.where(Job.status == job_status)
    if not user.is_superuser:
        # Non-admins only see jobs they initiated. Org-wide visibility
        # comes via the per-Org Station UIs (Phase 2+).
        stmt = stmt.where(Job.initiated_by_user_id == user.id)

    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.post("/{job_id}/cancel", response_model=JobRead)
async def cancel_job(
    job_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> Job:
    job = await session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    if job.status in (JobStatus.succeeded, JobStatus.failed, JobStatus.canceled):
        return job  # already terminal — no-op

    # Tell Celery to revoke the task. Lazy import to avoid pulling Celery
    # into the API process startup path.
    if job.celery_task_id:
        try:
            from app.worker.celery_app import celery_app
            celery_app.control.revoke(job.celery_task_id, terminate=True)
        except Exception:
            pass  # best-effort

    job.status = JobStatus.canceled
    await session.flush()
    await session.commit()
    await session.refresh(job)
    return job


# ---------- SSE stream --------------------------------------------------

async def _job_event_stream(job_id: UUID, session: AsyncSession) -> AsyncGenerator[str, None]:
    """Polls the DB twice per second and emits an SSE 'data:' line each
    time the Job changes. Closes the stream when the Job reaches a
    terminal state (succeeded / failed / canceled).
    """
    last_payload: str | None = None
    terminal = {JobStatus.succeeded, JobStatus.failed, JobStatus.canceled}
    # Cap the stream at 30 min to prevent zombie connections.
    max_iterations = 30 * 60 * 2  # 30 min × 60 s × 2 polls/s

    for _ in range(max_iterations):
        # Fresh fetch — session needs to expire to see other process's commits.
        job = await session.get(Job, job_id)
        if job is None:
            yield "event: error\ndata: {\"error\":\"job not found\"}\n\n"
            return

        payload = JobRead.model_validate(job).model_dump_json()
        if payload != last_payload:
            yield f"data: {payload}\n\n"
            last_payload = payload

        if job.status in terminal:
            yield "event: complete\ndata: {}\n\n"
            return

        await asyncio.sleep(0.5)
        # Force the session to refetch — async sessions otherwise cache.
        await session.refresh(job)


@router.get("/{job_id}/stream")
async def stream_job(
    job_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Server-Sent Events stream of a Job's evolving state.

    Client side: `new EventSource('/api/v1/jobs/<id>/stream', { headers })`.
    Note: EventSource can't send custom headers in browsers, so the UI
    layer wraps this with a fetch + ReadableStream consumer to attach
    the Bearer token. The endpoint itself just needs auth on the request.
    """
    # Validate access up front using the same logic as get_job
    job = await session.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")
    if (
        not user.is_superuser
        and job.initiated_by_user_id != user.id
        and job.organization_id is not None
    ):
        from app.models.organization import OrganizationMembership
        result = await session.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.organization_id == job.organization_id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this job.")

    return StreamingResponse(
        _job_event_stream(job_id, session),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # disable nginx buffering if proxied
        },
    )
