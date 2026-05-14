"""Workflow templates API (S4-D2/D6).

  GET  /api/v1/workflows/templates       — list catalog entries
  POST /api/v1/workflows/templates/{key}/clone — clone into org as a Workflow row
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.ops import Workflow, WorkflowStatus
from app.models.organization import OrganizationMembership, OrganizationRole
from app.models.user import User
from app.services.workflow_templates import get_template, list_templates


router = APIRouter(prefix="/workflows/templates", tags=["workflows"])


class TemplateOut(BaseModel):
    key: str
    label: str
    description: str
    dsl: dict


@router.get("", response_model=list[TemplateOut])
async def list_(_: User = Depends(current_active_user)) -> list[TemplateOut]:
    return [TemplateOut(**t) for t in list_templates()]


class CloneBody(BaseModel):
    organization_id: UUID
    name: str | None = None


@router.post("/{key}/clone", status_code=201)
async def clone(
    key: str,
    body: CloneBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
) -> dict:
    tpl = get_template(key)
    if tpl is None:
        raise HTTPException(status_code=404, detail="template not found")
    # Auth: admin/manager in the org.
    from sqlalchemy import select

    row = (
        await db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.organization_id == body.organization_id,
            )
        )
    ).scalar_one_or_none()
    if row is None or row.role not in (
        OrganizationRole.admin,
        OrganizationRole.manager,
    ):
        raise HTTPException(status_code=403, detail="Not an admin/manager.")

    import secrets
    import re

    base = (body.name or tpl["label"]).lower()
    base = re.sub(r"[^a-z0-9]+", "-", base).strip("-") or "workflow"
    slug = f"{base[:40]}-{secrets.token_hex(3)}"

    wf = Workflow(
        organization_id=body.organization_id,
        slug=slug,
        name=body.name or tpl["label"],
        description=tpl["description"],
        dsl_json=tpl["dsl"],
        status=WorkflowStatus.draft,
        created_by_user_id=user.id,
    )
    db.add(wf)
    await db.commit()
    await db.refresh(wf)
    return {"id": str(wf.id)}
