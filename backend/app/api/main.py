from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import health
from app.api.v1 import admin, agent_threads, agents, approvals, assets, auth, brand_insights, brand_kits, campaigns_router, leads_router, analytics_router, costs, email_send, gdpr, goals, ingest, integrations, jobs, kg, me, orgs, projects, scheduled_posts, seo, social_accounts, time_entries, webhooks_email, workflows
from app.core.config import settings
from app.core.database import get_db, init_db
from app.models.analytics_event import AnalyticsEvent, EventType
from app.models.campaign import Campaign, CampaignStatus
from app.models.lead import Lead, LeadStatus


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.observability import init_sentry, init_structured_logging

    init_sentry()
    init_structured_logging()
    await init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.2.0-rc1",
    lifespan=lifespan,
    description="DClaw Marketing — agent-driven marketing operating system",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health
app.include_router(health.router, prefix="/health", tags=["health"])

# Auth (FastAPI-Users) — login / logout / reset / verify
app.include_router(auth.router, prefix="/api/v1/auth")

# Current-user — /me, /me/password (first-login mandatory reset)
app.include_router(me.router, prefix="/api/v1")

# Admin user management — admin-only (only Admin can create users)
app.include_router(admin.router, prefix="/api/v1")

# Organizations + their memberships
app.include_router(orgs.router, prefix="/api/v1")

# Projects (under /orgs/{org_id}/projects) + their memberships
app.include_router(projects.router, prefix="/api/v1")

# Background jobs — list, get, cancel, SSE stream
app.include_router(jobs.router, prefix="/api/v1")

# Assets — presigned upload + metadata + delete
app.include_router(assets.router, prefix="/api/v1")

# Approval Inbox — Hard-gate decision queue (PLAN-v1.2 §v2.0 §5.2)
app.include_router(approvals.router, prefix="/api/v1")

# Brand Kits — per-Org versioned brand identity (Theme Q1)
app.include_router(brand_kits.router, prefix="/api/v1")

# Theme Q3 — Brand kit insights (KG write-back loop §6.2)
app.include_router(brand_insights.router, prefix="/api/v1")

# Ingestion — file/url/git/zip → text chunks (Theme Q2)
app.include_router(ingest.router, prefix="/api/v1")

# Knowledge Graph — semantic search across DocumentChunks (Theme Q3)
app.include_router(kg.router, prefix="/api/v1")

# Org goals + constraints + autonomy posture (Theme Q5)
app.include_router(goals.router, prefix="/api/v1")

# Agents — Creatives Agent (Phase 2), more agents in Phase 3
app.include_router(agents.router, prefix="/api/v1")

# Scheduled posts — calendar + dispatcher (Theme C1, Phase 4)
app.include_router(scheduled_posts.router, prefix="/api/v1")

# Phase 5 — connected publishing endpoints (Theme C2 / v2.0 §6)
app.include_router(social_accounts.router, prefix="/api/v1")

# MCP integrations — registry + per-Org Connection (Theme D / Phase 6)
app.include_router(integrations.router, prefix="/api/v1")

# Phase 9 — agent threads + messages (Conductor + role-agents)
app.include_router(agent_threads.router, prefix="/api/v1")

# Phase 7.1 — Resend email send (admin-only test send for now)
app.include_router(email_send.router, prefix="/api/v1")

# Phase 7.4 — inbound email-event webhooks (Resend / Postmark / SendGrid)
app.include_router(webhooks_email.router, prefix="/api/v1")

# Phase 11.1 — cost-ledger totals + drill-down
app.include_router(costs.router, prefix="/api/v1")

# Phase 11.4 — GDPR export request + download endpoints
app.include_router(gdpr.router, prefix="/api/v1")

# Phase 10.4 — workflow execution (DAG runner + WorkflowRun persistence)
app.include_router(workflows.router, prefix="/api/v1")

# Phase 10.5 — time tracking (TimeEntry CRUD + totals for retainer burn-down)
app.include_router(time_entries.router, prefix="/api/v1")

# Theme H — SEO Agent depth: site audit, internal-link suggester, ranking delta
app.include_router(seo.router, prefix="/api/v1")

# Legacy v1 routers (will be made Org/Project-scoped in a follow-up commit)
app.include_router(campaigns_router, prefix="/api/v1/campaigns", tags=["campaigns"])
app.include_router(leads_router, prefix="/api/v1/leads", tags=["leads"])
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["analytics"])


@app.get("/api/v1/dashboard", tags=["dashboard"])
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    """TEMPORARY: returns global aggregates. Will be Org-scoped in a
    follow-up commit once existing v1 routers are migrated to require
    organization_id + project_id.
    """
    active_result = await db.execute(
        select(func.count())
        .select_from(Campaign)
        .where(Campaign.status == CampaignStatus.active)
    )
    active_campaigns = active_result.scalar() or 0

    total_leads_result = await db.execute(select(func.count()).select_from(Lead))
    total_leads = total_leads_result.scalar() or 0

    converted_result = await db.execute(
        select(func.count()).select_from(Lead).where(Lead.status == LeadStatus.converted)
    )
    converted_leads = converted_result.scalar() or 0

    conversion_rate = (
        (converted_leads / total_leads * 100) if total_leads > 0 else 0.0
    )

    total_spend_result = await db.execute(
        select(func.sum(AnalyticsEvent.value)).where(
            AnalyticsEvent.event_type == EventType.conversion
        )
    )
    total_spend = total_spend_result.scalar() or 0.0

    return {
        "active_campaigns": active_campaigns,
        "total_leads": total_leads,
        "conversion_rate": round(conversion_rate, 2),
        "total_spend": float(total_spend),
    }
