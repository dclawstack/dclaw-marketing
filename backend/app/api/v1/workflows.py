"""Workflow execution API (Phase 10.4).

Kicks the synchronous DAG runner from #141 against a persisted
``Workflow.dsl_json``, storing the result as a ``WorkflowRun`` row.

Two endpoints:

  • POST /orgs/{org_id}/workflows/{workflow_id}/runs
        Kicks a new run. Returns the WorkflowRun row.
  • GET  /orgs/{org_id}/workflow-runs/{run_id}
        Reads an existing run's status + result.

Paused state (approval / branch nodes) is recognised by the runner
but not yet resumed by an endpoint — see deferred_reason on the
returned run for details. Resume support lands in a follow-up.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.ops import Workflow, WorkflowRun, WorkflowRunStatus, WorkflowStatus
from app.models.organization import OrganizationMembership, OrganizationRole
from app.models.user import User
from app.services.workflow_runner import (
    WorkflowError,
    resume_workflow_run,
    run_workflow,
)


router = APIRouter(tags=["workflows"])


# ---------- schemas ----------------------------------------------------


class WorkflowRunCreate(BaseModel):
    initial_context: dict[str, Any] = Field(default_factory=dict)


class WorkflowRunRead(BaseModel):
    id: UUID
    workflow_id: UUID
    organization_id: UUID
    status: WorkflowRunStatus
    initial_context: dict
    final_context: dict | None
    node_results: list | None
    deferred_reason: str | None
    error_message: str | None
    started_by_user_id: UUID | None
    started_at: datetime
    completed_at: datetime | None

    class Config:
        from_attributes = True


# ---------- helpers ----------------------------------------------------


_RUN_ROLES: tuple[OrganizationRole, ...] = (
    OrganizationRole.admin,
    OrganizationRole.manager,
    OrganizationRole.creatives,
    OrganizationRole.social_media_manager,
    OrganizationRole.seo_specialist,
    OrganizationRole.paid_media_specialist,
)


async def _user_can_run(
    session: AsyncSession,
    user: User,
    org_id: UUID,
) -> None:
    if user.is_superuser:
        return
    result = await session.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == org_id,
        )
    )
    m = result.scalar_one_or_none()
    if m is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not a member."
        )
    if m.role not in _RUN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role {m.role.value} cannot run workflows.",
        )


async def _user_can_view(
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


# ---------- routes -----------------------------------------------------


@router.post(
    "/orgs/{org_id}/workflows/{workflow_id}/runs",
    response_model=WorkflowRunRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_workflow_run(
    org_id: UUID,
    workflow_id: UUID,
    body: WorkflowRunCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> WorkflowRunRead:
    await _user_can_run(session, user, org_id)

    workflow = await session.get(Workflow, workflow_id)
    if workflow is None or workflow.organization_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found in this organization.",
        )

    # Persist the run row up front so we have an audit trail even if
    # the runner raises.
    run_row = WorkflowRun(
        workflow_id=workflow.id,
        organization_id=org_id,
        initial_context=body.initial_context,
        status=WorkflowRunStatus.running,
        started_by_user_id=user.id,
    )
    session.add(run_row)
    await session.flush()

    try:
        result = await run_workflow(
            workflow=workflow,
            initial_context=body.initial_context,
            session=session,
        )
    except WorkflowError as exc:
        run_row.status = WorkflowRunStatus.failed
        run_row.error_message = str(exc)
        run_row.completed_at = datetime.now(tz=timezone.utc)
        await session.commit()
        await session.refresh(run_row)
        return WorkflowRunRead.model_validate(run_row)

    # Serialise NodeResult dataclasses
    run_row.node_results = [
        {
            "node_id": n.node_id,
            "type": n.type,
            "output": n.output,
            "error": n.error,
        }
        for n in result.nodes
    ]
    run_row.final_context = result.final_context
    if result.completed:
        run_row.status = WorkflowRunStatus.completed
    elif result.deferred_reason:
        run_row.status = WorkflowRunStatus.paused
        run_row.deferred_reason = result.deferred_reason
    else:
        run_row.status = WorkflowRunStatus.failed
    run_row.completed_at = datetime.now(tz=timezone.utc)
    await session.commit()
    await session.refresh(run_row)
    return WorkflowRunRead.model_validate(run_row)


@router.post(
    "/orgs/{org_id}/workflow-runs/{run_id}/resume",
    response_model=WorkflowRunRead,
)
async def resume_workflow_run_endpoint(
    org_id: UUID,
    run_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> WorkflowRunRead:
    """Re-enter a paused WorkflowRun.

    Typical flow: a previous ``POST .../runs`` hit an ``approval`` node
    and returned with status=paused + ``deferred_reason="approval:<id>"``.
    The reviewer approved or rejected the ApprovalRequest. The caller
    POSTs to this endpoint to continue.

    The runner short-circuits the deferred node based on the
    ApprovalRequest's current status, skips already-completed nodes,
    and runs the rest of the DAG.
    """
    await _user_can_run(session, user, org_id)
    run_row = await session.get(WorkflowRun, run_id)
    if run_row is None or run_row.organization_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow run not found in this organization.",
        )
    if run_row.status not in (
        WorkflowRunStatus.paused,
        WorkflowRunStatus.running,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Run is in status {run_row.status.value}; only paused / "
                "running runs can be resumed."
            ),
        )
    run_row.status = WorkflowRunStatus.running
    await session.flush()

    try:
        result = await resume_workflow_run(run_id=run_id, session=session)
    except WorkflowError as exc:
        run_row.status = WorkflowRunStatus.failed
        run_row.error_message = str(exc)
        run_row.completed_at = datetime.now(tz=timezone.utc)
        await session.commit()
        await session.refresh(run_row)
        return WorkflowRunRead.model_validate(run_row)

    # Merge new node_results onto the existing ones (skip duplicates).
    existing = run_row.node_results or []
    existing_ids = {
        (r.get("node_id") if isinstance(r, dict) else r["node_id"])
        for r in existing
    }
    new_rows = [
        {
            "node_id": n.node_id,
            "type": n.type,
            "output": n.output,
            "error": n.error,
        }
        for n in result.nodes
        if n.node_id not in existing_ids
    ]
    run_row.node_results = existing + new_rows
    run_row.final_context = result.final_context
    if result.completed:
        run_row.status = WorkflowRunStatus.completed
        run_row.deferred_reason = None
    elif result.deferred_reason:
        run_row.status = WorkflowRunStatus.paused
        run_row.deferred_reason = result.deferred_reason
    else:
        run_row.status = WorkflowRunStatus.failed
    run_row.completed_at = datetime.now(tz=timezone.utc)
    await session.commit()
    await session.refresh(run_row)
    return WorkflowRunRead.model_validate(run_row)


@router.get(
    "/orgs/{org_id}/workflow-runs/{run_id}",
    response_model=WorkflowRunRead,
)
async def get_workflow_run(
    org_id: UUID,
    run_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> WorkflowRunRead:
    await _user_can_view(session, user, org_id)
    run_row = await session.get(WorkflowRun, run_id)
    if run_row is None or run_row.organization_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow run not found in this organization.",
        )
    return WorkflowRunRead.model_validate(run_row)


@router.get(
    "/orgs/{org_id}/workflows/{workflow_id}/runs",
    response_model=list[WorkflowRunRead],
)
async def list_workflow_runs(
    org_id: UUID,
    workflow_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
    limit: int = 25,
) -> list[WorkflowRunRead]:
    await _user_can_view(session, user, org_id)
    rows = (
        (
            await session.execute(
                select(WorkflowRun)
                .where(
                    WorkflowRun.workflow_id == workflow_id,
                    WorkflowRun.organization_id == org_id,
                )
                .order_by(WorkflowRun.started_at.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return [WorkflowRunRead.model_validate(r) for r in rows]


# ---------- §6.6 — workflow templates ---------------------------------------


class WorkflowRead(BaseModel):
    id: UUID
    organization_id: UUID
    slug: str
    name: str
    description: str | None = None
    is_template: bool
    cloned_from_workflow_id: UUID | None = None

    class Config:
        from_attributes = True


class WorkflowCloneRequest(BaseModel):
    target_organization_id: UUID
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=128)
    description: str | None = None


@router.get(
    "/orgs/{org_id}/workflow-templates",
    response_model=list[WorkflowRead],
)
async def list_workflow_templates(
    org_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> list[WorkflowRead]:
    """Return every ``is_template=True`` workflow in this Org. The UI
    surfaces these as 'starter templates' on the workflow-create page."""
    await _user_can_view(session, user, org_id)
    rows = (
        (
            await session.execute(
                select(Workflow)
                .where(
                    Workflow.organization_id == org_id,
                    Workflow.is_template.is_(True),
                )
                .order_by(Workflow.updated_at.desc())
            )
        )
        .scalars()
        .all()
    )
    return [WorkflowRead.model_validate(r) for r in rows]


@router.patch(
    "/orgs/{org_id}/workflows/{workflow_id}/template",
    response_model=WorkflowRead,
)
async def set_workflow_template_flag(
    org_id: UUID,
    workflow_id: UUID,
    is_template: bool,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> WorkflowRead:
    await _user_can_run(session, user, org_id)
    workflow = await session.get(Workflow, workflow_id)
    if workflow is None or workflow.organization_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow not found in this organization.",
        )
    workflow.is_template = bool(is_template)
    await session.commit()
    await session.refresh(workflow)
    return WorkflowRead.model_validate(workflow)


@router.post(
    "/orgs/{org_id}/workflows/{workflow_id}/clone",
    response_model=WorkflowRead,
    status_code=status.HTTP_201_CREATED,
)
async def clone_workflow(
    org_id: UUID,
    workflow_id: UUID,
    body: WorkflowCloneRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> WorkflowRead:
    """Clone a workflow (typically a template) into ``target_organization_id``.

    The caller must be a member of both the source Org (to read) and the
    target Org (to write). The new workflow starts in ``draft`` status,
    copies the source ``dsl_json`` byte-for-byte, and records the source
    id on ``cloned_from_workflow_id`` for lineage.
    """
    await _user_can_view(session, user, org_id)
    await _user_can_run(session, user, body.target_organization_id)

    source = await session.get(Workflow, workflow_id)
    if source is None or source.organization_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source workflow not found in this organization.",
        )

    clone = Workflow(
        organization_id=body.target_organization_id,
        slug=body.slug,
        name=body.name,
        description=body.description or source.description,
        dsl_json=dict(source.dsl_json or {}),
        status=WorkflowStatus.draft,
        is_template=False,
        cloned_from_workflow_id=source.id,
        created_by_user_id=user.id,
    )
    session.add(clone)
    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Workflow with this slug already exists in the target organization.",
        )
    await session.refresh(clone)
    return WorkflowRead.model_validate(clone)
