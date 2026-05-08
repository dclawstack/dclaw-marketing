from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.config import settings
from app.core.database import init_db, get_db
from app.api.routes import health
from app.api.v1 import campaigns_router, leads_router, analytics_router
from app.models.campaign import Campaign, CampaignStatus
from app.models.lead import Lead, LeadStatus
from app.models.analytics_event import AnalyticsEvent, EventType


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(campaigns_router, prefix="/api/v1/campaigns", tags=["campaigns"])
app.include_router(leads_router, prefix="/api/v1/leads", tags=["leads"])
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["analytics"])


@app.get("/api/v1/dashboard")
async def get_dashboard(db: AsyncSession = Depends(get_db)):
    active_result = await db.execute(
        select(func.count()).select_from(Campaign).where(Campaign.status == CampaignStatus.active)
    )
    active_campaigns = active_result.scalar() or 0

    total_leads_result = await db.execute(select(func.count()).select_from(Lead))
    total_leads = total_leads_result.scalar() or 0

    converted_result = await db.execute(
        select(func.count()).select_from(Lead).where(Lead.status == LeadStatus.converted)
    )
    converted_leads = converted_result.scalar() or 0

    conversion_rate = (converted_leads / total_leads * 100) if total_leads > 0 else 0.0

    total_spend_result = await db.execute(
        select(func.sum(AnalyticsEvent.value)).where(AnalyticsEvent.event_type == EventType.conversion)
    )
    total_spend = total_spend_result.scalar() or 0.0

    return {
        "active_campaigns": active_campaigns,
        "total_leads": total_leads,
        "conversion_rate": round(conversion_rate, 2),
        "total_spend": float(total_spend),
    }
