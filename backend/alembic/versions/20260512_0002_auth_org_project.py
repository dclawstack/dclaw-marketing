"""A1 — auth + Org/User/Project tables + tenant FKs on existing tables

Revision ID: 20260512_0002
Revises: 20260512_0001
Create Date: 2026-05-12

Adds the foundational tenancy layer per PLAN-v1.2 §v2.0 §2.

New tables:
- users — FastAPI-Users-managed; admins create users with temp passwords
- organizations — top tenancy tier; future external clients flip is_external
- organization_memberships — user × org with role
- projects — unit of work inside an Org
- project_memberships — user × project with role

New enums:
- organizationrole (admin / manager / creatives / smm / seo / paid_media /
  reviewer / analyst / viewer / client) — reused at both Org and Project level
- projectstatus (active / paused / archived)

Existing tables get tenancy columns:
- campaigns: + organization_id, + project_id (both NOT NULL)
- leads:     + organization_id, + project_id (both NOT NULL),
             drop the global UNIQUE on email, add composite UNIQUE
             (organization_id, email)
- analytics_events: + organization_id (NOT NULL)

For fresh installs starting from 0001 the existing tables are empty, so
NOT NULL adds are safe with no backfill. Production paths from any
populated v1.0 baseline would need a data migration step before
running this — leaving that as a TODO; v1.0.0 ships with empty tables.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260512_0002"
down_revision: Union[str, None] = "20260512_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- new enums --------------------------------------------------------
    org_role = sa.Enum(
        "admin",
        "manager",
        "creatives",
        "social_media_manager",
        "seo_specialist",
        "paid_media_specialist",
        "reviewer",
        "analyst",
        "viewer",
        "client",
        name="organizationrole",
    )
    org_role.create(op.get_bind(), checkfirst=False)

    project_status = sa.Enum("active", "paused", "archived", name="projectstatus")
    project_status.create(op.get_bind(), checkfirst=False)

    # --- users (FastAPI-Users shape) -------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(length=1024), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_superuser", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column(
            "password_reset_required",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # --- organizations ----------------------------------------------------
    op.create_table(
        "organizations",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1024), nullable=True),
        sa.Column(
            "is_external",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"])

    # --- organization_memberships ----------------------------------------
    op.create_table(
        "organization_memberships",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            sa.UUID(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.Enum(name="organizationrole", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "user_id", "organization_id", name="uq_org_membership_user_org"
        ),
    )
    op.create_index(
        "ix_organization_memberships_user_id", "organization_memberships", ["user_id"]
    )
    op.create_index(
        "ix_organization_memberships_organization_id",
        "organization_memberships",
        ["organization_id"],
    )

    # --- projects ---------------------------------------------------------
    op.create_table(
        "projects",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "organization_id",
            sa.UUID(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("slug", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("goals_json", sa.JSON(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(name="projectstatus", create_type=False),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("organization_id", "slug", name="uq_projects_org_slug"),
    )
    op.create_index("ix_projects_organization_id", "projects", ["organization_id"])

    # --- project_memberships ---------------------------------------------
    op.create_table(
        "project_memberships",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.UUID(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.Enum(name="organizationrole", create_type=False),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "user_id", "project_id", name="uq_project_membership_user_project"
        ),
    )
    op.create_index(
        "ix_project_memberships_user_id", "project_memberships", ["user_id"]
    )
    op.create_index(
        "ix_project_memberships_project_id", "project_memberships", ["project_id"]
    )

    # --- add tenancy FKs to existing tables ------------------------------
    # campaigns. NULLABLE in v1.0.0 — see model rationale. v1.1.0 will
    # tighten to NOT NULL once all routes are scoped under /orgs/{id}/...
    op.add_column(
        "campaigns",
        sa.Column(
            "organization_id",
            sa.UUID(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.add_column(
        "campaigns",
        sa.Column(
            "project_id",
            sa.UUID(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index("ix_campaigns_organization_id", "campaigns", ["organization_id"])
    op.create_index("ix_campaigns_project_id", "campaigns", ["project_id"])

    # leads — replace global UNIQUE(email) with composite UNIQUE(org_id, email).
    # NULLABLE org/project — see Campaign rationale above.
    op.drop_constraint("uq_leads_email", "leads", type_="unique")
    op.add_column(
        "leads",
        sa.Column(
            "organization_id",
            sa.UUID(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.add_column(
        "leads",
        sa.Column(
            "project_id",
            sa.UUID(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_unique_constraint(
        "uq_leads_org_email", "leads", ["organization_id", "email"]
    )
    op.create_index("ix_leads_email", "leads", ["email"])
    op.create_index("ix_leads_organization_id", "leads", ["organization_id"])
    op.create_index("ix_leads_project_id", "leads", ["project_id"])

    # analytics_events — NULLABLE in v1.0.0
    op.add_column(
        "analytics_events",
        sa.Column(
            "organization_id",
            sa.UUID(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_analytics_events_organization_id",
        "analytics_events",
        ["organization_id"],
    )


def downgrade() -> None:
    # Reverse the tenancy FKs first
    op.drop_index("ix_analytics_events_organization_id", table_name="analytics_events")
    op.drop_column("analytics_events", "organization_id")

    op.drop_index("ix_leads_project_id", table_name="leads")
    op.drop_index("ix_leads_organization_id", table_name="leads")
    op.drop_index("ix_leads_email", table_name="leads")
    op.drop_constraint("uq_leads_org_email", "leads", type_="unique")
    op.drop_column("leads", "project_id")
    op.drop_column("leads", "organization_id")
    op.create_unique_constraint("uq_leads_email", "leads", ["email"])

    op.drop_index("ix_campaigns_project_id", table_name="campaigns")
    op.drop_index("ix_campaigns_organization_id", table_name="campaigns")
    op.drop_column("campaigns", "project_id")
    op.drop_column("campaigns", "organization_id")

    # Drop tenancy tables in reverse-dependency order
    op.drop_index("ix_project_memberships_project_id", table_name="project_memberships")
    op.drop_index("ix_project_memberships_user_id", table_name="project_memberships")
    op.drop_table("project_memberships")

    op.drop_index("ix_projects_organization_id", table_name="projects")
    op.drop_table("projects")

    op.drop_index(
        "ix_organization_memberships_organization_id",
        table_name="organization_memberships",
    )
    op.drop_index(
        "ix_organization_memberships_user_id", table_name="organization_memberships"
    )
    op.drop_table("organization_memberships")

    op.drop_index("ix_organizations_slug", table_name="organizations")
    op.drop_table("organizations")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    sa.Enum(name="projectstatus").drop(op.get_bind(), checkfirst=False)
    sa.Enum(name="organizationrole").drop(op.get_bind(), checkfirst=False)
