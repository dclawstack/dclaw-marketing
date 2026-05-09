# DClaw Marketing — v1.2 Feature Roadmap

> **For coding agents:** Pick features from this list, implement them fully, and update this doc with a checkmark.
> **Do NOT change the basic stack.** See `AGENTS.md` for architecture lock and brand-system rules (`frontend/src/styles/brand.css` — light mode only, Poppins, `--dk-*` tokens).

## Vision

DClaw Marketing is an **end-to-end product-marketing operating system**: one place where a small team (or one operator + AI agents) plans campaigns, generates multimedia content, schedules and publishes across every channel, talks to leads, attributes revenue, and learns. The MCP integration hub is the connective tissue — every external surface (social, ads, CRMs, analytics, drive, design, voice) plugs in as an MCP server so agents can read/write through one consistent permissioned layer.

**North star:** _from a single PRD, this app produces a launch — copy, visuals, video clips, ads, landing pages, an email sequence, a scheduled posting plan, and a closed-loop attribution view — with a human approving every external action._

## Pre-Flight Checklist — Do This First

Before implementing any v1.2 feature, verify:

- [ ] `frontend/package-lock.json` is committed after any `npm install` / dependency change
- [ ] `frontend/next-env.d.ts` exists and is committed (required for Next.js TypeScript builds)
- [ ] `frontend/.gitignore` excludes `node_modules/` and `.next/`
- [ ] `docker-compose.yml` healthchecks use `python urllib.request.urlopen()` (backend) and `wget -q --spider` (frontend)
- [ ] `frontend/Dockerfile` declares `ARG NEXT_PUBLIC_API_URL` before `RUN npm run build`
- [ ] All new UI uses `--dk-*` tokens or remapped shadcn vars — no hardcoded hex; no `dark:` variants
- [ ] All long-running jobs (generation, posting, scraping) run via background workers (Celery/RQ + Redis), NOT inline in request handlers
- [ ] Every MCP/3rd-party credential is stored encrypted in `Connection` (see model below) — NEVER in env vars per-tenant

## v1.0 Feature Inventory (Current)

- [x] Backend scaffolded: FastAPI, async SQLAlchemy 2.0, Pydantic v2, repository pattern
- [x] Models: `Lead`, `Campaign`, `AnalyticsEvent` (placeholders — extend per v1.2)
- [x] Schemas + repositories + tests for all three entities
- [x] Frontend: Next.js 14 App Router, brand-themed Tailwind, pre-built UI components
- [x] Pages: Dashboard (`/`), Campaigns (`/campaigns`), Leads (`/leads`)
- [x] Docker + docker-compose + Helm chart
- [x] Alembic migrations setup
- [x] GitHub Actions CI
- [ ] Real CRUD wired to forms (verify with `docker compose up`)
- [ ] Auth (no auth in v1.0 — add in v1.2 P0)
- [ ] Background worker (no Celery/RQ in v1.0 — add in v1.2 P0)

---

## v1.2 Roadmap

The roadmap is grouped into **9 themes**. Inside each theme, features are listed roughly in dependency order. Priorities: **P0** (must ship for v1.2), **P1** (should ship), **P2** (stretch / next-iteration seeds).

### Theme A — Platform Foundations (P0)

These unblock everything else. Build them first.

#### A1. Multi-tenant Workspaces & Auth — **P0**
**Description:** Email + Google OAuth login, per-workspace data isolation, role-based access (Owner / Editor / Reviewer / Viewer).
- **Backend:**
  - Models: `User`, `Workspace`, `Membership(role)`, `Invitation`.
  - JWT access + refresh, `Depends(current_user)` and `Depends(current_workspace)` dependencies.
  - Add `workspace_id` FK + index to every existing tenant-scoped table (`Lead`, `Campaign`, `AnalyticsEvent`, …) with `ondelete="CASCADE"`.
- **Frontend:** `/login`, `/signup`, `/invite/[token]`, workspace switcher in nav, `/settings/team`.
- **Files to touch:** `backend/app/models/{user,workspace,membership}.py`, `backend/app/api/v1/auth.py`, `frontend/src/app/(auth)/*`, `frontend/src/lib/api.ts` (attach bearer).

