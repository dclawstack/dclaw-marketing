"""Demo seed / reset for the landing page.

Every entity written here is scoped to a single demo Organization whose
slug is `DEMO_ORG_SLUG`, plus one loginable demo User. `reset_demo()`
deletes the demo Org (campaigns / leads / brand kit / project / membership
cascade from it via ON DELETE CASCADE) and the demo user — so even if the
flag is flipped on against a populated instance, this cannot touch real
data: the only delete predicates are the demo Org id and the demo email.

The set is intentionally small but representative of the marketing suite:
  • Organization (workspace) with goals
  • A loginable demo User (admin membership on the Org)
  • An active BrandKit (palette + voice)
  • A Project
  • A couple of Campaigns (active + draft)
  • A handful of Leads across funnel stages

----------------------------------------------------------------------
TO REMOVE THE DEMO FEATURE, delete these three things:
  1. app/api/v1/demo.py          (the router)
  2. app/services/demo.py        (this file)
  3. The demo router registration in app/api/main.py
     (and the demo_user_*/enable_demo_mode settings in core/config.py)
----------------------------------------------------------------------
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from fastapi_users.password import PasswordHelper
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.brand_kit import BrandKit
from app.models.campaign import Campaign, CampaignStatus, CampaignType
from app.models.lead import Lead, LeadStage, LeadStatus
from app.models.organization import (
    Organization,
    OrganizationMembership,
    OrganizationRole,
)
from app.models.project import Project, ProjectStatus
from app.models.user import User

DEMO_ORG_SLUG = "demo-acme"
DEMO_USER_SLUG = "u-demo-000000"


@dataclass
class DemoCredentials:
    email: str
    password: str
    name: str


@dataclass
class DemoStatus:
    enabled: bool
    seeded: bool
    organization_id: str | None
    counts: dict[str, int]
    credentials: DemoCredentials | None = None


async def _find_org(db: AsyncSession) -> Organization | None:
    return (
        await db.execute(
            select(Organization).where(Organization.slug == DEMO_ORG_SLUG)
        )
    ).scalar_one_or_none()


async def gather_status(db: AsyncSession, *, enabled: bool) -> DemoStatus:
    org = await _find_org(db)
    if org is None:
        return DemoStatus(
            enabled=enabled, seeded=False, organization_id=None, counts={}
        )
    counts = {
        "organizations": 1,
        "brand_kits": len(
            (
                await db.execute(
                    select(BrandKit.id).where(BrandKit.organization_id == org.id)
                )
            ).all()
        ),
        "projects": len(
            (
                await db.execute(
                    select(Project.id).where(Project.organization_id == org.id)
                )
            ).all()
        ),
        "campaigns": len(
            (
                await db.execute(
                    select(Campaign.id).where(Campaign.organization_id == org.id)
                )
            ).all()
        ),
        "leads": len(
            (
                await db.execute(
                    select(Lead.id).where(Lead.organization_id == org.id)
                )
            ).all()
        ),
    }
    return DemoStatus(
        enabled=enabled,
        seeded=True,
        organization_id=str(org.id),
        counts=counts,
    )


async def seed_demo(db: AsyncSession) -> DemoStatus:
    """Idempotent: if the demo Org already exists, wipe + reseed."""
    await reset_demo(db)
    now = datetime.now(timezone.utc)

    # ── Demo user (so the landing can auto-log-in) ──────────────────────
    helper = PasswordHelper()
    demo_user = User(
        email=settings.demo_user_email.lower(),
        hashed_password=helper.hash(settings.demo_user_password),
        full_name=settings.demo_user_name,
        is_active=True,
        is_verified=True,
        is_superuser=False,
        password_reset_required=False,
        slug=DEMO_USER_SLUG,
    )
    db.add(demo_user)
    await db.flush()

    # ── Organization (workspace) ────────────────────────────────────────
    org = Organization(
        slug=DEMO_ORG_SLUG,
        name="Acme Demo Co.",
        description="A sample workspace showcasing the DClaw Marketing suite.",
        goals_json={
            "primary": "Grow qualified pipeline 30% this quarter",
            "icp": "B2B SaaS revenue leaders, 50-500 employees",
        },
        constraints_json={"monthly_budget_usd": 15000},
    )
    db.add(org)
    await db.flush()

    # Demo user is an admin of the demo Org.
    db.add(
        OrganizationMembership(
            user_id=demo_user.id,
            organization_id=org.id,
            role=OrganizationRole.admin,
        )
    )

    # ── Brand kit (active) ──────────────────────────────────────────────
    db.add(
        BrandKit(
            organization_id=org.id,
            name="Acme Brand Kit",
            description="Primary brand identity for Acme Demo Co.",
            is_active=True,
            palette_json={
                "primary": "#6D28D9",
                "secondary": "#0EA5E9",
                "neutral": "#0F172A",
            },
            voice_json={
                "tone": ["confident", "helpful", "concise"],
                "do_say": ["pipeline", "outcomes", "measurable"],
                "dont_say": ["synergy", "disrupt", "guru"],
            },
            positioning_json={
                "tagline": "Marketing on autopilot, supervised by you.",
            },
            created_by_user_id=demo_user.id,
        )
    )

    # ── Project ─────────────────────────────────────────────────────────
    project = Project(
        organization_id=org.id,
        slug="q3-growth",
        name="Q3 Growth Push",
        description="Demand-gen sprint targeting RevOps leaders.",
        status=ProjectStatus.active,
        goals_json={"target_mqls": 200},
    )
    db.add(project)
    await db.flush()

    # ── Campaigns ───────────────────────────────────────────────────────
    camp_active = Campaign(
        organization_id=org.id,
        project_id=project.id,
        name="Launch Webinar Funnel",
        type=CampaignType.email,
        status=CampaignStatus.active,
        start_date=date.today() - timedelta(days=7),
        end_date=date.today() + timedelta(days=21),
        budget=4500.0,
        description="3-touch nurture driving signups to the product webinar.",
    )
    camp_draft = Campaign(
        organization_id=org.id,
        project_id=project.id,
        name="Retargeting — Pricing Page Visitors",
        type=CampaignType.ppc,
        status=CampaignStatus.draft,
        budget=2500.0,
        description="Paid social retargeting for warm pricing-page traffic.",
    )
    db.add_all([camp_active, camp_draft])
    await db.flush()

    # ── Leads ───────────────────────────────────────────────────────────
    lead_specs = [
        ("dana@northwind.io", "Dana", "Reyes", "Northwind", LeadStatus.qualified, LeadStage.sql, 82),
        ("sam@globex.com", "Sam", "Okafor", "Globex", LeadStatus.contacted, LeadStage.mql, 61),
        ("lee@initech.dev", "Lee", "Tan", "Initech", LeadStatus.new, LeadStage.new, 34),
        ("morgan@umbrella.co", "Morgan", "Diaz", "Umbrella", LeadStatus.converted, LeadStage.customer, 95),
        ("riley@hooli.com", "Riley", "Park", "Hooli", LeadStatus.new, LeadStage.new, 28),
    ]
    for email, first, last, company, status_, stage, score in lead_specs:
        db.add(
            Lead(
                organization_id=org.id,
                project_id=project.id,
                campaign_id=camp_active.id,
                email=email,
                first_name=first,
                last_name=last,
                company=company,
                source="demo-seed",
                status=status_,
                stage=stage,
                score=float(score),
                last_activity_at=now - timedelta(days=1),
            )
        )

    await db.commit()
    snap = await gather_status(db, enabled=True)
    snap.credentials = DemoCredentials(
        email=settings.demo_user_email,
        password=settings.demo_user_password,
        name=settings.demo_user_name,
    )
    return snap


async def reset_demo(db: AsyncSession) -> DemoStatus:
    """Delete only the demo Org (cascades its children) and the demo user."""
    org = await _find_org(db)
    if org is not None:
        # Org cascade removes memberships, projects, brand kits, campaigns,
        # and leads (all carry ON DELETE CASCADE on organization_id).
        await db.execute(delete(Organization).where(Organization.id == org.id))
    await db.execute(
        delete(User).where(User.email == settings.demo_user_email.lower())
    )
    await db.commit()
    return await gather_status(db, enabled=settings.enable_demo_mode)
