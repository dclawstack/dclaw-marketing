"""Organization endpoints — CRUD + membership management.

Permission model:
- Only superusers (Admin role at the app level) can create Orgs.
- An Org's members (any role) can read it.
- Only the Org's Admin or Manager can update or delete it, or manage
  its membership.
"""

import re
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user, current_superuser
from app.core.database import get_db
from app.models.organization import (
    Organization,
    OrganizationMembership,
    OrganizationRole,
)
from app.models.user import User


router = APIRouter(prefix="/orgs", tags=["orgs"])


# ---------- schemas -----------------------------------------------------

class OrganizationCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9](-?[a-z0-9])*$")
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1024)
    is_external: bool = False


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=1024)


class OrganizationRead(BaseModel):
    id: UUID
    slug: str
    name: str
    description: str | None
    is_external: bool

    class Config:
        from_attributes = True


class MembershipCreate(BaseModel):
    user_id: UUID
    role: OrganizationRole


class MembershipInviteByEmail(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    role: OrganizationRole
    full_name: str | None = Field(default=None, max_length=255)


class MembershipInviteResponse(BaseModel):
    membership: "MembershipRead"
    user_created: bool
    temp_password: str | None  # only returned when a new user was created


class MembershipUpdate(BaseModel):
    role: OrganizationRole


class MembershipRead(BaseModel):
    id: UUID
    user_id: UUID
    organization_id: UUID
    role: OrganizationRole

    class Config:
        from_attributes = True


# ---------- helpers -----------------------------------------------------

async def _require_org_role(
    session: AsyncSession,
    user: User,
    org_id: UUID,
    allowed_roles: tuple[OrganizationRole, ...],
) -> OrganizationMembership:
    """Resolve current user's membership in the Org and check role."""
    if user.is_superuser:
        # App-level admins bypass per-Org checks
        m = await session.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.organization_id == org_id,
            )
        )
        return m.scalar_one_or_none()  # may be None even for superusers

    result = await session.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == org_id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this organization.",
        )
    if membership.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role {membership.role.value} not permitted for this action.",
        )
    return membership


# ---------- routes ------------------------------------------------------

@router.post("", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
async def create_org(
    body: OrganizationCreate,
    user: User = Depends(current_superuser),  # Only Admin can create Orgs
    session: AsyncSession = Depends(get_db),
) -> Organization:
    existing = await session.execute(select(Organization).where(Organization.slug == body.slug))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Org with slug '{body.slug}' already exists.",
        )

    org = Organization(**body.model_dump())
    session.add(org)
    await session.flush()
    # The creating Admin becomes the Org's first Admin member
    session.add(
        OrganizationMembership(
            user_id=user.id, organization_id=org.id, role=OrganizationRole.admin
        )
    )
    await session.commit()
    await session.refresh(org)
    return org