#### A2. Background Worker (Celery + Redis) — **P0**
**Description:** Long jobs (LLM generation, image/video render, scheduled publish, MCP polling) run async with retries and dead-letter handling.
- **Backend:** add Celery app at `backend/app/worker/`, Redis service in `docker-compose.yml`, `Job` model with status (`queued/running/succeeded/failed/canceled`), `progress`, `result_url`, `error`. `WS /api/v1/jobs/{id}/stream` for live progress.
- **Frontend:** `<JobStatus>` component (spinner + progress + retry); global toast on completion.
- **Files to touch:** `backend/app/worker/celery_app.py`, `backend/app/worker/tasks/`, `backend/app/models/job.py`, `docker-compose.yml`, `helm/templates/deployment.yaml` (worker pod).

#### A3. Object Storage Abstraction — **P0**
**Description:** S3-compatible storage (MinIO in dev, S3/R2 in prod) for generated images, video, audio, exports.
- **Backend:** `app/services/storage.py` with `put_object/get_url/delete`, presigned uploads, `Asset` model (`kind`, `mime`, `size`, `width/height/duration`, `storage_key`, `checksum_sha256`).
- **Frontend:** drag-drop upload component using presigned PUT; thumbnail grid with lazy loading.
- **Files to touch:** `backend/app/services/storage.py`, `backend/app/models/asset.py`, `frontend/src/components/upload.tsx`, `docker-compose.yml` (MinIO service).

#### A4. Audit Log + Approvals — **P0**
**Description:** Every external-facing action (publish, send email, run ad) is logged and (optionally) gated by human approval.
- **Backend:** `AuditEvent(actor, action, target_type, target_id, payload_json, ip, user_agent)`; `ApprovalRequest` with required reviewers per workspace policy.
- **Frontend:** `/inbox` showing pending approvals (Approve / Reject / Request changes); per-record activity timeline.

---

### Theme B — Content Generation Pipeline (P0)

The factory floor: brief in, multimedia assets out, with brand voice + visual consistency.

#### B1. Brand Kit & Voice Profile — **P0**
**Description:** A workspace's "design brain": logo, color tokens (mirrors `brand.css` for tenants who white-label), tone-of-voice attributes, do/don't word lists, audience personas, product positioning.
- **Backend:** `BrandKit(workspace_id, name, logo_asset_id, palette_json, fonts_json, voice_json, dont_say[], must_say[], personas[])`, `Persona(name, demo, jobs_to_be_done, fears, desires)`. Versioned: editing creates a new revision.
- **Frontend:** `/brand` editor with live preview, persona cards, voice slider (formal↔casual, witty↔technical, …).
- **Files to touch:** `backend/app/models/brand_kit.py`, `frontend/src/app/brand/page.tsx`.

#### B2. Briefs & Campaigns (extend existing `Campaign`) — **P0**
**Description:** Promote `Campaign` from "row in a table" to "container that bundles brief, hypothesis, target persona, channels, KPIs, and all generated assets."
- **Backend:** add `objective`, `hypothesis`, `target_persona_id`, `channels[]`, `kpi_json`, `start_at/end_at`, `status (draft|scheduled|live|paused|complete)` to `Campaign`. New: `Brief` (markdown + structured fields), `CampaignAsset` join.
- **Frontend:** `/campaigns/[id]` Kanban-style: Brief → Generate → Review → Schedule → Live → Report.

#### B3. Multimodal Content Generation — **P0**
**Description:** From a brief, generate text (long + short form), images, video clips, voiceover, and music in one workflow. All variants land in the campaign as draft assets.
- **Backend:**
  - `app/services/generation/` with provider adapters: `text/` (Claude, OpenAI), `image/` (Replicate / Flux / Imagen), `video/` (Runway, Veo, Sora-style providers), `voice/` (ElevenLabs, Cartesia), `music/` (Suno, Udio).
  - `GenerationRequest(brand_kit_id, brief_id, kind, prompt, params_json, status, …)` linked to `Asset`.
  - Strict adherence to `BrandKit.voice_json` + `dont_say` via system prompt + post-generation lint pass that re-runs on violations.
  - Cost tracking per request.
- **Frontend:** `/campaigns/[id]/generate` — pick kind, choose persona, write prompt or use template; live progress via WS; thumbnail wall; "regenerate variant" / "edit prompt and retry".
- **Files to touch:** `backend/app/services/generation/*`, `backend/app/api/v1/generation.py`, `frontend/src/app/campaigns/[id]/generate/page.tsx`.

