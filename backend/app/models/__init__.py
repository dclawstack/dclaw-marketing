"""Model registry — every model class is imported here so Base.metadata
sees them all for alembic --autogenerate and the test-db fixture.
"""

from app.models.user import User
from app.models.organization import Organization, OrganizationMembership, OrganizationRole
from app.models.project import Project, ProjectMembership, ProjectStatus
from app.models.campaign import Campaign, CampaignType, CampaignStatus
from app.models.invoice import Invoice, InvoiceLineItem, InvoiceStatus
from app.models.lead import (
    Lead,
    LeadActivity,
    LeadActivityKind,
    LeadNote,
    LeadStage,
    LeadStatus,
)
from app.models.analytics_event import AnalyticsEvent, EventType
from app.models.job import Job, JobStatus
from app.models.asset import Asset, AssetKind, AssetStatus
from app.models.audit_event import AuditActorKind, AuditEvent, AuditResult
from app.models.approval_request import ApprovalRequest, ApprovalStatus
from app.models.brand_kit import BrandKit, Persona
from app.models.brand_kit_insight import BrandKitInsight, BrandKitInsightKind
from app.models.ingestion import (
    DocumentChunk,
    IngestionSource,
    IngestionSourceType,
    IngestionStatus,
)
from app.models.connection import Connection, ConnectionStatus
from app.models.model_registry import (
    Capability,
    HealthStatus,
    ModelEntry,
    ModelProvider,
    ProviderType,
)
from app.models.email_event import EmailEvent, EmailEventKind, EmailEventProvider
from app.models.sequence_membership import (
    SequenceMembership,
    SequenceMembershipStatus,
)
from app.models.webhook import (
    Automation,
    AutomationAction,
    Webhook,
    WebhookEvent,
    WebhookEventStatus,
)
from app.models.social_account import (
    ProjectSocialAccount,
    SocialAccount,
    SocialAccountStatus,
    SocialPlatform,
)
from app.models.scheduled_post import (
    ScheduledPost,
    ScheduledPostChannel,
    ScheduledPostStatus,
)
from app.models.agent_thread import (
    AgentKind,
    AgentMessage,
    AgentMessageRole,
    AgentThread,
)
from app.models.attribution import (
    AnalyticsRollup,
    AttributionModel,
    AttributionResult,
    Conversion,
    Touchpoint,
)
from app.models.email_ads import (
    AdAccount,
    AdCampaign,
    AdPlatform,
    AdSet,
    AdStatus,
    EmailCampaign,
    EmailCampaignStatus,
    EmailSequence,
    EmailSequenceStep,
    EmailTemplate,
    Segment,
    SequenceStatus,
    SequenceStepKind,
)
from app.models.ops import (
    CostLedger,
    DataExportRequest,
    DataExportStatus,
    Playbook,
    PlaybookKind,
    QuotaCounter,
    TimeEntry,
    Workflow,
    WorkflowStatus,
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
    "BrandKitInsight",
    "BrandKitInsightKind",
    "IngestionSource",
    "IngestionSourceType",
    "IngestionStatus",
    "DocumentChunk",
    "Connection",
    "ConnectionStatus",
    "EmailEvent",
    "EmailEventKind",
    "EmailEventProvider",
    "SequenceMembership",
    "SequenceMembershipStatus",
    "Webhook",
    "WebhookEvent",
    "WebhookEventStatus",
    "Automation",
    "AutomationAction",
    "SocialAccount",
    "SocialAccountStatus",
    "SocialPlatform",
    "ProjectSocialAccount",
    "ScheduledPost",
    "ScheduledPostChannel",
    "ScheduledPostStatus",
    "AgentThread",
    "AgentMessage",
    "AgentKind",
    "AgentMessageRole",
    "Touchpoint",
    "Conversion",
    "AttributionResult",
    "AttributionModel",
    "AnalyticsRollup",
    "EmailTemplate",
    "EmailCampaign",
    "EmailCampaignStatus",
    "EmailSequence",
    "EmailSequenceStep",
    "SequenceStatus",
    "SequenceStepKind",
    "AdAccount",
    "AdCampaign",
    "AdSet",
    "AdPlatform",
    "AdStatus",
    "Segment",
    "CostLedger",
    "QuotaCounter",
    "TimeEntry",
    "Workflow",
    "WorkflowStatus",
    "Playbook",
    "PlaybookKind",
    "DataExportRequest",
    "DataExportStatus",
]
