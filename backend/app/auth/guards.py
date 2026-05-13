"""Centralised authorization guards (Sprint 4 — two-tier admin model).

A single place for the "is this user allowed to admin this org?" check, so
every endpoint converges on the same rules and we don't get drift.

Rules:
  - Superadmin (User.is_superuser) is **implicitly an admin of every org**.
    No explicit membership row required. Orgs can never be orphaned because
    superadmin can always re-grant admin to anyone.
  - Otherwise the user must have an OrganizationMembership row with
    role == OrganizationRole.admin on the target org.

Use these dependencies as `Depends(...)` in route signatures rather than
hand-rolling the SQL in each handler.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import current_active_user
from app.core.database import get_db
from app.models.organization import (
    Organization,
    OrganizationMembership,
    OrganizationRole,
)
from app.models.user import User


async def user_is_admin_of_org(
    session: AsyncSession, user: User, organization_id: UUID
) -> bool:
    """Pure check — does `user` admin `organization_id`? Superadmin always yes."""
    if user.is_superuser:
        return True
    m = (
        await session.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.role == OrganizationRole.admin,
            )
        )
    ).scalar_one_or_none()
    return m is not None


async def user_is_member_of_org(
    session: AsyncSession, user: User, organization_id: UUID
) -> bool:
    """Pure check — is `user` a member (any role) of `organization_id`?
    Superadmin always yes (implicit membership)."""
    if user.is_superuser:
        return True
    m = (
        await session.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.organization_id == organization_id,
            )
        )
    ).scalar_one_or_none()
    return m is not None


async def require_org_admin_or_superuser(
    organization_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> User:
    """Dependency: 403 unless the caller is a superadmin OR an admin-role
    member of `organization_id`. Returns the user on success."""
    if await user_is_admin_of_org(session, user, organization_id):
        return user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Superadmin or organization admin required.",
    )


async def require_org_member_or_superuser(
    organization_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> User:
    """Dependency: 403 unless the caller is a superadmin OR any-role member
    of `organization_id`. Returns the user on success."""
    if await user_is_member_of_org(session, user, organization_id):
        return user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not a member of this organization.",
    )


async def admin_org_ids_for(
    session: AsyncSession, user: User
) -> list[UUID]:
    """Return the list of orgs this user can admin.

    - Superadmin: every Organization.id in the DB (implicit).
    - Otherwise: orgs where they have a membership with role=admin.
    """
    if user.is_superuser:
        rows = (
            await session.execute(select(Organization.id))
        ).scalars().all()
        return list(rows)
    rows = (
        await session.execute(
            select(OrganizationMembership.organization_id).where(
                OrganizationMembership.user_id == user.id,
                OrganizationMembership.role == OrganizationRole.admin,
            )
        )
    ).scalars().all()
    return list(rows)


async def ensure_not_last_admin_demotion(
    session: AsyncSession,
    organization_id: UUID,
    *,
    demoting_user_id: UUID | None = None,
    removing_user_id: UUID | None = None,
) -> None:
    """Raise 409 if the proposed change would remove the **last** explicit
    admin from the org. Superadmin's implicit membership doesn't count for
    this check — explicit org-admins are what we're preserving (rule
    explained in module docstring).

    Pass `demoting_user_id` for role-demote operations; `removing_user_id`
    for membership delete. Exactly one should be set.
    """
    target_user_id = demoting_user_id or removing_user_id
    if target_user_id is None:
        return

    admin_user_ids = (
        await session.execute(
            select(OrganizationMembership.user_id).where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.role == OrganizationRole.admin,
            )
        )
    ).scalars().all()

    remaining = [uid for uid in admin_user_ids if uid != target_user_id]
    if not remaining:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Cannot remove or demote the last explicit org admin. "
                "Assign another admin first."
            ),
        )


def ensure_not_self_superadmin_demote(actor: User, target: User) -> None:
    """Prevent a superadmin from toggling off their own is_superuser flag."""
    if actor.id == target.id and target.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A superadmin cannot revoke their own superadmin flag.",
        )


__all__ = [
    "user_is_admin_of_org",
    "user_is_member_of_org",
    "require_org_admin_or_superuser",
    "require_org_member_or_superuser",
    "admin_org_ids_for",
    "ensure_not_last_admin_demotion",
    "ensure_not_self_superadmin_demote",
]
