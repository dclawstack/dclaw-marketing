"""Model registry — every model class is imported here so Base.metadata
sees them all for alembic --autogenerate and the test-db fixture.
"""

from app.models.user import User
from app.models.organization import Organization, OrganizationMembership, OrganizationRole
from app.models.project import Project, ProjectMembership, ProjectStatus
from app.models.campaign import Campaign, CampaignType, CampaignStatus
from app.models.lead import Lead, LeadStatus
from app.models.analytics_event import AnalyticsEvent, EventType

__all__ = [
    "User",
    "Organization",
    "OrganizationMembership",
    "OrganizationRole",
    "Project",
    "ProjectMembership",
    "ProjectStatus",
    "Campaign",
    "CampaignType",
    "CampaignStatus",
    "Lead",
    "LeadStatus",
    "AnalyticsEvent",
    "EventType",
]
