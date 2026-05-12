"""Model registry — every model class is imported here so Base.metadata
sees them all for alembic --autogenerate and the test-db fixture.
"""

from app.models.user import User
from app.models.organization import Organization, OrganizationMembership, OrganizationRole
from app.models.project import Project, ProjectMembership, ProjectStatus
from app.models.campaign import Campaign, CampaignType, CampaignStatus
from app.models.lead import Lead, LeadStatus
from app.models.analytics_event import AnalyticsEvent, EventType
from app.models.job import Job, JobStatus
from app.models.asset import Asset, AssetKind, AssetStatus
from app.models.audit_event import AuditActorKind, AuditEvent, AuditResult
from app.models.approval_request import ApprovalRequest, ApprovalStatus
from app.models.brand_kit import BrandKit, Persona
from app.models.ingestion import (
    DocumentChunk,
    IngestionSource,
    IngestionSourceType,
    IngestionStatus,
)
from app.models.social_account import (
    ProjectSocialAccount,
    SocialAccount,
    SocialAccountStatus,
    SocialPlatform,
)
from app.models.agent_thread import (
    AgentKind,
    AgentMessage,
    AgentMessageRole,
    AgentThread,
)

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
    "Job",
    "JobStatus",
    "Asset",
    "AssetKind",
    "AssetStatus",
    "AuditActorKind",
    "AuditEvent",
    "AuditResult",
    "ApprovalRequest",
    "ApprovalStatus",
    "BrandKit",
    "Persona",
    "IngestionSource",
    "IngestionSourceType",
    "IngestionStatus",
    "DocumentChunk",
    "SocialAccount",
    "SocialAccountStatus",
    "SocialPlatform",
    "ProjectSocialAccount",
    "AgentThread",
    "AgentMessage",
    "AgentKind",
    "AgentMessageRole",
]