#### B4. Repurposing Engine — **P0**
**Description:** One source asset (long blog, podcast episode, webinar recording, demo video) → many derivative assets (Twitter thread, LinkedIn carousel PDF, Instagram reel, YouTube shorts, TikTok hook, newsletter blurb, SEO meta title + description). Most-requested feature in the YC marketing class — "spray and atomize."
- **Backend:** `RepurposeJob(source_asset_id, targets[], status)`. For video sources: transcribe (Whisper / Deepgram), chapterize, pick high-energy segments via embedding + heuristics, render with subtitles via FFmpeg + ASS. For text sources: summarize → atomize into N variants per channel.
- **Frontend:** `/library/[asset]/repurpose` — pick targets (multi-select), preview, queue.

#### B5. Variant A/B Studio — **P1**
**Description:** Generate N copies / thumbnails / hooks for the same slot, ship them all, let real engagement pick the winner. Inspired by every growth team's manual variant table.
- **Backend:** `VariantSet(campaign_id, slot, hypothesis)`, `Variant(set_id, asset_id, weight, status)`. Hooked into the scheduler so traffic is split.
- **Frontend:** `/campaigns/[id]/ab` — variant gallery, real-time win-rate, auto-promote winner toggle.

#### B6. Hook & Headline Lab — **P1**
**Description:** Tiny tool: paste a draft, get 30 hook variants ranked by historical CTR of similar hooks across this workspace's content. Pure delight feature.

#### B7. Brand-Safe Image Editor — **P2**
**Description:** Lightweight in-app editor with brand-locked palette and font; layers, text, masks, generative inpainting via the same providers as B3.

---

### Theme C — Scheduling, Publishing & Channels (P0)

Get the asset out the door — to the right place, at the right time, in the right format.

