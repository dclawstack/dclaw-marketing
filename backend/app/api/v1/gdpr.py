"""GDPR data-export HTTP endpoints — Phase 11.4.

POST /api/v1/orgs/{org_id}/gdpr-export
    Admin-only. Creates a DataExportRequest row, fires the Celery
    task, returns the request id (caller polls GET to check progress).

GET /api/v1/orgs/{org_id}/gdpr-exports/{request_id}
    Returns the export's status. When ``ready``, the response includes
    a 24-hour presigned download URL to MinIO. When ``expired``, the
    presigned URL is omitted.

The right-to-delete companion endpoint (DELETE /leads/{lead_id}) is
implemented in the existing leads router via the CASCADE FK on
LeadActivity + LeadNote; this PR doesn't change that.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.ops import DataExportRequest, DataExportStatus
from app.models.organization import OrganizationMembership, OrganizationRole
from app.models.user import User
from app.services.storage import presigned_get_url


router = APIRouter(prefix="/orgs", tags=["gdpr"])


class ExportRequestOut(BaseModel):
    id: UUID
    organization_id: UUID
    status: DataExportStatus
    scope: str
    storage_key: str | None
    error_message: str | None
    expires_at: str | None
    download_url: str | None
    created_at: str
    completed_at: str | None

    model_config = ConfigDict(from_attributes=True)


async def _require_admin(
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
    if m is None or m.role != OrganizationRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Org admins or superusers can request GDPR exports.",
        )


@router.post(
    "/{org_id}/gdpr-export",
    response_model=ExportRequestOut,
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_gdpr_export(
    org_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> ExportRequestOut:
    await _require_admin(session, user, org_id)

    req = DataExportRequest(
        organization_id=org_id,
        requested_by_user_id=user.id,
        scope="full",
        status=DataExportStatus.queued,
    )
    session.add(req)
    await session.flush()
    await session.commit()
    await session.refresh(req)

    # Kick the Celery task — late import to avoid the worker module
    # graph being part of the FastAPI request-time imports.
    from app.worker.tasks.gdpr import export_organization_data

    export_organization_data.delay(str(org_id), request_id=str(req.id))

    return ExportRequestOut(
        id=req.id,
        organization_id=req.organization_id,
        status=req.status,
        scope=req.scope,
        storage_key=req.storage_key,
        error_message=req.error_message,
        expires_at=req.expires_at.isoformat() if req.expires_at else None,
        download_url=None,
        created_at=req.created_at.isoformat(),
        completed_at=req.completed_at.isoformat() if req.completed_at else None,
    )


@router.get(
    "/{org_id}/gdpr-exports/{request_id}",
    response_model=ExportRequestOut,
)
async def get_gdpr_export(
    org_id: UUID,
    request_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> ExportRequestOut:
    await _require_admin(session, user, org_id)

    req = await session.get(DataExportRequest, request_id)
    if req is None or req.organization_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Export request not found for this organization.",
        )

    download_url: str | None = None
    if (
        req.status == DataExportStatus.ready
        and req.storage_key
        and (req.expires_at is None or req.expires_at)
    ):
        # 24h presigned URL — short enough to be re-issued cheaply.
        download_url = await presigned_get_url(
            req.storage_key, expires_in=24 * 3600
        )

    return ExportRequestOut(
        id=req.id,
        organization_id=req.organization_id,
        status=req.status,
        scope=req.scope,
        storage_key=req.storage_key,
        error_message=req.error_message,
        expires_at=req.expires_at.isoformat() if req.expires_at else None,
        download_url=download_url,
        created_at=req.created_at.isoformat(),
        completed_at=req.completed_at.isoformat() if req.completed_at else None,
    )


__all__ = ["router"]
