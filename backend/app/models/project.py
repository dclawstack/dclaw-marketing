"""Project — the working container inside an Organization.

A Project has goals, KPIs, a brief, team assignments with project-level
roles, and a chosen subset of the Org's social accounts. Campaigns live
inside Projects.
"""

import enum
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.organization import OrganizationRole


class ProjectStatus(str, enum.Enum):
    active = "active"
    paused = "paused"
    archived = "archived"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    slug: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Free-form structured goals: {"objective": "leads", "target": 500, ...}
    goals_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # SP3-20 — Kanban tasks live as a JSON blob on the project for v0.2.x.
    # Shape: {"tasks": [{"id": str, "title": str, "status": "todo|in_progress|blocked|done",
    #                   "assignee_user_id": str|null, "due_date": iso|null, "notes": str|null}]}
    kanban_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    status: Mapped[ProjectStatus] = mapped_column(
        SQLEnum(ProjectStatus), nullable=False, default=ProjectStatus.active
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="projects", lazy="selectin"
    )
    memberships: Mapped[list["ProjectMembership"]] = relationship(
        "ProjectMembership",
        back_populates="project",
        lazy="selectin",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_projects_org_slug"),
    )


class ProjectMembership(Base):
    """Per-Project role assignment for a User.

    A user can be `creatives` on Project A and `viewer` on Project B.
    Reuses OrganizationRole — same role taxonomy applies at both levels.
    Org-level Admins and Managers see every Project automatically; this
    table holds the explicit assignments for all other roles.
    """
    __tablename__ = "project_memberships"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[OrganizationRole] = mapped_column(
        SQLEnum(OrganizationRole, name="organizationrole", create_type=False),
        nullable=False,
        default=OrganizationRole.viewer,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    project: Mapped["Project"] = relationship(
        "Project", back_populates="memberships", lazy="selectin"
    )

    __table_args__ = (
        UniqueConstraint("user_id", "project_id", name="uq_project_membership_user_project"),
    )