#### C1. Calendar & Scheduler — **P0**
**Description:** Drag-drop calendar of every scheduled piece across every channel. Day / week / month views. Conflict detection (don't fire two LinkedIn posts inside 60 min). Best-time-to-post recommendations from per-channel historical engagement.
- **Backend:** `ScheduledPost(workspace_id, channel_id, asset_ids[], copy, scheduled_at, status, parent_campaign_id, tags[])`. Cron-ish Celery beat task scans `scheduled_at <= now AND status='queued'` and dispatches.
- **Frontend:** `/calendar` (FullCalendar-ish, themed) with channel-color-coded chips and "publish now" action.

#### C2. Multi-Channel Publisher — **P0**
**Description:** First-class publishing for each surface, channel-aware payload shaping (image specs, character limits, hashtag rules, link previews).
- **Channels (P0 set):** X / Twitter, LinkedIn (personal + company), Instagram (Feed + Reels + Stories), Facebook (Page), YouTube (Shorts + long), TikTok, Threads, Reddit, Pinterest, Bluesky.
- **Backend:** `Channel(workspace_id, kind, account_label, connection_id)`; per-channel publisher in `app/services/publishing/{x,linkedin,instagram,…}.py`. Rate-limit guards, exponential retry on 5xx.
- **Frontend:** `/channels` connect/disconnect, last-publish status, error history.

#### C3. Email & Newsletter — **P0**
**Description:** Send sequences (drip), broadcasts, transactional via providers.
- **Channels:** SendGrid / Resend / Postmark for transactional, Mailchimp / ConvertKit / Beehiiv / Substack for newsletter.
- **Backend:** `EmailTemplate`, `Audience`, `EmailCampaign` (one-shot), `EmailSequence` (multi-step with delays + conditions). Open / click / reply ingest via webhook.
- **Frontend:** `/email/templates`, `/email/sequences/[id]` (visual flow builder using react-flow).

#### C4. Ads Publisher — **P1**
**Description:** Push generated creatives + copy + audiences as draft ad sets to Meta Ads, Google Ads, LinkedIn Ads, TikTok Ads. Human approves and launches.
- **Backend:** `AdAccount`, `AdCampaign`, `AdSet`, `AdCreative`. Each provider in `app/services/ads/`.
- **Frontend:** `/ads` cross-platform table, budget planner, performance dashboard.

#### C5. SMS / WhatsApp — **P2**
**Description:** Twilio (SMS), WhatsApp Cloud API. Templates + 1:1 inbox.

#### C6. Push & In-App — **P2**
**Description:** OneSignal / Customer.io for push, Knock for in-app. Same scheduler, same approvals.

---

### Theme D — MCP Integration Hub (P0)

The thesis: instead of one bespoke OAuth client per integration, treat every external system as an **MCP server** and let one common runtime drive them. The user said "streamlining multiple MCP connections / integrations with multimedia platforms" — this is that.

#### D1. MCP Connection Registry — **P0**
**Description:** Add, list, test, and refresh credentials for any MCP server (built-in or BYO). Tokens stored encrypted (libsodium / `cryptography.fernet`) keyed off a workspace KMS key.
- **Backend:**
  - `Connection(workspace_id, server_id, name, kind, auth_type, encrypted_secret_blob, scopes[], status, last_health_at)`.
  - `MCPServer` registry table for built-in defaults (X, LinkedIn, Instagram, YouTube, TikTok, Notion, Drive, Figma, Linear, Slack, Stripe, HubSpot, Salesforce, Apollo, Clearbit, GA4, Mixpanel, Posthog, Webflow, WordPress, Ghost, Beehiiv, Substack, Cal, Zoom, ElevenLabs, Replicate, Runway, Suno, Cartesia, Deepgram).
  - `app/services/mcp/client.py` — async MCP client; tool-call dispatcher with retry + audit logging.
  - Permission scoping per connection: read-only vs. read-write vs. publish.
- **Frontend:** `/integrations` grid (categorized: Social, Email, Ads, CRM, Analytics, Drive/Design, AI/Multimedia, Voice/Video, Other). Connect modal walks OAuth or PAT; "test connection" button.

#### D2. Multimedia MCP Servers — **P0**
**Description:** Built-in MCP servers (or thin adapters where no first-party MCP exists yet) for the multimedia stack:
- **Generation:** Replicate, Runway, Suno, ElevenLabs, Cartesia, Deepgram, OpenAI Images, Anthropic.
- **Editing / DAM:** Figma, Adobe Express, Canva, Frame.io.
- **Hosting:** Cloudflare Stream / Mux / S3 / R2.
- **Each surface implements a small uniform tool set:** `list_assets`, `get_asset`, `generate(kind, params)`, `edit(asset_id, ops)`, `export(asset_id, format)`.
- **Backend:** `app/services/mcp/servers/{provider}.py` if we ship our own; otherwise adapter to upstream.
- **Frontend:** `/integrations/multimedia` with provider tile + "what tools are available" inspector.

#### D3. MCP Tool Marketplace (BYO server) — **P1**
**Description:** Power-user can paste an MCP server URL + auth, the runtime introspects tools, and they appear in the agent's toolbox.
- **Frontend:** `/integrations/byo` form; tool inspector shows JSON-Schemas; per-tool allow/deny.

#### D4. Webhook Hub (inbound) — **P1**
**Description:** Generic inbound webhook receiver; signed payload verification per source; map → action (e.g., "new HubSpot lead → enrich → add to nurture sequence").
- **Backend:** `Webhook(workspace_id, source, secret, last_received_at)`, `WebhookEvent`. Receiver at `/api/v1/webhooks/{token}`. `Automation` rules dispatch.

---

### Theme E — Audience, Lead & CRM (P1)

The existing `Lead` model graduates from a contact-form sink into a real audience system.

#### E1. Lead 2.0 — **P1**
**Description:** Extend `Lead` with full identity, enrichment, scoring, and lifecycle stage. Feeds segmentation, sequences, ad audiences.
- **Backend:** add `email`, `phone`, `domain`, `linkedin_url`, `enrichment_json`, `score`, `stage (new|mql|sql|customer|churned)`, `source`, `utm_*`, `last_activity_at`. New: `LeadActivity`, `LeadNote`.

#### E2. Enrichment & Identity Resolution — **P1**
**Description:** On lead creation, fan out to Apollo / Clearbit / People Data Labs (via MCP) and merge findings; deduplicate by email + domain + linkedin.
- **Backend:** `app/services/enrichment.py` with provider chain; idempotency on (workspace_id, email).

#### E3. Segments & Audiences — **P1**
**Description:** Save segments as filter expressions; sync to ad-platform Custom Audiences and email-tool lists.
- **Backend:** `Segment(workspace_id, name, filter_dsl_json)`; materialized at query-time, cached. `AudienceSync(segment_id, channel_id, last_synced_at, count)`.
- **Frontend:** segment builder with AND/OR groups, live count.

#### E4. Sequences (Outbound) — **P1**
**Description:** Multi-step outbound flows: email → wait → check open → branch → LinkedIn DM → wait → … Reuses the email/LinkedIn channel publishers + a flow engine.
- **Backend:** `Sequence`, `SequenceStep(kind, delay, channel_id, template_id, branch_conditions_json)`, `SequenceEnrollment`.

#### E5. CRM Sync — **P1**
**Description:** Two-way sync with HubSpot / Salesforce / Pipedrive / Attio via their MCP servers — writes are gated by approval.

#### E6. Attribution & Revenue Tie-Back — **P1**
**Description:** Promote `AnalyticsEvent` into a touchpoint table; first-touch + last-touch + multi-touch (linear / time-decay / Markov) attribution to closed-won amounts pulled from CRM / Stripe MCP.
- **Backend:** `Touchpoint`, `Conversion`. Daily Celery job recomputes attribution, writes `AttributionResult` rows.
- **Frontend:** `/analytics/attribution` Sankey + cohort table.

---

### Theme F — Analytics & Insights (P1)

#### F1. Unified Analytics Dashboard — **P1**
**Description:** Promote `/` into a real dashboard: per-channel reach, engagement, conversions, spend, and CAC. Drill-down into any campaign or post.
- **Backend:** `app/services/analytics/aggregator.py` — daily rollups into `AnalyticsRollup(scope, key, day, metric_json)`. Queries hit rollups, not raw events.
- **Frontend:** `/` redesigned with brand cards (using `--dk-shadow-md`, `--dk-radius-lg`), recharts-based charts themed to brand palette.

#### F2. Content Performance Heatmap — **P1**
**Description:** Hooks vs. CTR, post times vs. engagement, persona vs. conversion. Surfaces "what's working."

#### F3. Competitor Tracker — **P2**
**Description:** Add competitor handles; weekly snapshots of post volume + engagement; LLM diff narrative ("what they tested last week").

#### F4. Customer-Voice Mining — **P2**
**Description:** Pull reviews, support tickets, social mentions; cluster into themes; surface top objections, top feature requests, top "love it" quotes (which feed B3 generation).

---

### Theme G — AI Agents & Automation (P1–P2)

#### G1. Marketing Agent (chat surface) — **P1**
**Description:** A workspace-scoped chat agent with access to MCP tools and the workspace's data. Can answer ("what posts went out last week?"), draft ("write 3 LinkedIn posts about our new feature"), and act ("schedule them for Tue/Thu/Fri 9am, draft only — wait for approval"). Action-class calls go through the approval queue (A4).
- **Backend:** Anthropic Claude with the workspace's MCP toolset; conversation persisted in `AgentThread` / `AgentMessage`; "tool call → audit event → optional approval" pipeline.
- **Frontend:** docked side panel `<AgentChat>` available on every page, plus full-screen `/agent`.

#### G2. Inbox Agent (replies & DMs) — **P2**
**Description:** Drafts replies for X / LinkedIn / Instagram DMs in the brand voice; human one-click sends.

#### G3. Trend Radar — **P2**
**Description:** Daily LLM run over the workspace's industry sources (RSS, X lists, Reddit, HN, GitHub trending) producing 5 ranked content opportunities with suggested hooks.

#### G4. Comment Sentiment & Triage — **P2**
**Description:** Auto-classify incoming comments (question / complaint / praise / spam), route, and suggest replies.

#### G5. Auto-Optimizer — **P2**
**Description:** Bandit policy over Variant Sets (B5) — automatically reallocate posting weight to higher-performing variants once significance is reached.

---

### Theme H — Sites, SEO & Long-Form (P1–P2)

#### H1. Landing-Page Builder — **P1**
**Description:** Brand-locked page builder (sections + slots), publish to a workspace subdomain or push to Webflow / WordPress / Ghost via MCP. Source of truth lives in the app; the destination is a render target.
- **Backend:** `Page(workspace_id, slug, sections_json, status, published_url)`; `PageVariant` for split tests.

#### H2. SEO Blog Pipeline — **P1**
**Description:** Keyword research (via Ahrefs / SEMrush MCP) → topic cluster planner → outline → draft → editorial review → publish to CMS (Webflow / WP / Ghost / Beehiiv). Internal linking suggester.

#### H3. Topic Cluster Map — **P2**
**Description:** Visual graph (react-flow) of pillar pages, supporting articles, and gaps; one-click "generate the missing piece."

---

### Theme I — Compliance, Reliability, Polish (P1)

#### I1. Rate-Limit & Quota Manager — **P1**
**Description:** Per-channel and per-provider sliding-window quotas with circuit breaker. UI shows "Twitter: 47/300 today."

#### I2. Sandbox / Preview Mode — **P1**
**Description:** Toggle a workspace into "dry-run" — every external action is recorded but not actually fired. Demos + onboarding.

#### I3. Cost Tracking — **P1**
**Description:** Aggregate per-workspace LLM/image/video/voice provider spend; daily budgets + soft caps + hard caps.

#### I4. Export / GDPR — **P2**
**Description:** Workspace data export (zip) and right-to-delete; per-record retention policies.

---

## New Backend Models — Summary

Roughly the order to add migrations in:

1. `User`, `Workspace`, `Membership`, `Invitation` *(A1)*
2. `Job` *(A2)*
3. `Asset` *(A3)*
4. `AuditEvent`, `ApprovalRequest` *(A4)*
5. `BrandKit`, `Persona`, `Brief` *(B1, B2)*
6. Extend `Campaign` *(B2)*; add `CampaignAsset`
7. `GenerationRequest` *(B3)*; `RepurposeJob` *(B4)*
8. `VariantSet`, `Variant` *(B5)*
9. `Channel`, `ScheduledPost` *(C1, C2)*
10. `EmailTemplate`, `Audience`, `EmailCampaign`, `EmailSequence` *(C3)*; `AdAccount`, `AdCampaign`, `AdSet`, `AdCreative` *(C4)*
11. `Connection`, `MCPServer` *(D1)*; `Webhook`, `WebhookEvent` *(D4)*
12. Extend `Lead`; add `LeadActivity`, `LeadNote` *(E1)*; `Segment`, `AudienceSync` *(E3)*; `Sequence`, `SequenceStep`, `SequenceEnrollment` *(E4)*
13. `Touchpoint`, `Conversion`, `AttributionResult` *(E6)*
14. `AnalyticsRollup` *(F1)*
15. `AgentThread`, `AgentMessage` *(G1)*
16. `Page`, `PageVariant` *(H1)*

Every new table gets `workspace_id` (except `User`/`Workspace`/`MCPServer` registry), `created_at`, `updated_at`, `deleted_at` (soft delete), and an alembic revision.

## New Frontend Routes — Summary

```
/(auth)
  /login, /signup, /invite/[token]
/                              # Dashboard (F1)
/calendar                      # C1
/campaigns, /campaigns/[id], /campaigns/[id]/generate, /campaigns/[id]/ab
/library                       # All assets (A3) with filters
/library/[asset]/repurpose     # B4
/email/templates, /email/sequences, /email/sequences/[id]
/ads                           # C4
/leads, /leads/[id]            # E1
/segments, /segments/[id]      # E3
/sequences, /sequences/[id]    # E4
/analytics/attribution         # E6
/integrations                  # D1
/integrations/multimedia, /integrations/byo
/channels                      # C2
/brand                         # B1
/agent                         # G1 (also as docked panel everywhere)
/inbox                         # A4 + G2
/settings/team, /settings/billing, /settings/quotas
```

## Implementation Priority

Recommended sequencing for the next ~3 sprints:

1. **Sprint 1 — Foundations:** A1 (auth + workspaces), A2 (worker), A3 (storage), A4 (audit/approval). Migrate existing models to be `workspace_id`-scoped.
2. **Sprint 2 — Generation + Publishing core:** B1 (brand kit), B2 (campaign 2.0), B3 (text + image generation only), C1 (calendar), C2 (X + LinkedIn + Instagram only), D1 (MCP registry), D2 (Replicate + ElevenLabs + Anthropic).
3. **Sprint 3 — Loop closure:** B4 (repurposing), B5 (A/B), C3 (email), E1–E3 (lead 2.0 + enrichment + segments), F1 (dashboard), G1 (agent chat), I1–I3 (rate limits, sandbox, cost).
4. **Sprint 4+ (P1/P2 backlog):** ads, attribution, landing pages, SEO pipeline, competitor tracker, optimizer, etc.

## What "Done" Looks Like for v1.2

- An operator can sign up, connect 5+ MCP integrations, write a one-paragraph campaign brief, hit "generate," review 12 multimedia variants in their brand voice/visuals, schedule a 4-week multi-channel rollout from one calendar, get a daily dashboard of reach + engagement + leads + revenue, and let an agent draft the next week's content while they sleep — all in light mode, all on Poppins, all in DKube purple.
