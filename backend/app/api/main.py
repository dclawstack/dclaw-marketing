from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import health
from app.auth import current_active_user
from app.models.user import User
from app.api.v1 import admin, agent_threads, agents, analytics_router, approvals, assets, audit_events, auth, brand_insights, brand_kits, branding, campaign_analytics, campaigns_router, costs, email_send, gdpr, goals, heatmap, hooks, ingest, integrations, jobs, kg, leads_router, magic_link, me, model_providers, oauth, orgs, pages, playbooks, projects, quotas, repurpose, retainer, scheduled_posts, seo, seo_pipeline, share_tokens, social_accounts, time_entries, totp, variants, webhooks_email, webhooks_generic, workflows
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
    version="1.1.1",
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

# Phase 5.7 — OAuth start/callback for publisher accounts
app.include_router(oauth.router, prefix="/api/v1")

# MCP integrations — registry + per-Org Connection (Theme D / Phase 6)
app.include_router(integrations.router, prefix="/api/v1")

# Sprint 4 S4-M — Model Registry CRUD (providers + model entries)
app.include_router(model_providers.router, prefix="/api/v1")

# Sprint 4 S4-M7/M8/M9 — feature availability + SSE log stream + metrics
from app.api.v1 import model_observability  # noqa: E402
app.include_router(model_observability.router, prefix="/api/v1")

# Sprint 4 S4-M11/M12/M13 — model resolver + org assignments + user prefs
from app.api.v1 import model_assignments  # noqa: E402
app.include_router(model_assignments.router, prefix="/api/v1")

# Sprint 4 S4-A1/A2 — Conductor decomposition + dispatch
from app.api.v1 import conductor as conductor_api  # noqa: E402
app.include_router(conductor_api.router, prefix="/api/v1")

# Sprint 4 S4-A3/A5/A6 — generic role-agent runner + 4-eye + trace replay
from app.api.v1 import agent_runtime as agent_runtime_api  # noqa: E402
app.include_router(agent_runtime_api.router, prefix="/api/v1")

# Sprint 4 S4-D2/D6 — workflow templates catalog + clone-to-org
from app.api.v1 import workflow_templates as workflow_templates_api  # noqa: E402
app.include_router(workflow_templates_api.router, prefix="/api/v1")

# Phase 9 — agent threads + messages (Conductor + role-agents)
app.include_router(agent_threads.router, prefix="/api/v1")

# Phase 7.1 — Resend email send (admin-only test send for now)
app.include_router(email_send.router, prefix="/api/v1")

# Phase 7.4 — inbound email-event webhooks (Resend / Postmark / SendGrid)
app.include_router(webhooks_email.router, prefix="/api/v1")

# Phase 11.1 — cost-ledger totals + drill-down
app.include_router(costs.router, prefix="/api/v1")

# Phase 11 / I1 — live QuotaCounter browse for the /admin/quotas dashboard
app.include_router(quotas.router, prefix="/api/v1")

# Phase 11.4 — GDPR export request + download endpoints
app.include_router(gdpr.router, prefix="/api/v1")

# A4 follow-up — read-only audit event browser
app.include_router(audit_events.router, prefix="/api/v1")

# Theme D4 — generic webhook receiver + Automation rules
app.include_router(webhooks_generic.router, prefix="/api/v1")

# Phase 10.4 — workflow execution (DAG runner + WorkflowRun persistence)
app.include_router(workflows.router, prefix="/api/v1")

# Phase 10.5 — time tracking (TimeEntry CRUD + totals for retainer burn-down)
app.include_router(time_entries.router, prefix="/api/v1")

# Theme H — SEO Agent depth: site audit, internal-link suggester, ranking delta
app.include_router(seo.router, prefix="/api/v1")

# Theme H2 — SEO blog pipeline (keyword → outline → draft)
app.include_router(seo_pipeline.router, prefix="/api/v1")

# Theme B5 — Variant A/B Studio
app.include_router(variants.router, prefix="/api/v1")

# Theme B6 — Hook & Headline Lab
app.include_router(hooks.router, prefix="/api/v1")

# Theme F2 — Content Performance Heatmap
app.include_router(heatmap.router, prefix="/api/v1")

# Theme N — Playbook search + editor
app.include_router(playbooks.router, prefix="/api/v1")

# v0.3-prep — branding/magic-link/F1/TOTP
app.include_router(branding.router, prefix="/api/v1")

# v0.3-prep — branding/magic-link/F1/TOTP
app.include_router(magic_link.router, prefix="/api/v1")

# F1 — Per-campaign analytics drill-down
app.include_router(campaign_analytics.router, prefix="/api/v1")

# A.11.6 — TOTP 2FA
app.include_router(totp.router, prefix="/api/v1")

# SP3-22 — per-Org retainer + monthly budget burn-down
app.include_router(retainer.router, prefix="/api/v1")

# SP3-16 — Landing-page builder (Theme H1)
app.include_router(pages.router, prefix="/api/v1")


# Theme M — Signed share-token public dashboards
app.include_router(share_tokens.router, prefix="/api/v1")


# Theme B4 — Repurposing Engine
app.include_router(repurpose.router, prefix="/api/v1")

# Legacy v1 routers — Org-scoped as of Sprint 3 (PR SP3-1). Every endpoint
# requires an `organization_id` query param + caller membership in that Org.
app.include_router(campaigns_router, prefix="/api/v1/campaigns", tags=["campaigns"])
app.include_router(leads_router, prefix="/api/v1/leads", tags=["leads"])
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["analytics"])


@app.get("/api/v1/dashboard", tags=["dashboard"])
async def get_dashboard(
    organization_id: UUID,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Org-scoped dashboard aggregates (Sprint 3 multi-tenant safety fix).

    Returns active-campaign / lead-count / conversion-rate / spend aggregates
    for the given Organization. Caller must be a member (or a superuser).
    """
    # Member check (mirrors the legacy-router pattern).
    if not user.is_superuser:
        from app.models.organization import OrganizationMembership as _OM

        m = (
            await db.execute(
                select(_OM).where(
                    _OM.user_id == user.id,
                    _OM.organization_id == organization_id,
                )
            )
        ).scalar_one_or_none()
        if m is None:
            from fastapi import HTTPException

            raise HTTPException(
                status_code=403, detail="Not a member of this organization."
            )

    active_result = await db.execute(
        select(func.count())
        .select_from(Campaign)
        .where(
            Campaign.organization_id == organization_id,
            Campaign.status == CampaignStatus.active,
        )
    )
    active_campaigns = active_result.scalar() or 0

    total_leads_result = await db.execute(
        select(func.count())
        .select_from(Lead)
        .where(Lead.organization_id == organization_id)
    )
    total_leads = total_leads_result.scalar() or 0

    converted_result = await db.execute(
        select(func.count())
        .select_from(Lead)
        .where(
            Lead.organization_id == organization_id,
            Lead.status == LeadStatus.converted,
        )
    )
    converted_leads = converted_result.scalar() or 0

    conversion_rate = (
        (converted_leads / total_leads * 100) if total_leads > 0 else 0.0
    )

    total_spend_result = await db.execute(
        select(func.sum(AnalyticsEvent.value)).where(
            AnalyticsEvent.organization_id == organization_id,
            AnalyticsEvent.event_type == EventType.conversion,
        )
    )
    total_spend = total_spend_result.scalar() or 0.0

    return {
        "organization_id": str(organization_id),
        "active_campaigns": active_campaigns,
        "total_leads": total_leads,
        "conversion_rate": round(conversion_rate, 2),
        "total_spend": float(total_spend),
    }
