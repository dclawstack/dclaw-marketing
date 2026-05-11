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

---

# v2.0 Vision: The Agent-Driven Agency Platform

> **Status — forward-looking addendum.** The v1.2 sections above remain the next-up engineering commitment. This section captures the platform we're building toward: an **agent crew where humans supervise stations** rather than operate tools, capable of running a full marketing operation at agency scale. Locked in planning sessions through 2026-05-12.

## Pivot in one paragraph

The noun shifts from *tool* (humans operate it) to *crew* (agents do the work; humans supervise). Each role gets a paired AI **Agent** that operates a **Station** autonomously. A **Conductor** agent decomposes briefs and dispatches to role-Agents. Humans give minimal directives via their Station and approve gated actions in an Inbox. The MCP integration hub (Theme D) becomes the tool layer all agents speak through. The Knowledge Graph (new in Theme Q) becomes the shared memory all agents read and write.

## 1. Hierarchy — Organization → Project → Campaign → Asset

GitHub-shaped. Replaces v1.2's "Workspace" tier.

| Tier | Owns |
|---|---|
| **Organization** | Members + Brand Kits + Social/Ad accounts (multiple per platform allowed) + MCP integrations + default trust modes + autonomy posture + billing |
| **Project** | Goals, KPIs, brief, team assignments, channel *selection* (a subset of the Org's connected accounts), trust-mode overrides |
| **Campaign** | A time-boxed initiative within a Project |
| **Asset** | Output of an agent — post, image, video, blog draft, ad creative, … |

External clients become additional Orgs with `is_external=true` — no migration needed.

## 2. Identity & access

### 2.1 The reframe: roles describe supervision, not work

**Agents have roles.** Each agent is a specialist (Creatives, SMM, SEO, Paid Media, …). **Humans have supervision scopes** — which agents you oversee on which projects, what you can approve / override / change. The 10 "roles" below are scoping labels for human oversight, not job descriptions.

### 2.2 The 10 system roles (as supervision scopes)

| # | Role | Scope |
|---|---|---|
| 1 | **Admin** | Everything in the Org. Only Admin can create users, assign roles, reset passwords, revoke access, manage Org settings + billing, install integrations |
| 2 | **Manager** | Supervises the Conductor; sees all Projects in the Org; final approver for big actions; no user mgmt |
| 3 | **Creatives** | Supervises Creatives Agent (text + image + video + voice + brand assets). Wraps the former Designer/Brand Manager scope |
| 4 | **Social Media Manager** | Supervises SMM Agent. Owns Calendar; approves social posts and DM responses |
| 5 | **SEO Specialist** | Supervises SEO Agent. Approves blog drafts, internal-link plans, keyword targeting |
| 6 | **Paid Media Specialist** | Supervises Paid Media Agent. Approves ad creative and budget moves |
| 7 | **Reviewer** | Approval-only. Read + comment + approve / request changes inside assigned Projects |
| 8 | **Analyst** | Read-only across analytics; can build dashboards and request reports |
| 9 | **Viewer** | Read-only on assigned Projects |
| 10 | **Client** *(external, future)* | Lights up when `is_external=true` on an Org. Portal-restricted |

Each role is a bundle of permissions. Admin can clone any role, tweak, save as custom. Per-user overrides handle exceptions.

### 2.3 Permission model — hybrid

Module-level defaults (25 modules; one checkbox per module per role) with **resource × action** drill-down available per module for fine cases. Standard verbs: `read`, `create`, `update`, `delete`, `approve`, `publish`, `export`.

The 25 modules: Users & Roles · Organizations · Projects · Campaigns · Briefs · Brand Kits · Content Generation · Asset Library (DAM) · Calendar & Scheduling · Social Publishing · Email & Newsletter · Ads · SEO · Sites & Landing Pages · Leads & CRM · Segments & Audiences · Sequences · Analytics & Reports · Attribution · Agents · Integrations · Approvals & Inbox · Settings · Time Tracking · Client Portal *(future)*.

### 2.4 Project-based access

Two layers, GitHub-shaped:

- **Org membership** — base role on the Org. **Admin** and **Manager** see all Projects automatically. All other roles require explicit Project assignment.
- **Project assignment** — a user gets a role *on this specific project*. Same person can be `Creatives` on Project A, `Viewer` on Project B, no access to Project C.

Per-user overrides are layered on top (e.g., grant `social_post:publish` to a specific Reviewer for a specific Project).

### 2.5 Progressive tiering — don't burden small teams

| Tier | Team size | Role setup |
|---|---|---|
| **T0 — Solo** | 1 | Just Admin. No role-setup screen surfaced |
| **T1 — Small team** | 2-5 | Admin + Manager + Reviewer + Viewer |
| **T2 — Growing** | 5-20 | Add specialist supervisors as people are hired |
| **T3 — Agency scale** | 20+ or once external clients flip on | Full role grid + custom roles + per-resource overrides + Client portal |

Platform ships with T3 capability under the hood; UI progressively discloses as Org member count grows.

### 2.6 Account lifecycle — admin-only user creation

Per the agency requirement that admins (not self-signup) create users:

- Admin issues `(user_id, autogenerated_temp_password)` from the Users console.
- User's first login → mandatory password reset before any other access.
- Admin can reset password / revoke access / lock account at any time, with full audit log.
- All auth events (login, lockout, password reset, role change) recorded in the audit log.
- External SSO (Google, Microsoft, Okta, magic-link) can be added later as opt-in alongside the default flow.

## 3. Theme Q — Brand & Context Ingestion *(P0 — ships before the agents)*

The foundational theme. Until Q is set up, agents have no context to work with.

| Sub | Feature | What it does |
|---|---|---|
| **Q1** | **Brand Setup Studio** | A `claude.ai/design`-style flow: upload logo → auto-extract palette → adjust → pick fonts → tune voice sliders (formal↔casual, technical↔witty, …) → define do-say / don't-say → build personas → live preview of generated content samples. Materialized as a versioned **BrandKit** (also B1; this is the *setup UX*) |
| **Q2** | **Input Channel Hub** | Ingest from **URLs** (web crawler + sitemap walk + blog scrape), **files** (PDF / DOCX / PPTX / Markdown / images / SVG / CSV), **git repos** (clone + read README + docs + code), **zip archives** (extract + ingest). All run as Celery jobs surfaced via the `Job` model |
| **Q3** | **Knowledge Graph** | The result of Q2: a queryable graph of extracted entities (products, features, value props, customer quotes, past content, ICPs, competitor mentions) + embeddings for semantic search. **Every agent reads from and writes to this** — it is the shared memory |
| **Q4** | **Freshness & Re-ingestion** | Schedulers re-crawl URLs / re-import drives on cadence; diffs flagged in the KG; subscribed agents notified when their inputs change |
| **Q5** | **Goal & Constraint Setup** | Business objectives (leads / revenue / awareness), ICPs, channels-of-interest, brand-safety lines, monthly budgets, autonomy posture per action class. Feeds the Conductor's planning |
| **Q6** | **Project Setup Wizard** | Per-project onboarding: name + goals, inherit brand from Org (or override), choose which Org **SocialAccounts** this project uses, team assignments with project-level roles, trust mode per action type |

## 4. The agent fleet

### 4.1 The Conductor

A Manager-level agent. Given a brief + Knowledge-Graph context + budgets:

1. Decomposes into role-specific tasks
2. Dispatches to role-Agents
3. Watches dependencies and timelines
4. Escalates to a human when stuck (over budget, low confidence, conflicting signals, brand-safety question, integration failure)
5. Reports rollup status to the Manager Station

### 4.2 Role agents and Stations

Each role has a paired Agent + Station UI:

| Role | Station (human UI) | Agent does |
|---|---|---|
| **Manager** | Conductor Station — briefs in flight, retainer/budget burn-down, escalations | Conductor: decomposes, dispatches, escalates |
| **Creatives** | Studio Station — drafts wall, brand-fit reviews, "more like this" controls | Generates text + image + video + voice + brand assets; auto-revises to brand voice; A/B variants |
| **SMM** | Calendar Station — scheduled posts, channel health, DM queue | Drafts + queues + (pending approval) publishes; replies to DMs in brand voice; suggests best times |
| **SEO** | Search Station — keyword pipeline, blog calendar, ranking deltas | Researches keywords, builds outlines, drafts + publishes posts, suggests internal links |
| **Paid Media** | Spend Station — live ad sets, creative carousel, budget shifts | Generates ad creative, runs A/Bs, bandit-shifts budget, kills losers |
| **Reviewer** | Approval Inbox | Pre-filters obvious wins/losses; surfaces borderline cases for human decision |
| **Analyst** | Insights Station — live dashboards, anomaly alerts, custom report builder | Computes rollups, detects anomalies, drafts weekly narrative reports |
| **Admin** | System Console | Health watchdog, rate-limit guard, integration auto-reconnect, key rotation reminders |

### 4.3 Agent runtime — Claude Agent SDK + MCP

**Plain-language explainer for non-engineers reading this:**

- **Claude Agent SDK** is Anthropic's framework for building AI agents. For each agent we define three things: (a) a **system prompt** that gives the agent its role, personality and rules; (b) a list of **tools** it can call (e.g. `generate_image`, `post_to_x`, `search_knowledge_graph`); (c) **memory** it remembers across sessions. Agents can call other agents as sub-tasks — that's how the Conductor talks to role-Agents.
- **MCP (Model Context Protocol)** is the standard way agents talk to external systems. Every social platform, ad platform, CRM, file store, design tool, etc. is implemented as an **MCP server** that exposes tools (`post_to_linkedin(account, content)`, `search_drive(query)`, `update_hubspot_contact(id, fields)`, …). Agents call those tools through one consistent interface.
- **Why this stack vs. alternatives** (CrewAI, LangGraph, custom orchestration): native MCP support matches our Theme D plans; best-in-class tool use and memory; sub-agent patterns are first-class (Conductor → role-Agents → tools); built by Anthropic so it stays in lockstep with Claude model upgrades; less framework code to maintain.

### 4.4 Shared Knowledge Graph

Q3 is the data layer all agents read from and contribute to. Brand kits, persona profiles, past wins, past failures, performance history, content embeddings. **Org-scoped — nothing leaks between Orgs.** Agents write back insights ("LinkedIn carousels outperform single-image posts by 22% for this persona") so future runs are smarter.

### 4.5 Audit + reasoning trace

Every agent action records: timestamp, agent identity, action type, inputs used, alternatives considered, confidence score, output, who approved (or auto-approved), MCP tool calls made, total cost. Humans can replay any decision. Drives governance (compliance, post-mortems) and continuous improvement (RLHF on approval/reject signals).

## 5. Autonomy posture

### 5.1 Three trust modes (per action type)

| Mode | Default for | Mechanic |
|---|---|---|
| **Autopilot** | Internal-only (drafts, research, briefs, outlines, anomaly detection, KG updates, repurposing into drafts) | Agent acts immediately; logged in audit trail |
| **Soft gate** | Customer-facing low-risk (drafting an email body, generating an ad creative variant, suggesting a calendar slot) | Agent proposes; auto-approves after configurable timeout unless a reviewer objects |
| **Hard gate** | **All outbound posting**; sending email to >1k recipients; spending >$X on ads; brand-kit changes; granting access; integration changes | Agent prepares; human must explicitly approve before action fires |

### 5.2 The hard rule: outbound posting is always Hard-gate by default

Generation, drafting, queueing, scheduling are autopilot. **Going live on a connected account always passes through the Approval Inbox first.** Configurable per-channel per-Org (e.g., "auto-approve scheduled X posts after 4-eye review Mon-Fri 9-6"), but the default everywhere is hard-gate. *Posting is the one place where humans always remain in the loop.*

### 5.3 Resolution chain

Trust modes resolve in this order:

```
Org default → Project override → Channel override → Action-level override
```

The UI shows the resolved mode for any action before it fires.

## 6. Multi-account multi-channel publishing

### 6.1 Multi-account per platform per Org

An Org can have **N accounts on each platform**. Examples: 3 X handles, 2 LinkedIn company pages, 4 Instagram accounts, 2 YouTube channels. Each is a separate OAuth grant.

**Data model:**

```python
class SocialAccount(Base):
    id: UUID
    organization_id: UUID                # FK, indexed
    platform: SocialPlatform             # enum
    handle: str                          # e.g. "@acme_official"
    display_name: str                    # e.g. "Acme Inc — Official"
    oauth_connection_id: UUID            # FK to Connection
    is_default_for_platform: bool        # per (org, platform), at most one
    status: AccountStatus                # active | reauth_required | revoked
    scopes: list[str]
    last_health_at: datetime
    created_by: UUID                     # FK User
```

- One Org → many `SocialAccount`s; uniqueness indexed by `(organization_id, platform, handle)`
- Each Project selects a subset of the Org's `SocialAccount`s to use (via `ProjectSocialAccount` join)
- Publisher adapters always take `social_account_id`, never just `platform`
- Per-account rate-limit and quota tracking
- Per-account health monitoring + auto-reconnect prompt when tokens expire

### 6.2 Full channel coverage — v1.2 commitment

**Direct publish + schedule + analytics ingest** ship for v1.2 across every channel below.

**Short-form + professional + visual + video + community:**
X · LinkedIn (personal + company) · Instagram (Feed + Reels + Stories) · Facebook Page · YouTube (Shorts + long) · TikTok · Threads · Reddit · Pinterest · Bluesky · Mastodon · Snapchat · Telegram channels · WhatsApp Business · Discord (server announcements) · Quora

**Long-form + CMS:**
Medium · Substack · Beehiiv · Ghost · WordPress · Webflow CMS

**Audio:**
**Spotify for Podcasters**

**Backlog (P2+, added on demand):** Tumblr · Vimeo · Apple Podcasts (RSS-driven) · Lemon8 · Xiaohongshu / RED · WeChat

Each channel = a publisher adapter in `app/services/publishing/{channel}.py` + an MCP server exposing publish/schedule/analytics tools. Channel-specific content-shape rules (character limits, image specs, hashtag rules, link previews) live with the adapter.

## 7. New agency-grade themes (J–P)

The existing v1.2 themes A-I stay scoped as written above. These new themes ship on the v2.0 timeline.

| Theme | What it adds |
|---|---|
| **J. Client Operations** | Client / Org CRUD; onboarding wizard (collect brand assets, social accounts, persona, goals); per-Org retainers + budgets; per-Org approval workflows |
| **K. Project Management** | Project templates (Product Launch, SEO Refresh, Brand Revamp, Newsletter Reboot, …); Kanban + Gantt boards; task dependencies; **capacity planning** (per-user / per-agent utilization); milestones |
| **L. Time Tracking & Billing** | Time logs per task / campaign / Org; auto-rollup to retainer burn-down; invoice generation (Stripe + QuickBooks export); billable vs. non-billable |
| **M. Client Reporting** | Auto-generated weekly + monthly PDFs; scheduled email delivery; **white-label option** (per-Org logo + colors); embeddable read-only dashboard URLs |
| **N. Knowledge Base & SOPs** | Reusable prompts, briefs, processes, playbooks; AI-searchable across the Org; agents propose new SOPs derived from successful patterns |
| **O. Client Portal** *(future)* | Activates on `is_external=true`. External read + approve + comment access; activity timeline; signed file handoff; calendar sharing |
| **P. Workflow Builder** | Visual no-code chain of LLM steps + tool calls + approval gates ("on new lead from HubSpot → enrich → score → if score>80 → draft personalized intro → notify SDR"). Magic Loops / Wordware-shaped |

## 8. Y Combinator patterns folded in

Citations for our design choices. *Already covered by existing v1.2 themes are marked ★; net-new pulls are +.*

| Company | Pattern adopted | Where it lands |
|---|---|---|
| **Copy.ai / Jasper** | Template library (50+ prompt-engineered templates per channel) | + B sub-feature **B8 Templates** |
| **Letterdrop** (S21) | Sales-call → social-post pipeline (record → atomize) | + B4 (Repurposing) extension |
| **Persana AI** (W23) | AI ICP detection + personalization at scale | + E (Lead 2.0) extension |
| **Junia AI** | SEO-optimized blog with auto internal-linking | ★ H2 base case |
| **Mutiny** | Visitor-segmented landing pages (per-segment hero/CTA) | ★ H1 extension |
| **Sutro** (W24) | "Describe your page in a sentence → AI generates landing page" | + H1 extension: prompt-to-page mode |
| **Outset** (S23) | AI customer-research interviews → theme synthesis | ★ F4 extension |
| **Magic Loops / Wordware** | Visual LLM-chain workflow builder | + **P** (Workflow Builder) — new theme |
| **Cluely** (S24) | Real-time on-screen AI assist during creation | + B sub-feature ("agent watches you write") |
| **Lindy / Embra** | Workspace AI agent with cross-tool access | ★ G1 base case |
| **Decagon / Sierra** | Customer-facing AI agents | + G extension ("FAQ bot on client landing pages") |
| **Default** | RevOps automation (lead routing, scoring) | ★ E extension |
| **Crayon / Klue** | Competitive intelligence dashboards | ★ F3 base case |
| **Lovable / Bolt / v0** | NL → working landing page | + H1 extension (same as Sutro) |
| **Mintlify** | AI-generated docs / wiki | + N extension |
| **Cresta** | Real-time AI coaching for humans | + G extension ("coach reviewer's tone") |

## 9. Sequencing — from v1.2 baseline to v2.0

Six phases. Each phase = its own feature branch and one or more PRs. Per the continuous-commit rule, mid-phase commits land regularly on the feature branch.

| Phase | Scope | Outcome |
|---|---|---|
| **0. Baseline** | A0 alembic baseline migration; A1 Org/User/Auth (admin-only flow, temp password, first-login reset); A2 Celery + Redis worker; A3 S3 storage abstraction; A4 audit + approval queue | Identity, infra, governance ready |
| **1. Theme Q — Foundation** | Q1 Brand Setup Studio; Q2 Input Channel Hub; Q3 Knowledge Graph; Q4 Freshness; Q5 Goals/Constraints; Q6 Project Setup Wizard | Agents have context to work from |
| **2. Agent runtime** | Claude Agent SDK integration; Conductor shell; one role-Agent end-to-end (Creatives Agent as MVP); Approval Inbox UI; trust-mode resolver | Single agent works fully autonomously with hard-gate on outbound posting |
| **3. Full role fleet** | All remaining role-Agents (SMM, SEO, Paid Media, Analyst) + their Stations | Full crew operating |
| **4. Multi-channel publishing** | `SocialAccount` model with multi-account; all v1.2 channels live; per-channel adapters; per-account rate limits | An Org can run a multi-channel multi-account campaign at scale |
| **5. Themes J–P** | Client Operations, Project Management, Time/Billing, Reporting, Knowledge Base, Workflow Builder (Client Portal stays deferred) | Agency-grade operations |
| **6. Polish + external clients** | Theme O Client Portal, white-label, Tier-3 role UI, custom roles, custom workflows | Multi-agency / external-client tenants supported |

## 10. What "Done" Looks Like for v2.0

- A new Org admin completes Theme Q in under 30 minutes: brand kit ingested, social accounts (multiple per platform) connected, input channels (website, drive, git, file uploads) feeding the Knowledge Graph, goals + budgets set, first Project created via the wizard.
- The Conductor agent reads the Project brief, decomposes into work for Creatives + SMM + SEO + Paid Media agents, and dispatches.
- Over the next week, the role-Agents draft content, queue posts, build ad sets, draft blog posts, and surface ~30 items for human review. The supervisor at each Station spends ~15 minutes/day approving in their Inbox.
- The Analyst Agent produces a Monday-morning narrative report ("CTR on LinkedIn carousels +18% WoW driven by hook style X — recommend doubling down").
- The Manager Station shows a live dashboard of agent activity, retainer burn-down, escalations to handle, and the next week's projected schedule.
- Zero hardcoded hex anywhere; everything in DKube purple; all `--dk-*` tokens; light mode only.

---

# Appendix A: Technology Choices & Deployment Model

> **Status — locked in planning sessions through 2026-05-12.** These are the foundations every implementation PR builds on. Listed here so the doc, not chat history, is the source of truth.

## A.1 Deployment model

**The platform ships as a Helm chart + container images. Customers install onto their own existing Kubernetes cluster.** DClaw does not host the platform; the customer brings the cluster and the connecting credentials.

- Install path: `helm install dclaw-marketing dclaw/dclaw-marketing -f values.yaml`
- Container images published to **GHCR** (`ghcr.io/dclawstack/dclaw-marketing-{backend,frontend,worker}`)
- **Minimum Kubernetes version: 1.28+**
- Customers reach out to required external services from their cluster: `api.anthropic.com`, Resend, the social platform APIs, etc. Egress must be allowed.
- For local development, `docker-compose` continues as the dev setup (existing).
- One Helm install = **multi-Org per install** (a single chart deployment supports N Organizations). External-client SaaS (future) = additional installs per customer agency.

## A.2 Helm chart shape

### A.2.1 Bundled-default dependencies (overridable to external)

| Dependency | Bundled default | External override |
|---|---|---|
| **Postgres** (with `pgvector` extension) | Bitnami Postgres subchart, in-cluster StatefulSet | Set `postgres.bundled: false` + `postgres.externalUri: "postgresql+asyncpg://..."` |
| **Redis** | Bitnami Redis subchart | `redis.bundled: false` + `redis.externalUri: "redis://..."` |
| **Object storage** (S3-compatible) | MinIO subchart, in-cluster | `objectStorage.bundled: false` + `objectStorage.endpoint`, `accessKey`, `secretKey`, `bucket` |

Easiest install = zero external setup, everything in-cluster. Production customers swap to managed Postgres (AWS RDS, GCP Cloud SQL, DO Managed DB), managed Redis, and S3/R2/Spaces via values flags. Customers retain responsibility for backups + HA when they go external.

### A.2.2 TLS — dual mode

Customer picks per install:

- `tls.certManager.enabled: true` — chart creates a `Certificate` resource expecting cert-manager to be pre-installed in the cluster (most production clusters have it; auto-issues + renews via Let's Encrypt or any configured Issuer).
- `tls.existingSecret: "<secret-name>"` — chart uses a pre-created TLS Secret. Customer brings their own cert.
- Either is supported; not both at once for a given install.

### A.2.3 URL routing — path-based, single domain

One Helm install = one domain (e.g., `marketing.acme.com`). Organizations are URL-pathed: `/orgs/<slug>/projects/<id>/...`. Org selection happens after login. One TLS cert, simplest DNS setup. Subdomain-per-Org and one-install-per-Org are explicitly deferred (they fit external-client SaaS, not internal-team installs).

### A.2.4 Multi-tenant isolation

All Org data is row-level isolated via:

- `organization_id` FK column on every tenant-scoped table (indexed)
- API-layer access checks via `Depends(current_organization)` dependency
- Encrypted-at-rest tenant secrets keyed per-Org (see A.6)

No schema-per-tenant; no database-per-tenant. Single Postgres serves all Orgs in the install.

## A.3 Backend stack

| Concern | Choice |
|---|---|
| Web framework | **FastAPI** (existing) — `lifespan` handler, async everything |
| ORM | **SQLAlchemy 2.0 async** (existing) — `Mapped[]` + `mapped_column()` only; `DeclarativeBase` from `app.models.base` |
| Schemas | **Pydantic v2** (existing) — `ConfigDict(from_attributes=True)` |
| Database | **Postgres 16+ with `pgvector` extension** for the Knowledge Graph embeddings |
| Cache + broker | **Redis** |
| Background jobs | **Celery** (Redis broker) + **Celery Beat** for scheduled tasks |
| Auth | **FastAPI-Users** — JWT + refresh tokens, **admin-only user creation**, mandatory first-login password reset, Argon2 password hashing, audit-logged auth events |
| Object storage | S3-compatible (MinIO default in-cluster; S3 / R2 / Spaces in prod) via `aiobotocore` |
| Email | **Resend** API (transactional + marketing) |
| Migrations | **Alembic** — every model change ships with a revision; baseline migration captured in **A0** before further work |
| Tests | `pytest` + `pytest-asyncio==0.24.0` (pinned; do not upgrade) — already in place |

## A.4 Frontend stack

| Concern | Choice |
|---|---|
| Framework | **Next.js 14 App Router** |
| Styling | **Tailwind CSS** + `frontend/src/styles/brand.css` (DKube tokens; light-mode only; **no `dark:` variants**) |
| Type | **Poppins** loaded via `next/font/google` |
| API client | Typed fetch wrapper in `src/lib/api.ts` |
| UI primitives | Pre-built shadcn-style components in `src/components/ui/` — **DO NOT install shadcn CLI** (breaks Tailwind v3) |
| Forms | **React Hook Form** + **Zod** resolvers — add in Phase 1 when first forms land |
| State mgmt | Local React state for v2.0; add **Zustand** if/when component-tree drilling becomes painful |
| Live updates | Server-Sent Events (SSE) for agent activity streams; WebSocket only if bidirectional is needed |

## A.5 Agent runtime

| Concern | Choice |
|---|---|
| Agent framework | **Claude Agent SDK** (Anthropic-built) |
| Tool layer | **MCP (Model Context Protocol)** — every external system implements an MCP server exposing typed tools |
| LLM model routing *(default; per-action overridable)* | **Opus** for the Conductor; **Sonnet** for role-Agents; **Haiku** for fast-path routine tasks (classification, simple drafting, anomaly detection) |
| Embedding model | Decision deferred to Phase 1 (Theme Q) — candidates: OpenAI `text-embedding-3-large`, Voyage AI, Cohere |
| Memory | Per-agent state + the shared **Knowledge Graph** (Postgres + pgvector). Org-scoped — nothing leaks between Orgs |
| Audit | Every agent action + tool call recorded in `AuditEvent` with reasoning trace (timestamp, agent, action, inputs, alternatives considered, confidence, output, approver, cost) |
| Cost guardrails | Per-Org daily/monthly LLM budget caps (Theme I3); per-action confidence threshold; soft + hard caps |

## A.6 Secrets management

| Scope | Approach |
|---|---|
| Dev | `.env.local` files in `backend/` and `frontend/` — gitignored, never committed |
| CI | **GitHub Actions Secrets** for test DB URL, mock API keys |
| Prod platform secrets (Anthropic key, Resend key, DB URL, Redis URL, master KMS key) | **Kubernetes Secrets**, populated from a `.env.production` file kept outside git, applied via Helm values |
| Tenant OAuth tokens (each Org's X / LinkedIn / Instagram / etc. tokens) | **Encrypted at rest in Postgres** using `cryptography.fernet` with a per-Org data key. The per-Org key is itself encrypted with a master KMS key (env var for v2.0; stored in cluster Secret) |
| Rotation | Manual via `helm upgrade` for v2.0. Add **External Secrets Operator** backed by AWS Secrets Manager / Vault / 1Password Connect later if rotation discipline becomes a real need |

## A.7 Container images

| Image | Path | Runs |
|---|---|---|
| **Backend** (API + worker + beat) | `ghcr.io/dclawstack/dclaw-marketing-backend:<version>` | One image, three containers (uvicorn / Celery worker / Celery beat) selected by command args in their respective Deployments |
| **Frontend** | `ghcr.io/dclawstack/dclaw-marketing-frontend:<version>` | Standalone Next.js build |
| **Migrations** | Same backend image | Runs `alembic upgrade head` in a Helm `pre-install` + `pre-upgrade` Hook Job |

Image tags follow semver (`v2.0.0`, `v2.0.1`, …) with a `latest` mutable tag for development.

## A.8 Observability

| Concern | Choice |
|---|---|
| Backend logs | Structured JSON via `structlog` |
| Frontend logs | Browser console + Sentry SDK |
| Errors | **Sentry** — both backend and frontend; DSN configurable in values |
| Metrics | **OpenTelemetry** → Prometheus exporter; chart exposes `/metrics` endpoint |
| Tracing | OpenTelemetry → OTLP endpoint configurable (customer points it at Jaeger, Tempo, Datadog, Honeycomb, etc.) |
| Health endpoints | Backend `/health` (liveness) + `/ready` (readiness); frontend simple up-check |

## A.9 Versioning & release

- **Single semver line** for the platform; chart, backend image, frontend image all version-bump together.
- `main` branch always green; tags `v<major>.<minor>.<patch>` cut on every release.
- GitHub Actions workflow builds + pushes images on tag; chart published to a Helm repository (GHCR or chart-museum, TBD in Phase 0 polish).
- Customer upgrade path: `helm upgrade dclaw-marketing dclaw/dclaw-marketing --version <new>` — migrations run via the pre-upgrade Hook.

## A.10 What is explicitly deferred

These are common in mature platforms but explicitly OUT of v2.0 scope to keep the surface manageable:

- SSO / SAML / OIDC for end-user login (admin-only user creation + temp password + first-login reset is the only flow for v2.0; SSO is post-v2.0)
- Self-service signup / billing portals (this is an install-it-yourself platform; we're not collecting payments)
- Per-tenant database isolation (row-level only in v2.0)
- External Secrets Operator integration (v2.1+)
- Multi-region active-active deployment (single-cluster install for v2.0)
- Dark mode (forbidden by the brand system; explicitly out)
- Mobile native apps (web responsive only)
- Real-time collaborative editing of the same campaign (basic optimistic-lock for v2.0)
