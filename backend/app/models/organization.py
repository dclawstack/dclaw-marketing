"""Organization — top tier of the tenancy hierarchy.

Replaces the v2.0-plan's "Workspace" concept; GitHub-shaped. Each Org
owns its members, brand kits, social/ad accounts, MCP integrations,
default trust modes, and billing.

External clients (future) = Orgs with is_external=true; the rest of
the model is identical.
"""

import enum
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class OrganizationRole(str, enum.Enum):
    """Roles within an Organization. Same set used at Project level too
    (a user can be Manager on Org but Creatives on a specific Project).

    These are *supervision scopes* — agents do the work; humans supervise
    via their corresponding Station. See PLAN-v1.2 §v2.0 Vision §2.
    """
    admin = "admin"                      # Everything; only role that can create users
    manager = "manager"                  # Supervises Conductor; sees all Projects
    creatives = "creatives"              # Supervises Creatives Agent
    social_media_manager = "social_media_manager"
    seo_specialist = "seo_specialist"
    paid_media_specialist = "paid_media_specialist"
    reviewer = "reviewer"                # Approval-only
    analyst = "analyst"                  # Read-only across analytics
    viewer = "viewer"                    # Read-only on assigned items
    client = "client"                    # External; future portal user


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # Future: when external client agencies sign up, their Org has
    # is_external=true, which lights up the Client Portal UI surface.
    is_external: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    # Q5 — Goals & Constraints. Each is a free-form JSON blob that
    # the Conductor (and agents) pull from when planning a brief.
    # Shape suggestions live in OpenAPI docs; not strictly typed at
    # the DB level so the schema can evolve without migrations.
    goals_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    constraints_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Per-action-class autonomy posture overrides. Shape:
    # {"social_post": "hard_gate", "draft_email": "soft_gate", ...}
    # Action types not listed fall back to platform defaults
    # (see PLAN-v1.2 §v2.0 §5).
    autonomy_posture_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # SP3-16 — Landing pages stored as a JSON blob. Shape:
    # {"pages": [{"id": str, "slug": str, "title": str, "body_html": str,
    #             "published": bool, "created_at": iso, "updated_at": iso}]}
    landing_pages_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

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

    memberships: Mapped[list["OrganizationMembership"]] = relationship(
        "OrganizationMembership",
        back_populates="organization",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
    projects: Mapped[list["Project"]] = relationship(
        "Project",
        back_populates="organization",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class OrganizationMembership(Base):
    """Many-to-many: a User can belong to many Orgs, each with a role.

    Admin and Manager roles see every Project in the Org automatically.
    All other roles require explicit Project assignment via ProjectMembership.
    """
    __tablename__ = "organization_memberships"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[OrganizationRole] = mapped_column(
        SQLEnum(OrganizationRole), nullable=False, default=OrganizationRole.viewer
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="memberships", lazy="selectin"
    )

    __table_args__ = (
        UniqueConstraint("user_id", "organization_id", name="uq_org_membership_user_org"),
    )
