"""Project endpoints — CRUD + membership management.

Mounted under /orgs/{org_id}/projects so URLs are tenanted.
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_active_user
from app.core.database import get_db
from app.models.organization import OrganizationMembership, OrganizationRole
from app.models.project import (
    Project,
    ProjectMembership,
    ProjectStatus,
)
from app.models.user import User


router = APIRouter(prefix="/orgs/{org_id}/projects", tags=["projects"])


# ---------- schemas -----------------------------------------------------

class ProjectCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9](-?[a-z0-9])*$")
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    goals_json: dict[str, Any] | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    goals_json: dict[str, Any] | None = None
    status: ProjectStatus | None = None


class ProjectRead(BaseModel):
    id: UUID
    organization_id: UUID
    slug: str
    name: str
    description: str | None
    goals_json: dict[str, Any] | None
    status: ProjectStatus

    class Config:
        from_attributes = True


class ProjectMembershipCreate(BaseModel):
    user_id: UUID
    role: OrganizationRole


class ProjectMembershipRead(BaseModel):
    id: UUID
    user_id: UUID
    project_id: UUID
    role: OrganizationRole

    class Config:
        from_attributes = True


# ---------- helpers -----------------------------------------------------

async def _user_can_manage_org(
    session: AsyncSession, user: User, org_id: UUID
) -> OrganizationMembership | None:
    """Admin / Manager at the Org level can manage all Projects within."""
    if user.is_superuser:
        return None
    result = await session.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == org_id,
            OrganizationMembership.role.in_(
                (OrganizationRole.admin, OrganizationRole.manager)
            ),
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or Manager role required to manage projects.",
        )
    return membership


async def _user_can_view_project(
    session: AsyncSession, user: User, org_id: UUID, project_id: UUID
) -> None:
    """Org admins/managers see all projects; everyone else needs an
    explicit ProjectMembership for that project.
    """
    if user.is_superuser:
        return

    org_m = await session.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == org_id,
        )
    )
    org_membership = org_m.scalar_one_or_none()
    if org_membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization.",
        )

    if org_membership.role in (OrganizationRole.admin, OrganizationRole.manager):
        return

    proj_m = await session.execute(
        select(ProjectMembership).where(
            ProjectMembership.user_id == user.id,
            ProjectMembership.project_id == project_id,
        )
    )
    if proj_m.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No access to this project.",
        )


# ---------- routes ------------------------------------------------------

@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(
    org_id: UUID,
    body: ProjectCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> Project:
    await _user_can_manage_org(session, user, org_id)

    existing = await session.execute(
        select(Project).where(
            Project.organization_id == org_id, Project.slug == body.slug
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Project with slug '{body.slug}' already exists in this org.",
        )

    project = Project(organization_id=org_id, **body.model_dump())
    session.add(project)
    await session.flush()
    await session.commit()
    await session.refresh(project)
    return project


@router.get("", response_model=list[ProjectRead])
async def list_projects(
    org_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> list[Project]:
    # Org admin / manager / superuser see all
    if user.is_superuser:
        result = await session.execute(
            select(Project).where(Project.organization_id == org_id)
        )
        return list(result.scalars().all())

    org_m_q = await session.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == user.id,
            OrganizationMembership.organization_id == org_id,
        )
    )
    org_membership = org_m_q.scalar_one_or_none()
    if org_membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization.",
        )

    if org_membership.role in (OrganizationRole.admin, OrganizationRole.manager):
        result = await session.execute(
            select(Project).where(Project.organization_id == org_id)
        )
        return list(result.scalars().all())

    # Other roles see only Projects they have explicit membership in
    result = await session.execute(
        select(Project)
        .join(ProjectMembership, ProjectMembership.project_id == Project.id)
        .where(
            Project.organization_id == org_id,
            ProjectMembership.user_id == user.id,
        )
    )
    return list(result.scalars().all())


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(
    org_id: UUID,
    project_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> Project:
    await _user_can_view_project(session, user, org_id, project_id)
    project = await session.get(Project, project_id)
    if project is None or project.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    return project


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(
    org_id: UUID,
    project_id: UUID,
    body: ProjectUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> Project:
    await _user_can_manage_org(session, user, org_id)
    project = await session.get(Project, project_id)
    if project is None or project.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    await session.flush()
    await session.commit()
    await session.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    org_id: UUID,
    project_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    await _user_can_manage_org(session, user, org_id)
    project = await session.get(Project, project_id)
    if project is None or project.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    await session.delete(project)
    await session.flush()
    await session.commit()


# ---------- project memberships ----------------------------------------

@router.post(
    "/{project_id}/memberships",
    response_model=ProjectMembershipRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_project_member(
    org_id: UUID,
    project_id: UUID,
    body: ProjectMembershipCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> ProjectMembership:
    await _user_can_manage_org(session, user, org_id)
    # Target user must be an Org member already
    target_org_m = await session.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.user_id == body.user_id,
            OrganizationMembership.organization_id == org_id,
        )
    )
    if target_org_m.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must be an Organization member before being assigned to a Project.",
        )

    project = await session.get(Project, project_id)
    if project is None or project.organization_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")

    membership = ProjectMembership(
        user_id=body.user_id, project_id=project_id, role=body.role
    )
    session.add(membership)
    await session.flush()
    await session.commit()
    await session.refresh(membership)
    return membership


@router.get(
    "/{project_id}/memberships",
    response_model=list[ProjectMembershipRead],
)
async def list_project_members(
    org_id: UUID,
    project_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> list[ProjectMembership]:
    await _user_can_view_project(session, user, org_id, project_id)
    result = await session.execute(
        select(ProjectMembership).where(ProjectMembership.project_id == project_id)
    )
    return list(result.scalars().all())


@router.delete(
    "/{project_id}/memberships/{membership_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_project_member(
    org_id: UUID,
    project_id: UUID,
    membership_id: UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    await _user_can_manage_org(session, user, org_id)
    m = await session.get(ProjectMembership, membership_id)
    if m is None or m.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found.")
    await session.delete(m)
    await session.flush()
    await session.commit()
