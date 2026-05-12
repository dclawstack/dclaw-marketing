"""SocialAccount API — connected-publisher endpoint management.

Endpoints:
  POST   /orgs/{org_id}/social-accounts                     — manual-add (admin)
  GET    /orgs/{org_id}/social-accounts                     — list
  GET    /orgs/{org_id}/social-accounts/{id}                — get one
  PATCH  /orgs/{org_id}/social-accounts/{id}                — edit (display_name, scopes, etc.)
  POST   /orgs/{org_id}/social-accounts/{id}/set-default    — pin as default for its platform
  POST   /orgs/{org_id}/social-accounts/{id}/health-check   — re-probe
  DELETE /orgs/{org_id}/social-accounts/{id}                — revoke (soft)

OAuth start/callback flows are stubbed in v1; the manual-add flow
takes a pasted access token so the calendar dispatcher has something
to authenticate with. Real OAuth comes per-platform in Phase 5.x PRs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.organization import (
    OrganizationMembership,
    OrganizationRole,
)
from app.models.social_account import (
    SocialAccount,
    SocialAccountStatus,
    SocialPlatform,
)
from app.models.user import User


router = APIRouter(
    prefix="/orgs/{org_id}/social-accounts", tags=["social-accounts"]
)


_WRITE_ROLES: tuple[OrganizationRole, ...] = (
    OrganizationRole.admin,
    OrganizationRole.manager,
)


class SocialAccountCreate(BaseModel):
    platform: SocialPlatform
    handle: str = Field(min_length=1, max_length=255)
    display_name: str | None = None
    avatar_url: str | None = None
    interim_access_token: str | None = Field(
        default=None,
        description=(
            "Plaintext access token used by Phase-5 publisher adapters. "
            "Will be migrated to encrypted Connection rows in Phase 6."
        ),
    )
    auth_metadata_json: dict | None = None
    scopes: list[str] | None = None
    is_default_for_platform: bool = False


class SocialAccountUpdate(BaseModel):
    display_name: str | None = None
    avatar_url: str | None = None
    interim_access_token: str | None = None
    auth_metadata_json: dict | None = None
    scopes: list[str] | None = None
    status: SocialAccountStatus | None = None


class SocialAccountRead(BaseModel):
    id: UUID
    organization_id: UUID
    platform: SocialPlatform
    handle: str
    display_name: str | None
    avatar_url: str | None
    is_default_for_platform: bool
    status: SocialAccountStatus
    scopes: list[str] | None
    last_health_at: datetime | None
    last_publish_at: datetime | None
    last_error_message: str | None
    has_token: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


def _to_read(acc: SocialAccount) -> SocialAccountRead:
    return SocialAccountRead(
        id=acc.id,
        organization_id=acc.organization_id,
        platform=acc.platform,
        handle=acc.handle,
        display_name=acc.display_name,
        avatar_url=acc.avatar_url,
        is_default_for_platform=acc.is_default_for_platform,
        status=acc.status,
        scopes=acc.scopes,
        last_health_at=acc.last_health_at,
        last_publish_at=acc.last_publish_at,
        last_error_message=acc.last_error_message,
        has_token=bool(acc.access_token),
        created_at=acc.created_at,
        updated_at=acc.updated_at,
    )


async def _require_member(
    session: AsyncSession,
    user: User,
    org_id: UUID,
    *,
    write: bool = False,
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
    if write and m.role not in _WRITE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin or manager can manage social accounts.",
        )


async def _get_or_404(
    session: AsyncSession, org_id: UUID, account_id: UUID
) -> SocialAccount:
    result = await session.execute(
        select(SocialAccount).where(
            SocialAccount.id == account_id,
            SocialAccount.organization_id == org_id,
        )
    )
    a = result.scalar_one_or_none()
    if a is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Social account not found.",
        )
    return a


@router.post(
    "",
    response_model=SocialAccountRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_social_account(
    org_id: UUID,
    body: SocialAccountCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> SocialAccountRead:
    await _require_member(session, user, org_id, write=True)

    # Enforce single-default-per-platform invariant if requested.
    if body.is_default_for_platform:
        await session.execute(
            update(SocialAccount)
            .where(
                SocialAccount.organization_id == org_id,
                SocialAccount.platform == body.platform,
                SocialAccount.is_default_for_platform.is_(True),
            )
            .values(is_default_for_platform=False)
        )

    acc = SocialAccount(
        organization_id=org_id,
        platform=body.platform,
        handle=body.handle,
        display_name=body.display_name,
        avatar_url=body.avatar_url,
        access_token=body.interim_access_token,
        auth_metadata_json=body.auth_metadata_json,
        scopes=body.scopes,
        is_default_for_platform=body.is_default_for_platform,
        status=SocialAccountStatus.active,
        created_by_user_id=user.id,
    )
    session.add(acc)
    try:
        await session.commit()
    except Exception as e:
        await session.rollback()
        if "uq_social_account_org_platform_handle" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"{body.platform.value} account "
                    f"'{body.handle}' is already connected."
                ),
            )
        raise
    await session.refresh(acc)
    return _to_read(acc)


@router.get("", response_model=list[SocialAccountRead])
async def list_social_accounts(
    org_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> list[SocialAccountRead]:
    await _require_member(session, user, org_id)
    result = await session.execute(
        select(SocialAccount)
        .where(SocialAccount.organization_id == org_id)
        .order_by(SocialAccount.platform, SocialAccount.handle)
    )
    return [_to_read(a) for a in result.scalars().all()]


@router.get("/{account_id}", response_model=SocialAccountRead)
async def get_social_account(
    org_id: UUID,
    account_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> SocialAccountRead:
    await _require_member(session, user, org_id)
    a = await _get_or_404(session, org_id, account_id)
    return _to_read(a)


@router.patch("/{account_id}", response_model=SocialAccountRead)
async def update_social_account(
    org_id: UUID,
    account_id: UUID,
    body: SocialAccountUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> SocialAccountRead:
    await _require_member(session, user, org_id, write=True)
    a = await _get_or_404(session, org_id, account_id)

    data = body.model_dump(exclude_unset=True)
    if "interim_access_token" in data:
        a.access_token = data.pop("interim_access_token")
    for k, v in data.items():
        setattr(a, k, v)
    await session.commit()
    await session.refresh(a)
    return _to_read(a)


@router.post("/{account_id}/set-default", response_model=SocialAccountRead)
async def set_default(
    org_id: UUID,
    account_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> SocialAccountRead:
    await _require_member(session, user, org_id, write=True)
    a = await _get_or_404(session, org_id, account_id)

    await session.execute(
        update(SocialAccount)
        .where(
            SocialAccount.organization_id == org_id,
            SocialAccount.platform == a.platform,
        )
        .values(is_default_for_platform=False)
    )
    a.is_default_for_platform = True
    await session.commit()
    await session.refresh(a)
    return _to_read(a)


@router.post("/{account_id}/health-check", response_model=SocialAccountRead)
async def health_check(
    org_id: UUID,
    account_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> SocialAccountRead:
    """Re-probe the account.

    Phase 5 stub: just stamps last_health_at and clears the error
    message. Real probes ship per platform alongside the publisher
    adapter.
    """
    await _require_member(session, user, org_id, write=True)
    a = await _get_or_404(session, org_id, account_id)
    a.last_health_at = datetime.now(tz=timezone.utc)
    a.last_error_message = None
    if a.status == SocialAccountStatus.reauth_required:
        # Stub-mode: assume re-auth is needed; UI will surface this.
        pass
    await session.commit()
    await session.refresh(a)
    return _to_read(a)


@router.delete("/{account_id}", response_model=SocialAccountRead)
async def revoke_social_account(
    org_id: UUID,
    account_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> SocialAccountRead:
    """Soft-revoke — flip status, blank token. Keeps the row for audit."""
    await _require_member(session, user, org_id, write=True)
    a = await _get_or_404(session, org_id, account_id)
    a.status = SocialAccountStatus.revoked
    a.access_token = None
    await session.commit()
    await session.refresh(a)
    return _to_read(a)
