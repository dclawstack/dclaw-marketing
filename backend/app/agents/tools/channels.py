"""Channels tools — social accounts, email sequences, ad campaigns.

External-side-effect operations (publish, send, real ad creation) are
gated: the tools return an "approval queued" receipt rather than firing
synchronously. The actual fire happens after the human approves in the
Inbox.
"""

from __future__ import annotations

from sqlalchemy import select

from app.agents.tools.registry import ToolContext, tool
from app.models.scheduled_post import ScheduledPostChannel
from app.models.social_account import SocialAccount, SocialAccountStatus


@tool(
    name="list_channels",
    description=(
        "List the social-account / channel connections for this org. "
        "Returns one row per connected social account."
    ),
    input_schema={"type": "object", "properties": {}},
    category="channels",
)
async def list_channels(ctx: ToolContext) -> dict:
    rows = (
        await ctx.session.execute(
            select(SocialAccount).where(SocialAccount.organization_id == ctx.org_id)
        )
    ).scalars().all()
    return {
        "ok": True,
        "count": len(rows),
        "items": [
            {
                "id": str(r.id),
                "platform": r.platform.value,
                "handle": r.handle,
                "status": r.status.value,
                "is_default": bool(r.is_default_for_platform),
                "last_publish_at": r.last_publish_at.isoformat()
                if r.last_publish_at
                else None,
            }
            for r in rows
        ],
    }


@tool(
    name="connect_channel",
    description=(
        "Walk the user through connecting a new social channel. Does NOT "
        "perform an OAuth handshake itself — returns a navigation hint "
        "to the /channels page where the user finishes the flow."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "platform": {
                "type": "string",
                "enum": [p.value for p in ScheduledPostChannel],
            },
        },
        "required": ["platform"],
    },
    category="channels",
)
async def connect_channel(ctx: ToolContext, *, platform: str) -> dict:
    return {
        "ok": True,
        "next_step": "open_channels_page",
        "platform": platform,
        "route": "/channels",
        "message": (
            f"Open /channels and start the {platform} OAuth flow — "
            "I'll surface the connected account here once it's live."
        ),
    }


@tool(
    name="queue_post",
    description=(
        "Alias of schedule_post for natural-language compatibility. See "
        "schedule_post — same behavior, same hard-gate."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "channel": {
                "type": "string",
                "enum": [c.value for c in ScheduledPostChannel],
            },
            "copy": {"type": "string"},
            "scheduled_at": {"type": "string"},
        },
        "required": ["channel", "copy", "scheduled_at"],
    },
    requires_approval=True,
    category="channels",
)
async def queue_post(
    ctx: ToolContext,
    *,
    channel: str,
    copy: str,
    scheduled_at: str,
) -> dict:
    from app.agents.tools.work import schedule_post
    return await schedule_post(
        ctx,
        channel=channel,
        copy=copy,
        scheduled_at=scheduled_at,
    )


# ---------------- Email ------------------------------------------------

@tool(
    name="list_email_sequences",
    description="List configured email sequences for this org. Stubbed until the email pipeline is fully live (S5+).",
    input_schema={"type": "object", "properties": {}},
    category="channels",
)
async def list_email_sequences(ctx: ToolContext) -> dict:
    return {
        "ok": True,
        "count": 0,
        "items": [],
        "note": "Email sequences inventory tool is wired but pipeline is Phase-5.",
    }


@tool(
    name="draft_email_sequence",
    description=(
        "Draft a multi-step email sequence given a topic. Returns a "
        "structured plan the user can review; nothing is sent. Real "
        "drafting requires the Creatives Agent — this tool returns a "
        "skeleton + a routing suggestion to /email."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "topic": {"type": "string"},
            "audience": {"type": "string"},
            "n_steps": {"type": "integer", "minimum": 1, "maximum": 12, "default": 4},
        },
        "required": ["topic"],
    },
    category="channels",
)
async def draft_email_sequence(
    ctx: ToolContext,
    *,
    topic: str,
    audience: str = "general",
    n_steps: int = 4,
) -> dict:
    plan = [
        {"step": i + 1, "subject": f"Step {i+1}: about {topic}", "summary": f"Draft step {i+1} content here."}
        for i in range(n_steps)
    ]
    return {
        "ok": True,
        "topic": topic,
        "audience": audience,
        "plan": plan,
        "next_step": "open_email_page",
        "route": "/email",
    }


@tool(
    name="send_email_test",
    description=(
        "Queue a single test-send of an email. HARD-GATED — does not send "
        "synchronously; routes through Approval Inbox."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "to": {"type": "string", "format": "email"},
            "subject": {"type": "string"},
            "body_markdown": {"type": "string"},
        },
        "required": ["to", "subject", "body_markdown"],
    },
    requires_approval=True,
    category="channels",
)
async def send_email_test(
    ctx: ToolContext,
    *,
    to: str,
    subject: str,
    body_markdown: str,
) -> dict:
    return {
        "ok": True,
        "queued_for_approval": True,
        "to": to,
        "subject": subject,
        "preview": body_markdown[:160],
        "message": "Queued in Approval Inbox — pending human sign-off.",
    }


# ---------------- Ads --------------------------------------------------

@tool(
    name="list_ad_campaigns",
    description="List ad campaigns. Returns rows from the campaigns table for this org.",
    input_schema={"type": "object", "properties": {}},
    category="channels",
)
async def list_ad_campaigns(ctx: ToolContext) -> dict:
    from app.models.campaign import Campaign
    rows = (
        await ctx.session.execute(
            select(Campaign).where(Campaign.organization_id == ctx.org_id)
        )
    ).scalars().all()
    return {
        "ok": True,
        "count": len(rows),
        "items": [
            {
                "id": str(r.id),
                "name": getattr(r, "name", None),
                "type": getattr(r.type, "value", None) if getattr(r, "type", None) else None,
                "status": getattr(r.status, "value", None) if getattr(r, "status", None) else None,
            }
            for r in rows
        ],
    }


@tool(
    name="create_ad_campaign",
    description=(
        "Create a NEW ad campaign in PAUSED state. Never goes live without "
        "explicit human approval — the tool returns an approval-queued "
        "receipt; the campaign is created paused and surfaced on /ads."
    ),
    input_schema={
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "platform": {"type": "string", "enum": ["meta", "linkedin", "google"]},
            "objective": {"type": "string"},
            "daily_budget_usd": {"type": "number"},
        },
        "required": ["name", "platform"],
    },
    requires_approval=True,
    category="channels",
)
async def create_ad_campaign(
    ctx: ToolContext,
    *,
    name: str,
    platform: str,
    objective: str = "awareness",
    daily_budget_usd: float = 50.0,
) -> dict:
    return {
        "ok": True,
        "queued_for_approval": True,
        "platform": platform,
        "name": name,
        "objective": objective,
        "daily_budget_usd": daily_budget_usd,
        "status": "paused",
        "message": (
            "Ad campaign blueprint queued. Will be created in PAUSED state "
            "on /ads once approved — never auto-starts."
        ),
    }