@router.get("", response_model=list[OrganizationRead])
async def list_my_orgs(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> list[Organization]:
    """Returns Orgs the current user is a member of.

    Superusers see all Orgs (they can administer any).
    """
    if user.is_superuser:
        result = await session.execute(
            select(Organization).order_by(Organization.created_at.desc())
        )
        return list(result.scalars().all())

    result = await session.execute(
        select(Organization)
        .join(OrganizationMembership)
        .where(OrganizationMembership.user_id == user.id)
        .order_by(Organization.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{org_id}", response_model=OrganizationRead)
async def get_org(
    org_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> Organization:
    await _require_org_role(
        session,
        user,
        org_id,
        allowed_roles=tuple(OrganizationRole),  # any member can read
    )
    org = await session.get(Organization, org_id)
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Org not found.")
    return org


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_org(
    org_id: UUID,
    request: Request,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Permanently delete an Organization and every row that hangs off it.

    Permission: superuser OR the Org's own ``admin`` role member. The
    cascade FKs on every child model (campaigns, leads, scheduled posts,
    ingested chunks, agent threads, …) tear the dependent data down in
    one statement. The audit event we write before the delete uses
    ``organization_id=None`` so it survives the cascade — the org id is
    preserved in ``target_id`` and the payload.
    """
    org = await session.get(Organization, org_id)
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Org not found."
        )

    if not user.is_superuser:
        result = await session.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.organization_id == org_id,
            )
        )
        membership = result.scalar_one_or_none()
        if membership is None or membership.role != OrganizationRole.admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Only a superuser or the organization's own admin "
                    "can delete an organization."
                ),
            )

    from app.services.audit import write_audit_event

    await write_audit_event(
        session,
        action_type="org.delete",
        organization_id=None,
        actor_user_id=user.id,
        target_type="organization",
        target_id=str(org_id),
        payload={"slug": org.slug, "name": org.name},
        request=request,
    )

    await session.delete(org)
    await session.commit()


@router.patch("/{org_id}", response_model=OrganizationRead)
async def update_org(
    org_id: UUID,
    body: OrganizationUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> Organization:
    await _require_org_role(
        session, user, org_id,
        allowed_roles=(OrganizationRole.admin, OrganizationRole.manager),
    )
    org = await session.get(Organization, org_id)
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Org not found.")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(org, field, value)
    await session.flush()
    await session.commit()
    await session.refresh(org)
    return org


# ---------- membership routes -------------------------------------------

@router.post("/{org_id}/memberships", response_model=MembershipRead, status_code=status.HTTP_201_CREATED)
async def add_member(
    org_id: UUID,
    body: MembershipCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> OrganizationMembership:
    await _require_org_role(
        session, user, org_id,
        allowed_roles=(OrganizationRole.admin, OrganizationRole.manager),
    )

    # Verify target user exists
    target = await session.get(User, body.user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found.")

    # Check no existing membership
    existing = await session.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == body.user_id,
            OrganizationMembership.organization_id == org_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this organization.",
        )

    membership = OrganizationMembership(
        user_id=body.user_id, organization_id=org_id, role=body.role
    )
    session.add(membership)
    await session.flush()
    await session.commit()
    await session.refresh(membership)
    return membership


@router.post(
    "/{org_id}/invite",
    response_model=MembershipInviteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def invite_member_by_email(
    org_id: UUID,
    body: MembershipInviteByEmail,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> MembershipInviteResponse:
    """Find-or-create a User by email, then attach a membership.

    SP3-3 invite flow. If the user is new, returns a one-time temporary
    password the inviter can hand off out-of-band (or that the email
    transport will deliver, once wired up).
    """
    await _require_org_role(
        session, user, org_id,
        allowed_roles=(OrganizationRole.admin, OrganizationRole.manager),
    )

    email = body.email.strip().lower()
    if "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email.")

    target = (
        await session.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()

    user_created = False
    temp_password: str | None = None

    if target is None:
        import secrets
        from fastapi_users.password import PasswordHelper

        temp_password = secrets.token_urlsafe(12)
        helper = PasswordHelper()
        target = User(
            email=email,
            full_name=body.full_name,
            hashed_password=helper.hash(temp_password),
            is_active=True,
            is_verified=False,
            is_superuser=False,
        )
        session.add(target)
        await session.flush()
        user_created = True

    existing = (
        await session.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == target.id,
                OrganizationMembership.organization_id == org_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this organization.",
        )

    membership = OrganizationMembership(
        user_id=target.id, organization_id=org_id, role=body.role
    )
    session.add(membership)
    await session.flush()
    await session.commit()
    await session.refresh(membership)

    return MembershipInviteResponse(
        membership=MembershipRead.model_validate(membership),
        user_created=user_created,
        temp_password=temp_password,
    )


@router.get("/{org_id}/memberships", response_model=list[MembershipRead])
async def list_members(
    org_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> list[OrganizationMembership]:
    await _require_org_role(session, user, org_id, allowed_roles=tuple(OrganizationRole))
    result = await session.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == org_id
        )
    )
    return list(result.scalars().all())


@router.patch(
    "/{org_id}/memberships/{membership_id}",
    response_model=MembershipRead,
)
async def update_member_role(
    org_id: UUID,
    membership_id: UUID,
    body: MembershipUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> OrganizationMembership:
    await _require_org_role(
        session, user, org_id,
        allowed_roles=(OrganizationRole.admin, OrganizationRole.manager),
    )
    membership = await session.get(OrganizationMembership, membership_id)
    if membership is None or membership.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found.")
    membership.role = body.role
    await session.flush()
    await session.commit()
    await session.refresh(membership)
    return membership


@router.delete(
    "/{org_id}/memberships/{membership_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_member(
    org_id: UUID,
    membership_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    await _require_org_role(
        session, user, org_id,
        allowed_roles=(OrganizationRole.admin, OrganizationRole.manager),
    )
    membership = await session.get(OrganizationMembership, membership_id)
    if membership is None or membership.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found.")
    await session.delete(membership)
    await session.flush()
    await session.commit()


# ---------- Phase 11.5 — Sandbox / dry-run mode -----------------------


class SandboxModeRequest(BaseModel):
    enabled: bool


class SandboxModeResponse(BaseModel):
    organization_id: UUID
    sandbox_mode: bool


@router.patch("/{org_id}/sandbox-mode", response_model=SandboxModeResponse)
async def set_org_sandbox_mode(
    org_id: UUID,
    body: SandboxModeRequest,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> SandboxModeResponse:
    """Toggle sandbox / dry-run mode for an Org. Admin-only.

    When enabled, every outbound side-effect (publishers, email send)
    short-circuits to a stub. Inbound + read paths are unaffected.
    """
    await _require_org_role(
        session, user, org_id,
        allowed_roles=(OrganizationRole.admin,),
    )

    from app.services.sandbox import set_sandbox_mode  # local import to avoid cycle

    try:
        new_value = await set_sandbox_mode(session, org_id, body.enabled)
    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc),
        ) from exc

    await session.commit()
    return SandboxModeResponse(organization_id=org_id, sandbox_mode=new_value)


@router.get("/{org_id}/sandbox-mode", response_model=SandboxModeResponse)
async def get_org_sandbox_mode(
    org_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> SandboxModeResponse:
    """Read the current sandbox flag. Members can read; only admin sets."""
    await _require_org_role(
        session, user, org_id,
        allowed_roles=(
            OrganizationRole.admin,
            OrganizationRole.manager,
            OrganizationRole.reviewer,
            OrganizationRole.viewer,
        ),
    )

    from app.services.sandbox import is_sandbox_mode  # local import

    enabled = await is_sandbox_mode(session, org_id)
    return SandboxModeResponse(organization_id=org_id, sandbox_mode=enabled)
