"""Assets API — presigned-upload flow + metadata + delete.

Upload sequence (3 steps):
1. POST /assets/upload  → body: filename, mime_type, kind, organization_id
   Returns: { asset_id, presigned_put_url, expires_in }
2. Client uploads bytes via HTTP PUT to that URL.
3. POST /assets/{id}/confirm  → server runs head_object, marks Asset
   as `ready`, records size + etag.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.config import settings
from app.core.database import get_db
from app.models.asset import Asset, AssetKind, AssetStatus
from app.models.organization import OrganizationMembership
from app.models.user import User
from app.services import storage


router = APIRouter(prefix="/assets", tags=["assets"])


# ---------- schemas -----------------------------------------------------

class AssetRead(BaseModel):
    id: UUID
    organization_id: UUID | None
    created_by_user_id: UUID | None
    kind: AssetKind
    mime_type: str
    original_filename: str | None
    size_bytes: int | None
    width: int | None
    height: int | None
    duration_seconds: float | None
    bucket: str
    storage_key: str
    sha256: str | None
    status: AssetStatus

    model_config = ConfigDict(from_attributes=True)


class AssetUploadRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=512)
    mime_type: str = Field(min_length=1, max_length=255)
    kind: AssetKind
    organization_id: UUID | None = None


class AssetUploadResponse(BaseModel):
    asset: AssetRead
    presigned_put_url: str
    expires_in: int


# ---------- helpers -----------------------------------------------------

async def _user_can_use_org(
    session: AsyncSession, user: User, organization_id: UUID | None
) -> None:
    """Verify the user is a member of the named Org (or it's None or
    they're a superuser).
    """
    if organization_id is None or user.is_superuser:
        return
    result = await session.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == organization_id,
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of the requested organization.",
        )


def _extension_for(mime_type: str, filename: str | None) -> str:
    """Pull file extension from filename if available; else map mime."""
    if filename and "." in filename:
        return filename.rsplit(".", 1)[-1].lower()
    return {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/gif": "gif",
        "image/webp": "webp",
        "image/svg+xml": "svg",
        "video/mp4": "mp4",
        "video/webm": "webm",
        "audio/mpeg": "mp3",
        "audio/mp4": "m4a",
        "audio/wav": "wav",
        "application/pdf": "pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
        "text/markdown": "md",
        "text/plain": "txt",
        "text/csv": "csv",
        "application/json": "json",
        "application/zip": "zip",
    }.get(mime_type, "bin")


# ---------- routes ------------------------------------------------------

@router.post("/upload", response_model=AssetUploadResponse, status_code=status.HTTP_201_CREATED)
async def request_upload(
    body: AssetUploadRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> AssetUploadResponse:
    """Step 1 of upload: returns presigned PUT URL + Asset row in
    `uploading` status. Client uploads bytes directly to the URL.
    """
    await _user_can_use_org(session, user, body.organization_id)

    storage_key = storage.make_storage_key(
        organization_id=str(body.organization_id) if body.organization_id else None,
        kind=body.kind.value,
        extension=_extension_for(body.mime_type, body.filename),
    )

    asset = Asset(
        organization_id=body.organization_id,
        created_by_user_id=user.id,
        kind=body.kind,
        mime_type=body.mime_type,
        original_filename=body.filename,
        bucket=settings.s3_bucket,
        storage_key=storage_key,
        status=AssetStatus.uploading,
    )
    session.add(asset)
    await session.flush()
    await session.commit()
    await session.refresh(asset)

    put_url = await storage.presigned_put_url(
        storage_key, content_type=body.mime_type, expires_in=600
    )

    return AssetUploadResponse(
        asset=AssetRead.model_validate(asset),
        presigned_put_url=put_url,
        expires_in=600,
    )


@router.post("/{asset_id}/confirm", response_model=AssetRead)
async def confirm_upload(
    asset_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> Asset:
    """Step 3 of upload: HEAD the object, mark Asset ready, record size
    + sha256 (from S3's etag — note: for multipart uploads etag is not
    the MD5; for our single-PUT path it is).
    """
    asset = await session.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
    if asset.created_by_user_id != user.id and not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your upload.")

    head = await storage.head_object(asset.storage_key)
    if head is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Object not found in storage — upload may have failed.",
        )

    asset.status = AssetStatus.ready
    asset.size_bytes = head.get("size")
    # etag is hex MD5 for single-PUT uploads in S3-compatible stores;
    # post-processing pipelines may compute a real sha256 and overwrite.
    if not asset.sha256 and head.get("etag"):
        asset.sha256 = head["etag"]
    await session.flush()
    await session.commit()
    await session.refresh(asset)
    return asset


@router.get("/{asset_id}", response_model=AssetRead)
async def get_asset(
    asset_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> Asset:
    asset = await session.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
    # Access: creator, Org member, or superuser
    if user.is_superuser or asset.created_by_user_id == user.id:
        return asset
    if asset.organization_id is not None:
        result = await session.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.organization_id == asset.organization_id,
            )
        )
        if result.scalar_one_or_none() is not None:
            return asset
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to this asset.")


class PresignedDownloadResponse(BaseModel):
    presigned_get_url: str
    expires_in: int


@router.get("/{asset_id}/download", response_model=PresignedDownloadResponse)
async def get_download_url(
    asset_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> PresignedDownloadResponse:
    """Issues a short-lived presigned GET URL for the underlying bytes.
    Client should use it immediately and not store it.
    """
    # Reuse the access check from get_asset
    asset = await get_asset(asset_id, user=user, session=session)
    if asset.status != AssetStatus.ready:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Asset not ready (status={asset.status.value}).",
        )
    url = await storage.presigned_get_url(asset.storage_key, expires_in=3600)
    return PresignedDownloadResponse(presigned_get_url=url, expires_in=3600)


@router.get("", response_model=list[AssetRead])
async def list_assets(
    organization_id: UUID | None = None,
    kind: AssetKind | None = None,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
    limit: int = 50,
) -> list[Asset]:
    stmt = select(Asset).order_by(Asset.created_at.desc()).limit(limit)
    if organization_id is not None:
        await _user_can_use_org(session, user, organization_id)
        stmt = stmt.where(Asset.organization_id == organization_id)
    else:
        # No org filter — show user's own creations only (unless superuser)
        if not user.is_superuser:
            stmt = stmt.where(Asset.created_by_user_id == user.id)
    if kind is not None:
        stmt = stmt.where(Asset.kind == kind)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_asset(
    asset_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    asset = await session.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
    if asset.created_by_user_id != user.id and not user.is_superuser:
        # Org admin can also delete
        if asset.organization_id is not None:
            from app.models.organization import OrganizationRole
            result = await session.execute(
                select(OrganizationMembership).where(
                    OrganizationMembership.user_id == user.id,
                    OrganizationMembership.organization_id == asset.organization_id,
                    OrganizationMembership.role.in_(
                        (OrganizationRole.admin, OrganizationRole.manager)
                    ),
                )
            )
            if result.scalar_one_or_none() is None:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail="No delete permission."
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="No delete permission."
            )

    # Best-effort S3 delete (idempotent)
    try:
        await storage.delete_object(asset.storage_key)
    except Exception:
        pass  # don't block DB cleanup on storage hiccup

    asset.status = AssetStatus.deleted
    await session.flush()
    await session.commit()
