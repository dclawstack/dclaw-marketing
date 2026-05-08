from app.api.v1.campaigns import router as campaigns_router
from app.api.v1.leads import router as leads_router
from app.api.v1.analytics import router as analytics_router

__all__ = [
    "campaigns_router",
    "leads_router",
    "analytics_router",
]
