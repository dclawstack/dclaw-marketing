"""Model Registry — Org assignments + User preferences CRUD (S4-M13).

Endpoints:
  PUT /api/v1/models/org-assignments         — org-admin sets org default
  PUT /api/v1/models/user-preferences        — any user sets their override
  GET /api/v1/models/resolved-assignments    — full resolved map for the caller
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.model_assignment import OrgModelAssignment, UserModelPreference
from app.models.model_registry import (
    Capability,
    ModelEntry,
    ModelProvider,
)
from app.models.organization import OrganizationMembership, OrganizationRole
from app.models.user import User
from app.services import model_resolver as resolver_svc


router = APIRouter(prefix="/models", tags=["model-registry"])


class OrgAssignmentBody(BaseModel):
    organization_id: UUID
    capability: Capability
    model_entry_id: UUID


class UserPrefBody(BaseModel):
    organization_id: UUID
    capability: Capability
    model_entry_id: UUID


class ResolvedRow(BaseModel):
    capability: str
    resolved_by: str
    model_entry_id: UUID | None
    model_id: str | None
    provider_type: str | None


async def _writer_in(db: AsyncSession, user: User, org_id: UUID) -> bool:
    row = (
        await db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.organization_id == org_id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        return False
    return row.role in (OrganizationRole.admin, OrganizationRole.manager)


@router.put("/org-assignments")
async def upsert_org_assignment(
    body: OrgAssignmentBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
) -> dict[str, Any]:
    if not getattr(user, "is_superuser", False) and not await _writer_in(
        db, user, body.organization_id
    ):
        raise HTTPException(status_code=403, detail="Not an admin/manager.")
    # Validate the model entry exists + is visible.
    e = await db.get(ModelEntry, body.model_entry_id)
    if e is None:
        raise HTTPException(status_code=404, detail="Model entry not found.")
    p = await db.get(ModelProvider, e.provider_id)
    if p is None:
        raise HTTPException(status_code=404, detail="Parent provider missing.")
    if p.organization_id not in (None, body.organization_id):
        raise HTTPException(
            status_code=400,
            detail="Model belongs to another org and is not global.",
        )
    if body.capability.value not in (e.capabilities or []):
        raise HTTPException(
            status_code=400,
            detail=f"Model does not support capability {body.capability.value}.",
        )

    existing = (
        await db.execute(
            select(OrgModelAssignment).where(
                OrgModelAssignment.organization_id == body.organization_id,
                OrgModelAssignment.capability == body.capability.value,
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        existing = OrgModelAssignment(
            organization_id=body.organization_id,
            capability=body.capability.value,
            model_entry_id=body.model_entry_id,
            set_by_user_id=user.id,
        )
        db.add(existing)
    else:
        existing.model_entry_id = body.model_entry_id
        existing.set_by_user_id = user.id
    await db.commit()
    await db.refresh(existing)
    return {"id": str(existing.id)}


@router.put("/user-preferences")
async def upsert_user_pref(
    body: UserPrefBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
) -> dict[str, Any]:
    # Any authenticated user with active org membership can set their pref.
    member = (
        await db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.organization_id == body.organization_id,
            )
        )
    ).scalar_one_or_none()
    if member is None:
        raise HTTPException(status_code=403, detail="Not a member of that org.")

    e = await db.get(ModelEntry, body.model_entry_id)
    if e is None:
        raise HTTPException(status_code=404, detail="Model entry not found.")
    if body.capability.value not in (e.capabilities or []):
        raise HTTPException(
            status_code=400,
            detail=f"Model does not support capability {body.capability.value}.",
        )

    pref = (
        await db.execute(
            select(UserModelPreference).where(
                UserModelPreference.user_id == user.id,
                UserModelPreference.organization_id == body.organization_id,
                UserModelPreference.capability == body.capability.value,
            )
        )
    ).scalar_one_or_none()
    if pref is None:
        pref = UserModelPreference(
            user_id=user.id,
            organization_id=body.organization_id,
            capability=body.capability.value,
            model_entry_id=body.model_entry_id,
        )
        db.add(pref)
    else:
        pref.model_entry_id = body.model_entry_id
    await db.commit()
    await db.refresh(pref)
    return {"id": str(pref.id)}


@router.get("/resolved-assignments", response_model=list[ResolvedRow])
async def resolved_assignments(
    organization_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(current_active_user),
) -> list[ResolvedRow]:
    """Return the fully resolved (user → org → auto → env → stub) mapping
    of capability → model for the current user in the given org."""
    member = (
        await db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.organization_id == organization_id,
            )
        )
    ).scalar_one_or_none()
    if member is None and not getattr(user, "is_superuser", False):
        raise HTTPException(status_code=403, detail="Forbidden.")

    out: list[ResolvedRow] = []
    for cap in Capability:
        r = await resolver_svc.resolve(
            db, user_id=user.id, org_id=organization_id, capability=cap
        )
        out.append(
            ResolvedRow(
                capability=cap.value,
                resolved_by=r.resolved_by,
                model_entry_id=r.model_entry_id,
                model_id=r.model_id,
                provider_type=r.provider_type.value if r.provider_type else None,
            )
        )
    return out
