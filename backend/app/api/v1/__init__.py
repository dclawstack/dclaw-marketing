"""v1 API router exports."""

from app.api.v1 import admin, auth, jobs, me, orgs, projects
from app.api.v1.analytics import router as analytics_router
from app.api.v1.campaigns import router as campaigns_router
from app.api.v1.leads import router as leads_router

__all__ = [
    "admin",
    "auth",
    "jobs",
    "me",
    "orgs",
    "projects",
    "campaigns_router",
    "leads_router",
    "analytics_router",
]
