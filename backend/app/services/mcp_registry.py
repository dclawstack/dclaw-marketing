"""Registry of built-in MCP servers (Phase 6 / Theme D).

In v0 this is an in-code Python dict (not a DB table) — the data is
static and the seed list rarely changes. A v2.x BYO marketplace would
flip these to DB rows.

Each entry maps a stable `server_id` (snake_case) to:
- display name + category
- auth kind (oauth2 / pat / api_key / basic_auth)
- the public docs URL where you'd register an app
- the tool surface — what the agent can call once connected
"""

from __future__ import annotations

import enum
from typing import TypedDict


class IntegrationCategory(str, enum.Enum):
    social = "social"
    generation = "generation"
    dam = "dam"
    hosting = "hosting"
    crm = "crm"
    analytics = "analytics"
    cms = "cms"
    email = "email"
    ads = "ads"
    productivity = "productivity"


class IntegrationAuth(str, enum.Enum):
    oauth2 = "oauth2"
    pat = "pat"
    api_key = "api_key"
    basic_auth = "basic_auth"


class MCPServerDef(TypedDict):
    server_id: str
    name: str
    category: IntegrationCategory
    auth: IntegrationAuth
    docs_url: str
    description: str
    tools: list[str]


SERVERS: list[MCPServerDef] = [
    # ---------- Social ----------
    {
        "server_id": "x",
        "name": "X / Twitter",
        "category": IntegrationCategory.social,
        "auth": IntegrationAuth.oauth2,
        "docs_url": "https://developer.x.com/en/portal/dashboard",
        "description": "Post threads, schedule, fetch metrics.",
        "tools": ["post_tweet", "schedule_post", "fetch_metrics"],
    },
    {
        "server_id": "linkedin",
        "name": "LinkedIn",
        "category": IntegrationCategory.social,
        "auth": IntegrationAuth.oauth2,
        "docs_url": "https://www.linkedin.com/developers/",
        "description": "Personal + company-page publishing and analytics.",
        "tools": ["post_update", "schedule_post", "fetch_analytics"],
    },
    {
        "server_id": "instagram",
        "name": "Instagram (Meta Graph)",
        "category": IntegrationCategory.social,
        "auth": IntegrationAuth.oauth2,
        "docs_url": "https://developers.facebook.com/docs/instagram-api",
        "description": "Feed, reels, stories — needs a connected FB page.",
        "tools": ["post_feed", "post_reel", "post_story"],
    },
    {
        "server_id": "facebook_pages",
        "name": "Facebook Pages",
        "category": IntegrationCategory.social,
        "auth": IntegrationAuth.oauth2,
        "docs_url": "https://developers.facebook.com/docs/pages-api",
        "description": "Publish to a page; fetch reach + engagement.",
        "tools": ["post_to_page", "fetch_insights"],
    },
    {
        "server_id": "youtube",
        "name": "YouTube",
        "category": IntegrationCategory.social,
        "auth": IntegrationAuth.oauth2,
        "docs_url": "https://developers.google.com/youtube/v3",
        "description": "Upload shorts + long form; read channel analytics.",
        "tools": ["upload_video", "fetch_analytics"],
    },
    {
        "server_id": "tiktok",
        "name": "TikTok for Business",
        "category": IntegrationCategory.social,
        "auth": IntegrationAuth.oauth2,
        "docs_url": "https://business-api.tiktok.com/",
        "description": "Publish to TikTok; pull engagement.",
        "tools": ["publish_video", "fetch_analytics"],
    },
    {
        "server_id": "threads",
        "name": "Threads",
        "category": IntegrationCategory.social,
        "auth": IntegrationAuth.oauth2,
        "docs_url": "https://developers.facebook.com/docs/threads",
        "description": "Post + reply threads; fetch interactions.",
        "tools": ["post_thread", "fetch_metrics"],
    },
    {
        "server_id": "bluesky",
        "name": "Bluesky (AT Protocol)",
        "category": IntegrationCategory.social,
        "auth": IntegrationAuth.basic_auth,
        "docs_url": "https://docs.bsky.app/",
        "description": "Post + repost + fetch follows / followers.",
        "tools": ["post", "repost", "fetch_followers"],
    },
    {
        "server_id": "reddit",
        "name": "Reddit",
        "category": IntegrationCategory.social,
        "auth": IntegrationAuth.oauth2,
        "docs_url": "https://www.reddit.com/dev/api",
        "description": "Submit + comment + read karma.",
        "tools": ["submit_post", "submit_comment", "fetch_karma"],
    },
    {
        "server_id": "pinterest",
        "name": "Pinterest",
        "category": IntegrationCategory.social,
        "auth": IntegrationAuth.oauth2,
        "docs_url": "https://developers.pinterest.com/",
        "description": "Create pins; fetch board insights.",
        "tools": ["create_pin", "fetch_board_insights"],
    },
    # ---------- Generation (AI/multimedia) ----------
    {
        "server_id": "anthropic",
        "name": "Anthropic Claude",
        "category": IntegrationCategory.generation,
        "auth": IntegrationAuth.api_key,
        "docs_url": "https://console.anthropic.com/",
        "description": "Text generation via Claude.",
        "tools": ["chat", "messages", "tool_use"],
    },
    {
        "server_id": "openai",
        "name": "OpenAI",
        "category": IntegrationCategory.generation,
        "auth": IntegrationAuth.api_key,
        "docs_url": "https://platform.openai.com/",
        "description": "GPT models + embeddings + image gen.",
        "tools": ["chat", "embeddings", "images"],
    },
    {
        "server_id": "replicate",
        "name": "Replicate",
        "category": IntegrationCategory.generation,
        "auth": IntegrationAuth.api_key,
        "docs_url": "https://replicate.com/",
        "description": "Run open-source image / video / audio models.",
        "tools": ["run_model", "fetch_prediction"],
    },
    {
        "server_id": "runway",
        "name": "Runway",
        "category": IntegrationCategory.generation,
        "auth": IntegrationAuth.api_key,
        "docs_url": "https://docs.dev.runwayml.com/",
        "description": "Gen-3 video generation.",
        "tools": ["generate_video"],
    },
    {
        "server_id": "elevenlabs",
        "name": "ElevenLabs",
        "category": IntegrationCategory.generation,
        "auth": IntegrationAuth.api_key,
        "docs_url": "https://elevenlabs.io/docs",
        "description": "Voice cloning + text-to-speech.",
        "tools": ["text_to_speech", "voice_clone"],
    },
    {
        "server_id": "cartesia",
        "name": "Cartesia",
        "category": IntegrationCategory.generation,
        "auth": IntegrationAuth.api_key,
        "docs_url": "https://docs.cartesia.ai/",
        "description": "Realtime + multilingual TTS.",
        "tools": ["text_to_speech", "stream"],
    },
    {
        "server_id": "suno",
        "name": "Suno",
        "category": IntegrationCategory.generation,
        "auth": IntegrationAuth.api_key,
        "docs_url": "https://suno.com/",
        "description": "Music generation from prompts.",
        "tools": ["generate_song"],
    },
    {
        "server_id": "deepgram",
        "name": "Deepgram",
        "category": IntegrationCategory.generation,
        "auth": IntegrationAuth.api_key,
        "docs_url": "https://developers.deepgram.com/",
        "description": "Transcription + STT.",
        "tools": ["transcribe", "diarize"],
    },
    # ---------- Editing / DAM ----------
    {
        "server_id": "figma",
        "name": "Figma",
        "category": IntegrationCategory.dam,
        "auth": IntegrationAuth.oauth2,
        "docs_url": "https://www.figma.com/developers/api",
        "description": "Read files, export frames, list components.",
        "tools": ["list_files", "export_frame", "fetch_components"],
    },
    {
        "server_id": "canva",
        "name": "Canva",
        "category": IntegrationCategory.dam,
        "auth": IntegrationAuth.oauth2,
        "docs_url": "https://www.canva.dev/",
        "description": "Create designs from templates, export.",
        "tools": ["create_design", "export"],
    },
    # ---------- CRM ----------
    {
        "server_id": "hubspot",
        "name": "HubSpot",
        "category": IntegrationCategory.crm,
        "auth": IntegrationAuth.oauth2,
        "docs_url": "https://developers.hubspot.com/",
        "description": "Contacts, deals, lists, workflows.",
        "tools": ["create_contact", "update_deal", "fetch_list"],
    },
    {
        "server_id": "salesforce",
        "name": "Salesforce",
        "category": IntegrationCategory.crm,
        "auth": IntegrationAuth.oauth2,
        "docs_url": "https://developer.salesforce.com/",
        "description": "Leads, opportunities, contacts.",
        "tools": ["upsert_lead", "fetch_opportunities"],
    },
    {
        "server_id": "attio",
        "name": "Attio",
        "category": IntegrationCategory.crm,
        "auth": IntegrationAuth.pat,
        "docs_url": "https://developers.attio.com/",
        "description": "Records + relationships + lists.",
        "tools": ["upsert_record", "fetch_list"],
    },
    {
        "server_id": "apollo",
        "name": "Apollo.io",
        "category": IntegrationCategory.crm,
        "auth": IntegrationAuth.api_key,
        "docs_url": "https://docs.apollo.io/",
        "description": "Lead enrichment + contact data.",
        "tools": ["enrich_contact", "search_contacts"],
    },
    # ---------- Analytics ----------
    {
        "server_id": "ga4",
        "name": "Google Analytics 4",
        "category": IntegrationCategory.analytics,
        "auth": IntegrationAuth.oauth2,
        "docs_url": "https://developers.google.com/analytics",
        "description": "Pull traffic + conversion + attribution data.",
        "tools": ["run_report", "fetch_realtime"],
    },
    {
        "server_id": "mixpanel",
        "name": "Mixpanel",
        "category": IntegrationCategory.analytics,
        "auth": IntegrationAuth.api_key,
        "docs_url": "https://developer.mixpanel.com/",
        "description": "Events, funnels, retention.",
        "tools": ["fetch_events", "build_funnel"],
    },
    {
        "server_id": "posthog",
        "name": "PostHog",
        "category": IntegrationCategory.analytics,
        "auth": IntegrationAuth.api_key,
        "docs_url": "https://posthog.com/docs",
        "description": "Product analytics + feature flags.",
        "tools": ["fetch_events", "evaluate_flag"],
    },
    # ---------- CMS ----------
    {
        "server_id": "webflow",
        "name": "Webflow",
        "category": IntegrationCategory.cms,
        "auth": IntegrationAuth.oauth2,
        "docs_url": "https://developers.webflow.com/",
        "description": "Publish CMS items, manage sites.",
        "tools": ["create_cms_item", "publish_site"],
    },
    {
        "server_id": "wordpress",
        "name": "WordPress",
        "category": IntegrationCategory.cms,
        "auth": IntegrationAuth.basic_auth,
        "docs_url": "https://developer.wordpress.org/rest-api/",
        "description": "Create / update posts via REST API.",
        "tools": ["create_post", "update_post"],
    },
    {
        "server_id": "ghost",
        "name": "Ghost",
        "category": IntegrationCategory.cms,
        "auth": IntegrationAuth.api_key,
        "docs_url": "https://ghost.org/docs/admin-api/",
        "description": "Admin API for posts + members.",
        "tools": ["create_post", "fetch_members"],
    },
    # ---------- Email ----------
    {
        "server_id": "resend",
        "name": "Resend",
        "category": IntegrationCategory.email,
        "auth": IntegrationAuth.api_key,
        "docs_url": "https://resend.com/docs",
        "description": "Transactional email API.",
        "tools": ["send_email"],
    },
    {
        "server_id": "beehiiv",
        "name": "Beehiiv",
        "category": IntegrationCategory.email,
        "auth": IntegrationAuth.api_key,
        "docs_url": "https://developers.beehiiv.com/",
        "description": "Newsletter publishing + subscriber mgmt.",
        "tools": ["create_post", "fetch_subscribers"],
    },
    {
        "server_id": "substack",
        "name": "Substack",
        "category": IntegrationCategory.email,
        "auth": IntegrationAuth.basic_auth,
        "docs_url": "https://substack.com/",
        "description": "Email newsletter publishing (RSS-driven).",
        "tools": ["create_post"],
    },
    # ---------- Productivity ----------
    {
        "server_id": "notion",
        "name": "Notion",
        "category": IntegrationCategory.productivity,
        "auth": IntegrationAuth.oauth2,
        "docs_url": "https://developers.notion.com/",
        "description": "Read + write pages and databases.",
        "tools": ["create_page", "query_database"],
    },
    {
        "server_id": "slack",
        "name": "Slack",
        "category": IntegrationCategory.productivity,
        "auth": IntegrationAuth.oauth2,
        "docs_url": "https://api.slack.com/",
        "description": "Post messages, listen for events.",
        "tools": ["post_message", "list_channels"],
    },
    {
        "server_id": "google_drive",
        "name": "Google Drive",
        "category": IntegrationCategory.productivity,
        "auth": IntegrationAuth.oauth2,
        "docs_url": "https://developers.google.com/drive",
        "description": "Read / write files for ingestion + delivery.",
        "tools": ["list_files", "upload_file", "fetch_file"],
    },
]

SERVERS_BY_ID: dict[str, MCPServerDef] = {s["server_id"]: s for s in SERVERS}


def get(server_id: str) -> MCPServerDef | None:
    return SERVERS_BY_ID.get(server_id)
