# DClaw Marketing — v1.2 Feature Roadmap

> 📘 **REVISED PRD v2.3 available:** See `REVISED-PRD.md` for complete gap analysis, current state, and full feature roadmap.


> **For coding agents:** Pick features from this list, implement them fully, and update this doc with a checkmark.
> **Do NOT change the basic stack.** See `AGENTS.md` for architecture lock and brand-system rules (`frontend/src/styles/brand.css` — light mode only, Poppins, `--dk-*` tokens).

## Vision

DClaw Marketing is an **end-to-end product-marketing operating system**: one place where a small team (or one operator + AI agents) plans campaigns, generates multimedia content, schedules and publishes across every channel, talks to leads, attributes revenue, and learns. The MCP integration hub is the connective tissue — every external surface (social, ads, CRMs, analytics, drive, design, voice) plugs in as an MCP server so agents can read/write through one consistent permissioned layer.

**North star:** _from a single PRD, this app produces a launch — copy, visuals, video clips, ads, landing pages, an email sequence, a scheduled posting plan, and a closed-loop attribution view — with a human approving every external action._

## Pre-Flight Checklist — Done

These were the green-light items before v1.2 implementation could start. All locked in by v1.1.0.

- [x] `frontend/package-lock.json` committed after any `npm install` / dependency change
- [x] `frontend/next-env.d.ts` exists and is committed
- [x] `frontend/.gitignore` excludes `node_modules/` and `.next/`
- [x] `docker-compose.yml` healthchecks use `python urllib.request.urlopen()` (backend) and `wget -q --spider` (frontend)
- [x] `frontend/Dockerfile` declares `ARG NEXT_PUBLIC_API_URL` before `RUN npm run build`; `BACKEND_INTERNAL_URL` added in v1.1.1 so the in-container rewrite proxy resolves the backend service
- [x] All new UI uses `--dk-*` tokens or remapped shadcn vars — no hardcoded hex; no `dark:` variants
- [x] All long-running jobs (generation, posting, scraping) run via background workers (Celery + Redis), NOT inline in request handlers
- [x] Every MCP / 3rd-party credential is stored Fernet-encrypted in `Connection` (per-Org data key) — NEVER in env vars per-tenant

## Current Feature Inventory (post-v1.1.1)

> **Legend.** `✅ Shipped` = merged and in the current `main`. `🟡 Partial` = some sub-parts shipped, others pending. `⬜ Pending` = not yet started. Releases referenced: **v1.0.0** (Sprint 1 closeout, formerly `v0.1.0-mvp`), **v1.1.0** (Sprint 2 closeout, formerly `v0.2.0`), **v1.1.1** (Sprint 3 closeout). Renamed in PR #278 so the version line aligns with this doc.

### Foundations (Theme A)
- [x] **A1 — Multi-tenant + Auth** ✅ Shipped (v1.0.0 + v1.1.1 hardening): `User`, `Organization`, `Project`, `Membership` models; fastapi-users JWT; admin-only user creation with temp passwords; mandatory first-login reset; two-tier admin model (bootstrap superadmin + per-org admins) added in v1.1.1; universal slug scheme (`u-/o-/s-` + 6-hex); centralized guards + last-admin protection + audit + notify.
- [x] **A2 — Background worker (Celery + Redis)** ✅ Shipped (v1.0.0): `Job` model with status / progress / result_url / error; SSE stream at `/api/v1/jobs/{id}/stream`; `<JobStatus>` component.
- [x] **A3 — Object storage** ✅ Shipped (v1.0.0): MinIO in dev, S3/R2 in prod; presigned PUT/GET; `Asset` model.
- [x] **A4 — Audit + Approvals** ✅ Shipped (v1.0.0): `AuditEvent` (with UUID-coerce fix in v1.1.1), `ApprovalRequest`, `/inbox` Approval queue with 4-eye rule; `/admin/audit` browser shipped in v1.1.0.

### Content Generation Pipeline (Theme B)
- [x] **B1 — Brand Kit & Voice Profile** ✅ Shipped backend (v1.0.0); Brand Setup Studio polish is Sprint 4 P0.
- [x] **B2 — Briefs & Campaigns** ✅ Shipped (v1.0.0).
- 🟡 **B3 — Multimodal Generation** Backend scaffold + Creatives Agent text path shipped (v1.0.0); **image / video / voice / music providers are pending — Sprint 4 P0** (this is the headline of next sprint).
- [x] **B4 — Repurposing Engine** ✅ Shipped (v1.1.0, SP3-11 in v1.1.1 polish lane).
- [x] **B5 — Variant A/B Studio** ✅ Shipped models + API (v1.1.1, SP3-10); auto-promote bandit is Sprint 4 (Auto-Optimizer G5).
- [x] **B6 — Hook & Headline Lab** ✅ Shipped (v1.1.1, SP3-9).
- ⬜ **B7 — Brand-Safe Image Editor** Pending — P2 / Sprint 5+.

### Scheduling, Publishing & Channels (Theme C)
- [x] **C1 — Calendar & Scheduler** ✅ Shipped (v1.0.0).
- 🟡 **C2 — Multi-Channel Publisher** Adapters live for ~13 channels (X, LinkedIn, IG, FB, YouTube, TikTok, Threads, Substack, Bluesky, Reddit, Pinterest, Discord, Mastodon). **OAuth scaffold shipped (v1.1.0); real client credentials are Sprint 4 P0.**
- [x] **C3 — Email & Newsletter** ✅ Shipped (v1.1.0): Resend / Postmark / SendGrid + sequences.
- 🟡 **C4 — Ads Publisher** Meta + LinkedIn + Google Ads paused-campaign create shipped (v1.1.0); UI dashboard is partial.
- ⬜ **C5 — SMS / WhatsApp** Pending — P2.
- ⬜ **C6 — Push & In-App** Pending — P2.

### MCP Integration Hub (Theme D)
- [x] **D1 — MCP Connection Registry** ✅ Shipped (v1.1.0): Fernet-encrypted tokens via per-Org data key.
- [x] **D2 — Multimedia MCP Servers** 14 adapters shipped (HubSpot, GA4, Stripe, Ahrefs, Webflow, WordPress, Ghost, Slack, Discord, Notion, Google Drive, Salesforce, Mixpanel, PostHog). **Generation MCPs (Replicate / Runway / Suno / ElevenLabs / Cartesia / Deepgram) are Sprint 4 P0** — they unblock B3 image/video/voice.
- [x] **D3 — BYO MCP marketplace** ✅ Shipped (v1.1.1, SP3-15).
- [x] **D4 — Webhook Hub (inbound)** ✅ Shipped (v1.1.0): generic receiver + `Automation` rules.

### Audience, Lead & CRM (Theme E)
- [x] **E1 — Lead 2.0** ✅ Shipped (v1.1.0).
- [x] **E2 — Enrichment & ID Resolution** ✅ Shipped (v1.1.1, SP3-12).
- [x] **E3 — Segments & Audiences** ✅ Shipped (v1.1.0).
- [x] **E4 — Sequences** ✅ Shipped (v1.1.0).
- [x] **E5 — CRM Sync** ✅ Shipped (v1.1.0): Pipedrive + Attio + HubSpot adapters.
- [x] **E6 — Attribution & Revenue Tie-Back** ✅ Shipped (v1.1.0): time-decay + `/analytics/sankey`.

### Analytics & Insights (Theme F)
- [x] **F1 — Unified Analytics Dashboard** ✅ Shipped (v1.1.0): per-campaign drill-down added v1.1.1.
- [x] **F2 — Content Performance Heatmap** ✅ Shipped (v1.1.1, SP3-13).
- ⬜ **F3 — Competitor Tracker** Pending — P2.
- ⬜ **F4 — Customer-Voice Mining** Pending — P2.

### AI Agents & Automation (Theme G)
- 🟡 **G1 — Marketing Agent (chat surface)** Conductor scaffold + chat dock shipped (v1.1.1, SP3-14). **Real Claude Agent SDK runtime, tool-calls into all MCPs, "every aspect of the platform" controllability — Sprint 4 P0** (this is the headline of next sprint).
- ⬜ **G2 — Inbox Agent (replies & DMs)** Sprint 4.
- ⬜ **G3 — Trend Radar** Sprint 4.
- ⬜ **G4 — Comment Sentiment & Triage** Sprint 4 / 5.
- ⬜ **G5 — Auto-Optimizer (bandit)** Sprint 4 / 5.

### Sites, SEO & Long-Form (Theme H)
- [x] **H1 — Landing-Page Builder** ✅ Shipped minimal HTML-body (v1.1.1, SP3-16).
- [x] **H2 — SEO Blog Pipeline** ✅ Shipped (v1.1.1, SP3-17) + Theme H site-audit / internal-link / ranking-delta (v1.1.0).
- ⬜ **H3 — Topic Cluster Map** Pending — P2.

### Compliance, Reliability, Polish (Theme I)
- [x] **I1 — Rate-Limit & Quota Manager** ✅ Shipped (v1.1.0).
- 🟡 **I2 — Sandbox / Preview Mode** Sandbox flag exists; full "dry-run" UI is Sprint 4 / 5.
- [x] **I3 — Cost Tracking** ✅ Shipped (v1.1.0): per-org daily budgets + soft/hard caps + `/admin/costs`.
- [x] **I4 — Export / GDPR** ✅ Shipped (v1.1.0).

### v2.0-track themes (J–P)
- [x] **J — Client Operations** ✅ Org CRUD + per-Org retainer + budgets (v1.1.0); onboarding wizard via Project Setup Wizard (SP3-5, v1.1.1).
- 🟡 **K — Project Management** Kanban shipped (v1.1.1, SP3-20); Gantt + capacity planning pending.
- [x] **L — Time Tracking & Billing** ✅ Shipped time logs (v1.1.1, SP3-21), retainer burn-down (v1.1.1, SP3-22), invoices CRUD + actions (v1.1.1, SP3-23). QuickBooks export shipped (v1.1.0).
- [x] **M — Client Reporting** ✅ Weekly + monthly HTML reports → MinIO (v1.1.0); signed-JWT embeddable dashboards (v1.1.1, SP3-19).
- [x] **N — Knowledge Base & SOPs** ✅ Playbook search + CRUD (v1.1.1, SP3-18).
- ⬜ **O — Client Portal** Activates on `is_external=true`. Pending — P2 / future.
- ⬜ **P — Workflow Builder** Visual no-code chain. Workflow runner backend exists (v1.1.0); **visual builder UI + agentic-step nodes are Sprint 4 / 5**.

### Theme Q (Brand & Context Ingestion — foundational)
- 🟡 **Q1 — Brand Setup Studio** Backend BrandKit + KG write-back insights shipped; **end-to-end Studio UX (guidelines-PDF → palette → fonts → voice → personas → live preview) is Sprint 4 P0**.
- [x] **Q2 — Input Channel Hub** ✅ File / URL / git-repo / zip ingestion (v1.0.0 + v1.1.0 URL + v1.1.1 git, SP3-8).
- [x] **Q3 — Knowledge Graph** ✅ Shipped (v1.0.0); per-source drill-down (v1.1.1, SP3-7).
- [x] **Q4 — Freshness & Re-ingestion** ✅ Schedulers + diff highlights (v1.1.0).
- [x] **Q5 — Goal & Constraint Setup** ✅ Shipped (v1.0.0).
- [x] **Q6 — Project Setup Wizard** ✅ Shipped (v1.1.1, SP3-5).

### Identity / admin (post-v2.0-§2 additions, Sprint 3)
- [x] **Two-tier admin model** ✅ Shipped (v1.1.1): bootstrap superadmin + per-org admins, centralized guards, last-admin protection, self-demote refusal, audit + notify.
- [x] **Universal slug scheme** ✅ Shipped (v1.1.1): `u-{first4}-{6hex}`, `o-{first4}-{6hex}`, bootstrap `s-admn-000000`; migration re-slugs all rows.
- [x] **Left-sidebar navigation** ✅ Shipped (v1.1.1): replaces overflowing top bar; admin group collapses.
- [x] **Auto-merge + auto-close pipeline** ✅ Shipped (v1.1.1): squash carries PR body; workflow has `issues: write`; queue drains itself.

### Pending blocks summary (what's left for v1.2.0)
- ⬜ **Sprint 4 P0** — Model Registry & AI Gateway (S4-M, new — multi-provider model config, health checks, feature-availability matrix, live logs + metrics) · Brand Setup Studio polish (Q1/S4-E) · real OAuth client credentials wired (C2/S4-F, all platforms) · TOTP enrollment UI (S4-G) · observability dashboards (Grafana + Sentry tags + `/admin/health` queue depth, S4-H) · user-guide refresh.
- ⬜ **Sprint 4 P0 — Agent runtime headline** — Claude Agent SDK integration (S4-A) · real model connections via Model Registry (S4-B) · Conductor as all-in-one chat controller (S4-C) · end-to-end live workflow execution (S4-D). See "Sprint 4 Plan" below.
- ⬜ **Sprint 4 P1** — Audit retention pruner · v1 legacy router consolidation · BrandKitInsight bandit ranking · AEO scorer (S4-K, new — Answer Engine Optimization for AI search).
- ⬜ **Sprint 5 P0 — Conductor consolidation & top-of-the-line agentic chat (NEW headline, 2026-05-15)** — Single Conductor under Work at `/conductor` (S5-CDR-A) · drag-drop file/folder upload + vision (S5-CDR-B) · Claude Agent SDK + maximum tool fleet covering every sidebar feature (S5-CDR-C) · streaming responses + extended thinking (S5-CDR-D) · web search + light/deep research modes (S5-CDR-E) · Claude/ChatGPT-parity polish (S5-CDR-F) · plan doc update (S5-CDR-G). See "Sprint 5 Plan" below. Issues #347–#353.
- ⬜ **Sprint 5+ P2** — Brand-Safe Image Editor (B7) · SMS / WhatsApp (C5) · Push / In-App (C6) · Competitor Tracker (F3) · Customer-Voice Mining (F4) · Topic Cluster Map (H3) · Client Portal (O) · Visual Workflow Builder (P) · Trend Radar / Comment Triage / Auto-Optimizer (G3-G5) · Sandbox dry-run UI polish.
- ⬜ **Marketing collateral** — Issues #49–#53 (one-pager / slides / demo script / demo video / launch posts). **Operator-owned, out-of-band, off-limits to engineering** unless explicitly asked.

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

## Implementation Priority — sprint-by-sprint (as actually executed)

1. **Sprint 1 — Foundations.** ✅ Shipped (v1.0.0, 2026-05-12). A1 (Auth + Org/Project), A2 (Celery + Redis), A3 (MinIO + Assets), A4 (Audit + Approvals). Theme Q backend (BrandKit, ingestion, KG, goals). Phase 4 (Creatives Agent scaffold). Frontend baseline: top-nav, Approval Inbox, Brand Kit page, Knowledge Sources, Agents, Library, Calendar. ~150 PRs · 52 % of plan.
2. **Sprint 2 — Feature-complete.** ✅ Shipped (v1.1.0, 2026-05-13). Phase 5 (multi-channel publishing across all 8 v1.2 channels + OAuth scaffold for 7 providers), Phase 6 (MCP Hub with 14 concrete adapters), Phase 7 (Email + Ads + Sequences), Phase 8 (Lead 2.0 + CRM sync + Sankey attribution), Phase 9 (Analyst agent + KG write-back), Phase 10 (agency ops: retainer, invoices, time, share tokens, weekly + monthly client reports), Phase 11 (QuotaCounter, cost-cap, GDPR export, audit browser). Theme D4 (webhooks + Automation). Theme H (SEO depth). ~60 PRs · 90 % of plan.
3. **Sprint 3 — Operator-ready.** ✅ Shipped (v1.1.1, 2026-05-14). Two-tier admin model (bootstrap superadmin + per-org admins + last-admin protection + audit + notify). Universal slug scheme. Combined create-user-with-org dialog. Left-sidebar navigation. End-to-end auto-merge + auto-close pipeline. SP3-1 → SP3-24 polish lane (Q6 wizard, Fernet-encrypted social tokens, knowledge drill-down, hooks lab, A/B variants, repurpose, heatmap, BYO MCP, kanban, time tracker, retainer + invoices, Pydantic v2 sweep, etc.). Release rename (`v0.1.0-mvp` → `v1.0.0`, `v0.2.0` → `v1.1.0`). 44 PRs · 95 % of plan.
4. **Sprint 4 — Agents go live + v1.2 demo posture.** ⬜ Pending. See **"Sprint 4 Plan"** below — this is the next sprint and the headline focus is: real agents calling real models doing real workflows on the platform, with the Conductor as a single all-in-one chat controller for every aspect of DClaw.

---

## Sprint 4 Plan — "Agents go live, run the platform from one chat"

> **Target release:** `v1.2.0` — the demo build the stakeholder is expecting (the plan doc is `PLAN-v1.2.md`, so this aligns the version line).
> **Headline.** Stop scaffolding agents. Start running them. By the end of Sprint 4, the Conductor agent can read a brief, pick the right role-Agent, call the right MCP tools against the right real model, draft a multi-channel campaign, queue it through the Approval Inbox, and report back — all from a single chat surface that controls every aspect of the platform.
> **Posture.** Sprint 4 is **build + integrate + test**, not new scaffolding. Almost every backend exists; the work is wiring real models / real credentials / real flows into the runtime.
> **No hard deadline** — ship when done right. Demo audience is both internal stakeholders and external/investor-grade. External credentials (Anthropic, Replicate, ElevenLabs, OAuth apps) will be wired in as they become available; all adapters fall back to the existing deterministic stub path until then.

### Competitive context (researched May 2026)

The market has validated this sprint's direction:

- **CharacterQuilt (YC P2026)** — "AI infra for marketing: a brain that learns your brand, and agents that operate your existing tools." Direct overlap with DClaw's Conductor + MCP hub vision. They ship in hours what used to take 3 agencies.
- **Sitefire (YC W2026)** — Answer Engine Optimization (AEO) for AI search (ChatGPT/Perplexity/Claude). Hot new frontier; HubSpot Spring 2026 Spotlight also launched AEO. DClaw adds this as S4-K.
- **Absurd (YC F2025)** — Production-quality brand videos in 72 hrs via multi-agent orchestration. DClaw's S4-B (Replicate + Runway) is the head-on answer.
- **HubSpot Breeze AI** — Content Agent + Social Agent + Prospecting Agent. Enterprise players are now shipping role-specific agents. DClaw's fleet (Conductor + 6 role-agents) is architecturally ahead.
- **Salesforce Agentforce** — Autonomous agents within Salesforce; 40–60% CAC reduction reported. Validates the agent-as-operator thesis.
- **Jasper / Writer.com / Copy.ai** — Brand voice is now "infrastructure" (video + audio knowledge), not just templates. DClaw's BrandKit + KG + Brand Setup Studio (S4-E) is the answer.

**White-space DClaw can own:** MCP integration hub breadth (14+ adapters as the unified tool layer), per-tenant trust-mode resolver with explainability, multi-tenant agency architecture, and — with S4-M — the most capable AI model management layer in any marketing platform.

**Anthropic Agent SDK (May 2026):** Anthropic renamed the Claude Code SDK → Claude Agent SDK, adding: programmatic tool calling (Claude writes code that orchestrates tools, not just individual round-trips), Agent Skills (reusable domain-specific expertise, maps to our role-agent pattern), and managed multi-agent orchestration (lead + specialist sub-agents on a shared file system). S4-A should be designed around these primitives.

### Sprint 4 themes (P0 → P2)

#### S4-A. Agent runtime — real Claude Agent SDK integration **(P0, headline)**
The current Conductor is a chat scaffold. Sprint 4 turns it into a working multi-agent fleet.

**Stories**
- **S4-A1** Swap inline LLM calls for Claude Agent SDK runtime. Per-agent system prompts + tool list + memory. Sub-agent pattern: Conductor calls role-Agents as tools.
- **S4-A2** Conductor agent: brief → decomposition → dispatch → watch → escalate → report. Reads `Goal`, `Constraint`, `Budget`, and `BrandKit` from the KG. Writes its reasoning trace to `AuditEvent` with confidence + cost.
- **S4-A3** Role-agents end-to-end (no more deterministic stubs): Creatives · SMM · SEO · Paid Media · Analyst · Inbox · Reviewer. Each agent has a typed tool list and a Station UI surface.
- **S4-A4** Trust-mode resolver wired into every tool call: `Org default → Project override → Channel override → Action-level override`. UI shows the resolved mode before the action fires.
- **S4-A5** 4-eye approval upgrade in the Approval Inbox: cannot approve your own request; per-action reasoning trace; side-by-side variant compare.
- **S4-A6** Reasoning trace replay UI (`/audit/{event_id}/replay`) — view any past agent decision: inputs / alternatives considered / confidence / tool calls / cost.

**Definition of done**
- Conductor can take a one-paragraph brief and produce a queued multi-channel rollout with all assets in the Approval Inbox.
- Every action is auditable end-to-end (input → reasoning → output → tool calls → cost → approver).
- Tests cover Conductor decomposition, role-Agent tool-call paths, trust-mode resolution, and approval gate enforcement.

---

#### S4-B. Real model connections — generation MCPs go live **(P0)**
B3 backend was scaffolded in v1.0.0 but image / video / voice / music providers were stubbed. Sprint 4 wires the real ones.

**Stories**
- **S4-B1** Generation MCP adapters: **Replicate** (image / Flux / Imagen) · **Runway** (video) · **Suno** + **Udio** (music) · **ElevenLabs** + **Cartesia** (voice) · **Deepgram** + **Whisper** (transcription). Each conforms to the uniform tool set (`generate / edit / export`).
- **S4-B2** Cost-tracking integration: every generation call writes a cost-ledger row tagged with `(org, project, agent, model, kind)`. QuotaCounter pre-check refuses if over budget.
- **S4-B3** `dont_say` lint pass on text outputs; auto-retry once with `[refine]` prompt before surfacing to reviewer.
- **S4-B4** Model selection per-action: Opus (Conductor) · Sonnet (role-Agents) · Haiku (fast-path: classification, anomaly, simple drafting). Per-Org override.
- **S4-B5** Embedding model decision + pin: OpenAI `text-embedding-3-large` (default) or Voyage AI. Migration to re-embed existing KG corpus.
- **S4-B6** Per-tenant LLM provider override — agencies want to scope provider per-client.

**Definition of done**
- Creatives Agent can produce a text + image + short video draft in one run.
- Cost ledger reflects each call within ~1s.
- Switching an Org's model preference takes effect on the next agent run with no restart.

---

#### S4-C. Conductor as all-in-one chat controller **(P0)**
The dock UI shipped (SP3-14). Sprint 4 makes it actually control the platform.

**Stories**
- **S4-C1** Conductor chat dock surfaces on every authenticated page. Context-aware: pre-fills the current Org / Project / record into the conversation so `summarise this lead` works without restating IDs.
- **S4-C2** Tool fleet exposed to the Conductor — read + write across the whole platform: `list_orgs · create_user · invite_member · search_kg · create_brief · launch_generation · queue_post · publish_now · approve_request · run_seo_audit · enrich_lead · build_segment · draft_email_sequence · export_gdpr · view_quota · rotate_oauth · ...`. Every tool goes through the existing centralized guard + audit + trust-mode resolver.
- **S4-C3** Full-screen mode `/conductor` with conversation history, dispatched-task tree, escalation queue, budget burn-down side panel.
- **S4-C4** Streaming responses (SSE). Tool calls render inline as cards with status (pending / running / approved / done / failed) + click-through to the actual record.
- **S4-C5** Cross-platform navigation: "show me last week's underperforming LinkedIn posts" returns a list with deep links into `/calendar` and `/heatmap`.
- **S4-C6** Conductor remembers across sessions per `(user, org)`; threads listed in `/conductor/threads`; pinning + sharing within Org.

**Definition of done**
- An operator can do every routine action from the Conductor chat without touching another page (besides eyeballing previews).
- "Drive the platform by chat alone" demo runs end-to-end in under 10 minutes.

---

#### S4-D. Live workflow execution + testing **(P0)**
Workflows shipped in v1.1.0 but they ran on stubs. Sprint 4 runs them for real.

**Stories**
- **S4-D1** Workflow runner: real tool calls (not stubs); approval-node pause/resume verified end-to-end; branch-node evaluator with KG-aware predicates.
- **S4-D2** Workflow templates: Product Launch · SEO Refresh · Brand Revamp · Newsletter Reboot · Lead-Nurture Cascade. Each ships with a real example run that lands a real (sandboxed) campaign.
- **S4-D3** **End-to-end smoke harness** — `pytest` suite that boots the full stack, runs each workflow template against `Org.dry_run=true`, and asserts the expected Approval Inbox entries / cost-ledger rows / audit events appear.
- **S4-D4** **Live workflow runs in production-shaped sandbox** — staging Org with real OAuth credentials for 3 channels (LinkedIn / X / Bluesky), real model keys (Anthropic + OpenAI + Replicate + ElevenLabs at minimum). Operator can flip a flag to publish for real or dry-run.
- **S4-D5** Failure playbook — workflow stalls / model timeouts / OAuth expiry are handled with structured retry + Conductor escalation rather than 500s.
- **S4-D6** Visual workflow builder UI (P) — simplest viable version: list of templates + ability to clone + edit step sequence + save as new template. Drag-graph builder is Sprint 5+.

**Definition of done**
- All 5 workflow templates run end-to-end in dry-run mode and produce the expected artefacts.
- One template (Product Launch) runs end-to-end **live** against the staging Org and posts to a real LinkedIn / X / Bluesky test account.
- Documented runbook in `docs/USER-GUIDE.md`.

---

#### S4-E. Brand Setup Studio polish (Q1) **(P0)**
The studio UX was scaffolded; Sprint 4 finishes the flow so an operator can complete Theme Q in one sitting.

**Stories**
- **S4-E1** Upload-guidelines-PDF flow: parse text + extract palette + extract fonts + extract voice fragments → preview → confirm → versioned BrandKit.
- **S4-E2** Live-preview pane: a generated post sample re-renders as the operator tweaks voice sliders / palette / fonts.
- **S4-E3** Persona builder: cards with name + JTBD + fears + desires; clone + version.
- **S4-E4** "Set Active" with diff view between versions.
- **S4-E5** BrandKitInsight bandit ranking — replace FIFO injection with a small bandit so agents converge on the brand voice fastest.

---

#### S4-F. Real OAuth credentials wired **(P0)**
**Stories**
- **S4-F1** LinkedIn / X / Instagram operator-supplied `client_id` + `client_secret` (env var per provider).
- **S4-F2** OAuth dance verified end-to-end against staging accounts; auto-reconnect prompts when tokens expire.
- **S4-F3** Per-account health monitoring rolls up to `/admin/health`.

---

#### S4-G. TOTP enrollment UI **(P0)**
Backend columns shipped (v1.1.1, PR #252). Sprint 4 surfaces them.

**Stories**
- **S4-G1** `/settings/2fa` page: QR code · scratch / recovery codes · verify-on-enable.
- **S4-G2** Login-time TOTP challenge.
- **S4-G3** Admin override (disable for a user) with audit row.

---

#### S4-M. Model Registry & AI Gateway **(P0 — prerequisite for agent runtime)**

Every agent on the platform needs models: text LLMs for reasoning, embedding models for the Knowledge Graph, image/video/voice/music generators for creative production, transcription models for repurposing. Right now the only way to configure models is via env-vars that apply globally. Sprint 4 ships a full **per-org, per-superadmin model management system** so that admins can configure exactly which models are available, see their health and capabilities live, and the platform's feature-availability changes accordingly.

**Why this comes before S4-A:** The agent runtime needs to know what models are available for each org before it can route tasks. The Model Registry is the config layer that makes all of S4-A, S4-B, and S4-C possible.

**Multiple providers of the same type are fully supported.** An org can have 3 Anthropic keys (e.g. dev / staging / prod), 2 OpenAI keys (personal + org-billing), an Ollama instance alongside a Groq OpenAI-compatible endpoint, etc. There is no limit. Each provider is an independent row; models from all providers of the same type coexist in the registry and appear in the same assignment dropdowns. This also means provider-level failover is possible (if provider A's Anthropic key is rate-limited, the resolver can fall back to provider B's key).

**Supported provider types — full taxonomy**

Providers are grouped into four tiers by their integration method.

**Tier 1 — Native APIs** (each has its own auth format or SDK; DClaw implements a dedicated adapter per provider)

| Provider type | What it covers | Auth |
|---|---|---|
| `anthropic` | Claude Opus / Sonnet / Haiku — text, function calling, extended reasoning | API key |
| `openai` | GPT-5/4o series (text, vision), `text-embedding-3-*` (embedding), `gpt-image-1` (image gen), `tts-1` / `gpt-4o-audio` (TTS), `whisper-1` (transcription) | API key |
| `google_gemini` | Gemini 2.x / Flash / Pro — text, vision/image_understanding, image gen (`Imagen`), embedding (`text-embedding-005`) | API key (AI Studio) |
| `google_vertex_ai` | Same Gemini + Imagen models served from Google Cloud; access via Vertex AI OpenAI-compatible endpoint or native API | Service account JSON or ADC |
| `azure_openai` | OpenAI models served from Azure — same capability set as `openai`, adds compliance / SLA / VNet | Base URL + API key + API version + deployment name |
| `aws_bedrock` | Claude, Llama, Mistral, Titan served from AWS — same models, adds IAM / VPC / CloudTrail | AWS access key + secret + region (or IAM role via instance profile) |
| `mistral` | Mistral Large / Medium / Small (text, function calling), Pixtral (vision), Voxtral / Le Chat TTS (voice), Mistral Embed | API key |
| `cohere` | Command R / Command A (text, function calling), `embed-v4` multimodal embedding, `rerank-4` reranker | API key |
| `voyage_ai` | Embedding specialists: `voyage-4-large`, `voyage-4`, `voyage-4-lite`, `voyage-4-nano`; multimodal embeddings (text + image in shared space); `rerank-2` reranker | API key |
| `huggingface` | Serverless Inference via HF router (`https://router.huggingface.co/v1`) — OpenAI-compatible; routes to partner providers (Together, fal, SambaNova, Replicate). Covers text LLMs, embeddings (BERT, BGE, sentence-transformers), image models, STT | HF API token |

**Tier 2 — Named OpenAI-compatible aggregators** (all speak OpenAI Chat Completions; DClaw pre-fills base URL + required headers; treated as `openai_compatible` under the hood but have named types for UX clarity and auto-discovery)

| Provider type | What it covers | Special notes |
|---|---|---|
| `openrouter` | 500+ models from 60+ upstream providers (Anthropic, OpenAI, Google, Meta, Mistral, DeepSeek, Qwen, …) via a single key + base URL `https://openrouter.ai/api/v1` | Requires `HTTP-Referer` + `X-Title` headers; exposes per-model pricing in `/models` response; supports provider routing / fallback preferences |
| `groq` | Llama 3.x, Qwen, Mistral, Gemma on Groq LPU hardware — text + function calling; 800+ tok/s | Base URL `https://api.groq.com/openai/v1`; text-only, no image gen |
| `together_ai` | 200+ open-source models: Llama, Qwen, DBRX, StableDiffusion, etc. — text, embedding, image gen | Base URL `https://api.together.xyz/v1`; image gen via `image_generation` endpoint |
| `fireworks_ai` | Fast open-source inference (FireAttention engine) — Llama, Mixtral, Qwen, function calling | Base URL `https://api.fireworks.ai/inference/v1` |
| `deepseek` | DeepSeek V3 / R1 — text, function calling, reasoning; very cheap per-token | Base URL `https://api.deepseek.com/v1`; R1 has `reasoning` capability |
| `perplexity` | Sonar models (web-augmented text) — adds live web context to every completion | Base URL `https://api.perplexity.ai`; adds `web_search` capability tag |
| `sambanova` | Fast enterprise inference on RDU chips — Llama, Meta models | Base URL from SambaNova dashboard |

**Tier 3 — Multimedia specialists** (non-text generation; native APIs)

| Provider type | What it covers |
|---|---|
| `replicate` | Image: Flux, SDXL, Stable Diffusion; Video: Wan, Kling, CogVideoX, Mochi; Music: MusicGen; Transcription: Whisper; any public Replicate model by ID |
| `elevenlabs` | TTS + voice cloning (`eleven_multilingual_v2`, Flash v2.5); STT via Scribe; Sound effects |
| `runway` | Video generation (Gen-3 Alpha / Gen-4); image-to-video; video editing |
| `suno` | Music generation (Suno v4); lyrics + audio |
| `deepgram` | STT / transcription (Nova-3); speaker diarisation; live streaming STT |
| `cartesia` | Low-latency TTS (Sonic); voice cloning; real-time streaming |
| `fal_ai` | Image: Flux fast variants, SDXL; Video: Kling, HunyuanVideo; LoRA training | 

**Tier 4 — Self-hosted / generic**

| Provider type | What it covers |
|---|---|
| `ollama` | Local Ollama instance; auto-discovers all pulled models via `GET /api/tags`; capability-tagged via `POST /api/show` metadata |
| `openai_compatible` | Generic catch-all: vLLM, LM Studio, text-generation-webui, llama.cpp server, Kobold, any custom server; admin supplies base URL + optional key |

**Model capability tags** (what a model can do — drives feature-availability matrix and assignment dropdowns)

`text` · `embedding` · `multimodal_embedding` · `image_generation` · `image_understanding` · `audio_transcription` · `text_to_speech` · `text_to_video` · `text_to_music` · `function_calling` · `reasoning` · `reranking` · `web_search`

- **`multimodal_embedding`** — embeds text and images into a shared vector space (Cohere Embed 4, Voyage AI multimodal, Together CLIP); enables image-based KG search.
- **`reranking`** — reorders a list of retrieved chunks by relevance to a query (Cohere Rerank 4, Voyage Rerank 2); improves RAG quality. The resolver exposes this as a separate capability slot so the KG can use a reranker if configured.
- **`web_search`** — model has live internet access built in (Perplexity Sonar, some OpenRouter routes); used by Analyst agent + Trend Radar.

**Stories**

- **S4-M1** `ModelProvider` + `ModelEntry` DB models + Alembic migration. `ModelProvider(org_id nullable, provider_type, name, base_url, encrypted_api_key, extra_config_json, is_active)`. `ModelEntry(provider_id, model_id, display_name, capabilities[], context_window, max_output_tokens, status, last_health_check_at, health_error)`. Superadmin-level providers have `org_id=NULL` and are available globally; org-admin providers are scoped to the org.

- **S4-M2** Provider CRUD API (`/api/v1/models/providers`) + model-entry CRUD (`/api/v1/models/entries`). Superadmin-only for global providers; org-admin for org-scoped. API key encrypted via the same Fernet-per-org pattern as `Connection`.

- **S4-M3** Auto-discovery on provider save (runs as a Celery task immediately after provider creation; also triggered manually via "Sync" button):
  - **OpenAI / Azure OpenAI / Groq / Together / Fireworks / DeepSeek / Perplexity / SambaNova / generic openai_compatible:** `GET base_url/v1/models` → import all returned model objects, capability-tag by heuristic (S4-M4).
  - **OpenRouter:** `GET https://openrouter.ai/api/v1/models` → rich model objects include `architecture.modality` (`text→text`, `text→image`, etc.) and `pricing`; use modality field for accurate capability tagging, no heuristic needed.
  - **Google Gemini:** hardcoded known-model list (Gemini 2.0 Flash, 2.0 Pro, Gemini 1.5 families, Imagen 3, text-embedding-005) with pinned capabilities.
  - **Google Vertex AI:** same list as Gemini; base URL differs per region / project.
  - **AWS Bedrock:** curated list of available foundation models (Claude, Llama, Mistral, Titan Embed); capabilities pinned per model ID.
  - **Azure OpenAI:** `GET base_url/openai/models?api-version={v}` → import deployed models; capabilities via heuristic.
  - **Mistral:** `GET https://api.mistral.ai/v1/models` → import; tag Pixtral → `image_understanding`, Voxtral → `text_to_speech`, embed → `embedding`.
  - **Cohere:** hardcoded list: Command A/R+ → `text`, `function_calling`; Embed 4 → `embedding`, `multimodal_embedding`; Rerank 4 → `reranking`.
  - **Voyage AI:** hardcoded list: voyage-4-* → `embedding`; voyage-multimodal → `embedding`, `multimodal_embedding`; rerank-2 → `reranking`.
  - **HuggingFace:** `GET https://router.huggingface.co/v1/models` → import supported models; capability via heuristic.
  - **Ollama:** `GET base_url/api/tags` → import all pulled models; `POST base_url/api/show {name}` for `details.families` to detect vision (`clip`) and embedding models.
  - **Anthropic:** hardcoded list: claude-opus-4-7, claude-sonnet-4-6, claude-haiku-4-5 → `text`, `function_calling`, `image_understanding`; Opus + claude-3-7-sonnet → add `reasoning`.
  - **Replicate:** curated lists per modality category + admin can add arbitrary model IDs (owner/name:version format).
  - **ElevenLabs / Cartesia / Runway / Suno / Deepgram / fal.ai:** curated known-model lists with pinned capabilities.

- **S4-M4** Capability heuristic for OpenAI-compatible model IDs (applied when no richer metadata is available). Pattern → capabilities assigned:
  - `*embed*`, `*e5*`, `*bge*`, `*nomic*`, `*minilm*`, `*sentence*` → `embedding`
  - `*rerank*` → `reranking`
  - `*dall-e*`, `*image*`, `*flux*`, `*sdxl*`, `*stable-diffusion*`, `*playground*` → `image_generation`
  - `*whisper*`, `*stt*`, `*transcrib*`, `*asr*` → `audio_transcription`
  - `*tts*`, `*voice*`, `*eleven*`, `*cartesia*`, `*voxtral*` → `text_to_speech`
  - `*video*`, `*runway*`, `*wan*`, `*kling*`, `*mochi*`, `*cogvideo*` → `text_to_video`
  - `*music*`, `*suno*`, `*musicgen*`, `*udio*` → `text_to_music`
  - `*vision*`, `*4o*`, `*llava*`, `*minicpm*`, `*pixtral*`, `*gemini*`, `*qwen-vl*`, `*internvl*` → `image_understanding` + `text`
  - `*sonar*`, `*perplexity*` → `text` + `web_search`
  - `*o1*`, `*o3*`, `*o4*`, `*deepseek-r1*`, `*qwq*` → `text` + `function_calling` + `reasoning`
  - else → `text` + `function_calling`
  - Operator can manually toggle any capability on any entry via the UI; manual overrides survive re-sync.

- **S4-M5** Health-check Celery beat task (every 5 min). Per-provider strategy:
  - **Anthropic:** `POST /v1/messages` with `max_tokens=1` + model param — success = healthy.
  - **OpenAI / Azure OpenAI / Groq / Together / Fireworks / DeepSeek / Perplexity / SambaNova / HuggingFace / generic openai_compatible:** `GET base_url/v1/models` — 200 = healthy (no credits spent).
  - **OpenRouter:** `GET https://openrouter.ai/api/v1/models` — 200 = healthy; additionally check `GET https://openrouter.ai/api/v1/auth/key` to verify key is valid and show remaining credit balance in the provider card.
  - **Google Gemini:** `GET https://generativelanguage.googleapis.com/v1beta/models?key={k}` — 200 = healthy.
  - **Google Vertex AI:** `GET {base_url}/v1/models` with OAuth2 Bearer — 200 = healthy.
  - **AWS Bedrock:** `ListFoundationModels` SDK call — success = healthy (uses boto3).
  - **Mistral:** `GET https://api.mistral.ai/v1/models` with Bearer — 200 = healthy.
  - **Cohere:** `GET https://api.cohere.com/v2/models` with Bearer — 200 = healthy.
  - **Voyage AI:** `GET https://api.voyageai.com/v1/models` — 200 = healthy.
  - **Ollama:** `GET base_url/` — body `"Ollama is running"` = healthy; additionally check model is still in `/api/tags`.
  - **Replicate:** `GET https://api.replicate.com/v1/models/{owner}/{name}` with auth — 200 = healthy.
  - **ElevenLabs:** `GET https://api.elevenlabs.io/v1/models` with `xi-api-key` header — 200 = healthy.
  - **Cartesia:** `GET https://api.cartesia.ai/voices` with `X-API-Key` header — 200 = healthy.
  - **Runway:** `GET https://api.runwayml.com/v1/models` with Bearer — 200 = healthy.
  - **Deepgram:** `GET https://api.deepgram.com/v1/projects` with `Token` auth — 200 = healthy.
  - **fal.ai:** `GET https://fal.run/health` — 200 = healthy.
  - **Suno:** lightweight ping to Suno API status endpoint.
  - On any failure: `status=unhealthy`, write `health_error` (first 500 chars of error message), emit `AuditEvent`. On recovery: `status=healthy`, clear error, emit recovery `AuditEvent`.

- **S4-M6** `ModelCallLog` table: every model invocation anywhere in the platform logs `(model_entry_id, org_id, caller_component, started_at, duration_ms, input_tokens, output_tokens, cost_usd, status, error_message, request_id)`. `caller_component` is a string constant defined per call site (e.g. `"conductor"`, `"creatives_agent"`, `"embeddings"`, `"image_gen"`). Written async via the Celery worker or a lightweight fire-and-forget (non-blocking).

- **S4-M7** Feature-availability API (`GET /api/v1/models/feature-availability`). Returns two objects:
  1. **Component coverage** — for each platform component (`conductor`, `creatives_agent`, `smm_agent`, `seo_agent`, `paid_media_agent`, `analyst_agent`, `knowledge_graph`, `image_generation`, `voice_generation`, `video_generation`, `music_generation`, `audio_transcription`, `brand_kit_studio`, `aeo_scorer`) → `{required: [cap,...], covered: [cap,...], missing: [cap,...], status: "full"|"partial"|"none"}`.
  2. **Capability coverage** — for each capability tag → `{available: bool, model_count: int, healthy_count: int}`.
  - Component → required capability map is hardcoded in the backend.

- **S4-M8** Live log streaming: SSE endpoint `GET /api/v1/models/{id}/logs/stream`. Publishes to Redis channel `model_logs:{model_entry_id}` on every call; SSE handler subscribes and streams JSON lines to the client. Log line shape: `{ts, component, status, latency_ms, input_tokens, output_tokens, cost_usd, error}`.

- **S4-M9** Metrics endpoint: `GET /api/v1/models/{id}/metrics?window=7d`. Aggregates from `ModelCallLog`: total calls, success rate, avg/p50/p95/p99 latency, total tokens, total cost, calls-by-component breakdown, daily time series. Cached in Redis with 60s TTL.

- **S4-M10** Frontend: `/admin/models` page (superadmin + org-admin).

  **Section A — Feature Availability** (top of page, always visible)
  - Sub-section A1: **Platform Components** — grid of component cards (Conductor, Creatives Agent, SMM Agent, SEO Agent, KG / Embeddings, Image Generation, Voice Generation, Video Generation, Music Generation, Audio Transcription, Brand Kit Studio, AEO Scorer). Each card shows a colour-coded status chip: ✅ Full | ⚠ Partial | ✗ Missing. Clicking opens a popover listing required / missing capabilities with "Add a provider" CTA.
  - Sub-section A2: **Capability Summary** — a single row of capability pills with counts: e.g. "text ✅ 3 models · embedding ✅ 1 · image_generation ✗ 0 needed · text_to_speech ✗ ...".

  **Section B — Providers** — cards for each configured ModelProvider with "Add Provider" button. Provider card shows: name, type badge, model count, overall health dot, and (for OpenRouter) remaining credit balance. "Add Provider" opens a slide-over form.

  **Provider type selection — two-level picker:**

  The form opens with six radio buttons displayed upfront (no dropdowns, no extra click):
  ```
  ◉ Anthropic
  ○ OpenAI
  ○ OpenAI-compatible
  ○ Ollama
  ○ OpenRouter
  ○ Others ▾
  ```
  These five are shown as radios because they cover the vast majority of use cases and are the ones users will reach for first. Selecting any of the first five immediately renders that provider's input form below the radios.

  Selecting **Others** renders a searchable dropdown listing every remaining provider, grouped by tier:
  ```
  Others ▾
  ┌─────────────────────────────────┐
  │ Cloud / Enterprise              │
  │   Google Gemini                 │
  │   Google Vertex AI              │
  │   Azure OpenAI                  │
  │   AWS Bedrock                   │
  │ Aggregators / Routers           │
  │   Groq                          │
  │   Together AI                   │
  │   Fireworks AI                  │
  │   DeepSeek                      │
  │   Perplexity                    │
  │   SambaNova                     │
  │ Specialist APIs                 │
  │   Mistral                       │
  │   Cohere                        │
  │   Voyage AI                     │
  │   HuggingFace                   │
  │   Replicate                     │
  │   ElevenLabs                    │
  │   Cartesia                      │
  │   Runway                        │
  │   Suno                          │
  │   Deepgram                      │
  │   fal.ai                        │
  └─────────────────────────────────┘
  ```
  Selecting any option from the dropdown immediately renders that provider's input form below, replacing the dropdown (the radio for "Others" stays selected so the user knows where they are).

  **Input forms per provider type** (appear below the radio/dropdown selection; only the fields that provider actually needs):
  - **Anthropic** → Name (pre-filled "Anthropic"), API Key.
  - **OpenAI** → Name (pre-filled "OpenAI"), API Key, optional Org ID.
  - **OpenAI-compatible** → Name, Base URL, optional API Key, optional API Version header.
  - **Ollama** → Name (pre-filled "Ollama"), Base URL (default `http://localhost:11434`, editable). No key field.
  - **Google Gemini** → Name, API Key (AI Studio).
  - **Google Vertex AI** → Name, GCP Project ID, Region, Service Account JSON (paste box).
  - **Azure OpenAI** → Name, Deployment Base URL, API Key, API Version.
  - **AWS Bedrock** → Name, Region, Access Key ID, Secret Access Key; toggle "Use instance profile / IAM role" hides the key fields.
  - **OpenRouter** → Name (pre-filled "OpenRouter"), API Key. Base URL locked to `https://openrouter.ai/api/v1`.
  - **Groq** → Name (pre-filled "Groq"), API Key. Base URL locked.
  - **Together AI** → Name (pre-filled "Together AI"), API Key. Base URL locked.
  - **Fireworks AI** → Name (pre-filled "Fireworks AI"), API Key. Base URL locked.
  - **DeepSeek** → Name (pre-filled "DeepSeek"), API Key. Base URL locked.
  - **Perplexity** → Name (pre-filled "Perplexity"), API Key. Base URL locked.
  - **SambaNova** → Name, Base URL (from SambaNova dashboard), API Key.
  - **Mistral** → Name (pre-filled "Mistral"), API Key. Base URL locked.
  - **Cohere** → Name (pre-filled "Cohere"), API Key.
  - **Voyage AI** → Name (pre-filled "Voyage AI"), API Key.
  - **HuggingFace** → Name (pre-filled "HuggingFace"), API Token. Base URL locked to `https://router.huggingface.co/v1`.
  - **Replicate** → Name (pre-filled "Replicate"), API Token, optional additional model IDs (multi-line text area, one `owner/name:version` per line).
  - **ElevenLabs** → Name (pre-filled "ElevenLabs"), API Key.
  - **Cartesia** → Name (pre-filled "Cartesia"), API Key.
  - **Runway** → Name (pre-filled "Runway"), API Key. Base URL locked.
  - **Suno** → Name (pre-filled "Suno"), API Key.
  - **Deepgram** → Name (pre-filled "Deepgram"), API Key.
  - **fal.ai** → Name (pre-filled "fal.ai"), API Key.

  All forms end with:
  - **"Test Connection"** button — live-calls the provider's health endpoint before saving; shows ✅ / ❌ inline with the raw error message on failure.
  - **"Save"** button (disabled until test passes, or skip-test toggle for power users).
  - On save: auto-discovery Celery task queues immediately; a "Discovering models…" progress banner replaces the form; model entries appear in Section C within seconds.

  **Section C — Models Table** — columns: Model ID | Provider | Capabilities (pills) | Status (healthy/unhealthy/unknown badge) | Last Checked | [Logs] | [Metrics]. Sortable by status and capability. Search/filter by capability tag.

  **[Logs] button** → slide-over panel with live SSE stream. Each line: timestamp + component badge + status dot + latency + token counts + cost. Auto-scrolls. Pause/resume button. "Clear" clears the visual buffer (not DB).

  **[Metrics] button** → slide-over panel with:
  - 4 summary cards: Total Calls (7d) · Success Rate · Avg Latency · Total Cost (USD).
  - Line chart: daily call volume over last 7 days (success vs error stacked).
  - Bar chart: calls by platform component.
  - Latency percentile bars: p50 / p95 / p99.

- **S4-M11** Model resolver service (`app/services/model_resolver.py`): resolves which specific `ModelEntry` to use for a given `(org_id, user_id, capability)` tuple. Resolution priority chain (top wins):
  1. `UserModelPreference` for `(user_id, org_id, capability)` → user's explicit selection
  2. `OrgModelAssignment` for `(org_id, capability)` → org-level default
  3. First healthy `ModelEntry` with the capability in the org-scoped pool, then global pool (lexicographic — deterministic)
  4. Env-var fallback (existing `settings.anthropic_api_key`, etc.)
  5. Deterministic stub (dev / CI / no key configured)
  All of S4-A + S4-B use the resolver. No direct `settings.*_api_key` references remain in agent code outside the fallback path.

- **S4-M12** `OrgModelAssignment` + `UserModelPreference` DB models + migration.
  - `OrgModelAssignment(id, org_id FK, capability str, model_entry_id FK, set_by_user_id FK, created_at, updated_at)` — UNIQUE(org_id, capability). Org-level default for each capability slot. Set by org-admin or superadmin.
  - `UserModelPreference(id, user_id FK, org_id FK, capability str, model_entry_id FK, updated_at)` — UNIQUE(user_id, org_id, capability). Per-user override; beats the org default. Set by any authenticated user for themselves.

- **S4-M13** Assignment / preference CRUD API.
  - `PUT /api/v1/models/org-assignments` — body: `{capability, model_entry_id}` — org-admin+ only; upserts `OrgModelAssignment` for the caller's active org.
  - `PUT /api/v1/models/user-preferences` — body: `{capability, model_entry_id}` — any authenticated user; upserts `UserModelPreference` for `(current_user, active_org)`.
  - `GET /api/v1/models/resolved-assignments` — returns the fully resolved assignment map for `(current_user, active_org)`: for each capability, which model entry was resolved and at which level (user / org / auto / fallback). Used by the Conductor settings panel and the gate hook.

- **S4-M14** Conductor model selector panel. The full-screen `/conductor` page and the docked chat panel both get a **Model Settings** collapsible section (gear icon in the dock; sidebar panel in full-screen). Layout per capability row:
  ```
  Text / Chat         [claude-sonnet-4-6  (Anthropic) ▼]  ● healthy
  Embeddings          [nomic-embed-text   (Ollama)    ▼]  ● healthy
  Image Generation    [— not selected —               ▼]  ✗ no model
  Voice (TTS)         [— not selected —               ▼]  ✗ no model
  Video Generation    [— not selected —               ▼]  ✗ no model
  Music Generation    [— not selected —               ▼]  ✗ no model
  Audio Transcription [— not selected —               ▼]  ✗ no model
  ```
  Each dropdown is populated with all `ModelEntry` rows that: (a) are healthy, (b) belong to the org's pool (org-scoped + global), (c) have the required capability. Each option shows `{display_name} ({provider_name})`. Options from multiple providers of the same type all appear — e.g., if there are two Anthropic providers, all their models show up labelled. Selecting a model calls `PUT /api/v1/models/user-preferences` immediately (no save button needed). A status dot next to each row reflects the resolved model's current health in real-time (polling the feature-availability endpoint). "Manage Providers" link → `/admin/models`.

- **S4-M15** Model gate hook + onboarding flow. Frontend React hook `useModelGate(capability: string)` available globally.

  **First-visit onboarding modal** (shown when user has zero preferences set AND visits any page that triggers a model-dependent action, OR when the user opens `/conductor` for the first time):
  ```
  ┌──────────────────────────────────────────────────────────┐
  │  Set up your AI models                                    │
  │  Choose which model handles each task for your workspace. │
  │  You can change these anytime from Conductor settings.    │
  │                                                           │
  │  Text & Chat  *required*  [— choose model ▼]             │
  │  Embeddings               [— choose model ▼]             │
  │  Image Generation         [— optional ▼]                 │
  │  Voice (TTS)              [— optional ▼]                 │
  │  Video Generation         [— optional ▼]                 │
  │  Music Generation         [— optional ▼]                 │
  │  Audio Transcription      [— optional ▼]                 │
  │                                                           │
  │  ⚠ No models available for Image Generation.             │
  │    Ask your admin to add a provider → /admin/models       │
  │                                                           │
  │  [Skip for now]           [Save & Start]                  │
  └──────────────────────────────────────────────────────────┘
  ```
  "Save & Start" is disabled until at least `text` is assigned. Dropdowns only show healthy available models; capabilities with no models show a greyed-out "No provider configured" message + link. "Skip for now" closes the modal and stores a `dismissed_at` timestamp in localStorage; if the user skips and later tries to use Conductor or any model-dependent feature, the inline gate fires.

  **Inline capability gate** (shown when any action requiring a specific capability is triggered with no model assigned for that capability, and the first-visit modal has already been dismissed):
  ```
  ┌──────────────────────────────────────────────────────┐
  │  Image Generation model required                      │
  │                                                       │
  │  This action needs an image generation model.        │
  │  Select one to continue:                              │
  │                                                       │
  │  [— choose model ▼]  (only image_generation models)  │
  │                                                       │
  │  No models available?                                 │
  │  → Ask your admin to add a Replicate or OpenAI key   │
  │    in /admin/models                                   │
  │                                                       │
  │  [Cancel]            [Select & Continue]              │
  └──────────────────────────────────────────────────────┘
  ```
  "Select & Continue" saves the preference and re-triggers the original action. The hook is called at every model-dispatch site in the frontend (generation forms, repurpose triggers, brand studio, etc.).

  **Conductor partial unlock:** once `text` is assigned, the Conductor chat input unlocks and the user can type. If the Conductor's tool-call plan includes an action that requires an unassigned capability (e.g. image generation), the Conductor's tool-call response card shows an inline "Select model for this action" prompt before proceeding.

- **S4-M16** Inline model selectors on action pages. Every page/form that triggers a model-dependent action gets a small "Model" selector chip showing the currently resolved model, clickable to change:
  - `/agents/creatives` — "Text model" chip in the generation form header.
  - `/campaigns/[id]/generate` — per-kind model chip: "Text: claude-sonnet-4-6 ▾ | Image: — ▾".
  - `/repurpose` — "Transcription model" chip (shown only when source is audio/video).
  - `/brand` (Brand Setup Studio) — "Vision model" chip for PDF/logo analysis step.
  - `/agents/seo` — "Text model" chip for AEO scorer and blog draft.
  Clicking a chip opens a compact dropdown (same options as Conductor panel). Selection calls `PUT /api/v1/models/user-preferences` and the action re-resolves immediately.

**Definition of done**
- Superadmin can add 3 separate Anthropic providers simultaneously; all their models appear in the same assignment dropdowns labelled by provider name.
- Adding an org-scoped Replicate API key makes Image Generation go from ✗ to ✅ for that org, and the Conductor panel's Image Generation row shows the new models immediately.
- Feature Availability matrix on `/admin/models` accurately reflects both what is registered and what is assigned.
- First-visit modal appears the first time a user opens `/conductor` with no preferences set; "Save & Start" unlocks after selecting a text model.
- Inline gate fires correctly when a user attempts image generation with no image model assigned.
- Inline model selector chips appear and are functional on: `/agents/creatives`, `/campaigns/[id]/generate`, `/repurpose`, `/brand`, `/agents/seo`.
- Resolver correctly honours user preference → org default → auto-pick → stub priority chain.
- Live model logs stream within 2s of a model call anywhere on the platform.
- Metrics show 7-day call volume, cost, and latency percentiles per model.

---

#### S4-H. Observability dashboards **(P1)**
**Stories**
- **S4-H1** Grafana board for request latency / error rate / quota usage / cost.
- **S4-H2** Sentry wired with org/user tags so reports filter by tenant.
- **S4-H3** `/admin/health` shows worker queue depth + last-beat time.
- **S4-H4** OpenTelemetry → OTLP endpoint configurable for tenant observability.

---

#### S4-I. Documentation + user-guide refresh **(P1)**
**Stories**
- **S4-I1** `docs/USER-GUIDE.md` walks an operator end-to-end from clean stack to first published post via the Conductor.
- **S4-I2** PDF export of the user guide.
- **S4-I3** ARCHITECTURE.md updated with the agent fleet + Conductor tool list + workflow runner.

---

#### S4-J. Tech-debt cleanup **(P1 / P2)**
**Stories**
- **S4-J1** v1 legacy router consolidation — fold under v2 surface, deprecate old paths.
- **S4-J2** Audit retention pruner — Celery beat task that prunes `audit_events` older than N days (per-org config).
- **S4-J3** Webhook signature key-id versioning.
- **S4-J4** Playwright frontend smoke test suite (golden-path coverage of the Conductor demo flow).

---

#### S4-K. AEO — Answer Engine Optimization **(P1 stretch)**

**Why now:** Sitefire (YC W2026) is funded specifically for this problem. HubSpot launched AEO in its Spring 2026 Spotlight. The market is moving from traditional SEO (rank in Google) to AEO (appear in ChatGPT / Perplexity / Claude answers). DClaw's existing SEO pipeline (H2 — Ahrefs MCP + blog pipeline) is 80% of the infrastructure needed. Adding AEO scoring here is a meaningful differentiator with low incremental cost.

**What AEO is:** Optimising content so that AI search engines cite or surface it. Unlike traditional SEO (keyword density, backlinks), AEO focuses on: structured data / schema.org markup, FAQ-format fragments, entity clarity (does the content clearly name the product/company/people?), direct-answer density (does the content contain crisp, quotable sentences?), and authority signals (citations, expert attributions).

**Stories**
- **S4-K1** AEO scorer service (`app/services/aeo_scorer.py`): given a URL or `Asset` (blog draft), runs the following checks:
  - **Entity clarity score** — NLP entity extraction via Claude (already available) to check product name, company, people mentions are consistent and unambiguous.
  - **Direct-answer density** — count short (≤25-word) standalone declarative sentences that directly answer likely queries.
  - **Schema markup presence** — check for `application/ld+json` blocks with `Article`, `FAQPage`, `HowTo`, `Product` schemas.
  - **FAQ fragment count** — count question + answer pairs in the content.
  - **Citing authority** — check for external citations / links to authoritative sources.
  - Returns an `AEOReport {overall_score: 0-100, breakdown: {entity_clarity, direct_answer_density, schema_markup, faq_fragments, authority_signals}, suggestions: [str]}`.
- **S4-K2** API endpoint: `POST /api/v1/seo/aeo-score {asset_id? url?}` → `AEOReport`. Runs as a Celery task for async scoring; result cached in `Asset.metadata_json`.
- **S4-K3** AEO widget in `/agents/seo`: "AEO Score" card alongside the existing SEO metrics. Shows the overall score (0–100 gauge), breakdown bars, and top 3 improvement suggestions. "Re-score" button re-triggers the Celery task.
- **S4-K4** Batch AEO audit: `POST /api/v1/seo/aeo-audit {project_id}` → queues scoring for all published blog assets in the project. Results appear in the Content Performance Heatmap (F2) as an additional dimension.
- **S4-K5** (stretch) AI-powered fix suggestions: if the Claude model for `text` is available (via S4-M resolver), auto-generate a revised FAQ section or suggested schema markup JSON for the operator to copy-paste.

**Definition of done**
- Pasting a blog URL into the AEO widget returns a scored report in <10s (async job).
- Batch audit of a 10-article blog project completes in <2 min.
- AEO scores appear in the heatmap alongside existing SEO metrics.

---

### Sprint 4 — out of scope (defer to Sprint 5+)
- B7 Brand-Safe Image Editor
- C5 SMS / WhatsApp
- C6 Push / In-App
- F3 Competitor Tracker
- F4 Customer-Voice Mining
- H3 Topic Cluster Map
- O Client Portal
- G3 Trend Radar / G4 Comment Triage / G5 Auto-Optimizer (advanced bandit)
- Full visual drag-graph Workflow Builder (P) — Sprint 4 ships template clone/edit; full builder is Sprint 5+
- Sandbox / dry-run UI polish (mechanism exists; full UX is Sprint 5)

### Sprint 4 — exit criteria for `v1.2.0`
- **Model Registry live:** superadmin can configure Anthropic + OpenAI + Ollama + OpenAI-compatible providers; Feature Availability matrix accurately reflects what is and isn't possible; live model logs + metrics visible per model.
- Conductor controls the platform end-to-end from one chat.
- ≥ 3 channels publish real posts via real OAuth against a staging Org.
- ≥ 4 generation MCPs (text · image · video · voice) wired with real keys + cost ledger reconciliation.
- 5 workflow templates run dry-run and 1 runs live.
- TOTP enrollment surfaced.
- Observability dashboards exposed to the operator.
- AEO scorer live in `/agents/seo` with batch audit capability.
- Marketing collateral (operator-owned) ready alongside.

---

## Sprint 5 Plan — Conductor consolidation & top-of-the-line agentic chat

> **Headline (2026-05-15).** Sprint 5 is NOT a new-features sprint. It is a fix-and-elevate sprint with one focused epic: make the Conductor the unmistakable flagship of the platform. Today the Conductor is split across two sidebar entries pointing at two different page UIs, and the newer features have only landed on the "Conductor → Conductor" path while the "Work → Conductor" path is a stale chat wrapper. Sprint 5 fixes that and pushes Conductor to Claude/ChatGPT-parity — agentic, streaming, vision-capable, web-aware, voice-enabled, operating every feature on the platform from a single chat surface.
>
> **Why it matters.** The whole pitch of DClaw is "agentic chatbots that chat AND operate every marketing operation on the same platform." If the Conductor is not the best-in-class entry point for that, the platform has no center of gravity. Sprint 5 makes the Conductor the center.
>
> **Posture.** No new features outside the Conductor surface. Every other backlog item waits. PRs ship one issue at a time, in order; each PR must pass local tests, push, auto-merge, then move the issue to Done and rebuild the affected docker servers before the next issue starts.

### Sprint 5 epic — Conductor (issues #347–#353)

| # | ID | Issue | Priority | Track |
|---|----|-------|----------|-------|
| #347 | **S5-CDR-A** | Sidebar + page unification — single Conductor under Work at `/conductor`; `/agent` redirects; ModelSettingsPanel visible at page level; widget untouched. | P0 | code |
| #348 | **S5-CDR-B** | Drag-and-drop file/folder upload + image paste + Claude vision; `AgentMessage.attachment_ids`; KG ingestion of doc attachments. | P0 | code |
| #349 | **S5-CDR-C** | Claude Agent SDK swap + **maximum** tool fleet (~40 tools) covering every sidebar feature so Conductor operates the entire platform via chat. Inline tool-call cards. | P0 | code |
| #350 | **S5-CDR-D** | SSE streaming responses + stop-generation + extended-thinking mode toggle. | P1 | code |
| #351 | **S5-CDR-E** | `web_search` + `fetch_url` tools + Quick / Light Research / Deep Research mode toggle with multi-step research orchestrator. | P1 | code |
| #352 | **S5-CDR-F** | Polish: voice input, prompt library, slash-command palette, copy/regen/edit, thread rename/pin/delete, markdown + code-block syntax highlighting, suggested-prompts empty state. | P2 | code |
| #353 | **S5-CDR-G** | This plan-doc update. | P2 | docs |

### Sprint 5 — exit criteria for `v1.2.1`

- Left sidebar has **one** Conductor entry, under "Work", routing to `/conductor`. The widget (`agent-dock`) is intact and unchanged.
- The unified `/conductor` page renders chat (primary) + decomposition/results panel (collapsible) + visible `ModelSettingsPanel`.
- An operator can drag-drop a folder of files (or paste images) into chat, and the Conductor can reason about them (Claude vision for images, KG-ingest summaries for docs).
- Conductor runs on the Claude Agent SDK with a tool fleet that covers every sidebar surface; any "do X on the platform" request resolves to a tool-call (and is rendered as an inline card in the message).
- Conductor responses stream token-by-token with a working stop-generation button; users can toggle Extended Thinking.
- Users can pick Quick / Light Research / Deep Research; Deep mode produces multi-source, multi-step answers with cited sources.
- Polish parity with Claude.ai / ChatGPT: voice input, prompt library, slash commands, copy/regen/edit message ops, markdown + syntax-highlighted code, thread rename / pin / delete.

### Sprint 5 — out of scope (defer to Sprint 6+)

- Any non-Conductor feature work (those backlog items stay where they are).
- MCP-style external tool federation beyond the in-process tool router (Sprint 6+).
- Multi-agent collaboration UI (multiple agents visible in one thread) — keep Conductor as the single orchestrator surface for now.
- Image generation rendered inline in chat (uses #C's `generate_creative` tool to drop the image into the Library; inline gallery preview is Sprint 6 polish).

## What "Done" Looks Like for v1.2

- An operator can sign up, connect 5+ MCP integrations, write a one-paragraph campaign brief, hit "generate," review 12 multimedia variants in their brand voice/visuals, schedule a 4-week multi-channel rollout from one calendar, get a daily dashboard of reach + engagement + leads + revenue, and let an agent draft the next week's content while they sleep — all in light mode, all on Poppins, all in brand purple.

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
- Zero hardcoded hex anywhere; everything in brand purple; all `--dk-*` design-kit tokens; light mode only.

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
| Styling | **Tailwind CSS** + `frontend/src/styles/brand.css` (DClaw design-kit tokens; light-mode only; **no `dark:` variants**) |
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


## A.11 Future planning — Auth surface beyond v1.2

These are NOT in scope for the current sprint. Listed here so the
work isn't lost when the v1.2-rc1 release closes.

**Core principle:** the only account that can self-recover is the
**admin** (single bootstrap superuser per install). Every other user's
password is **always reset by admin** — there is no self-serve
"forgot password" path for non-admin users. This matches the
agency-as-customer model: the agency owns user lifecycle, the platform
owner owns admin recovery.

### A.11.1 Admin-only password recovery flow

**Current state (May 2026):** The bootstrap admin's password is hardcoded
in ``backend/app/core/config.py`` (``bootstrap_admin_temp_password``)
and re-asserted on every backend startup via ``init_db()``. This is the
"lost admin password" recovery path today — operator edits the config
and restarts the backend.

**Future scope (admin user only):**

1. **Forgot-password endpoint** — POST ``/api/v1/auth/forgot-password``
   takes an email. **Checks ``user.is_superuser`` first**: if False,
   silently returns 202 and emits an audit row but does NOT send an
   email. If True, generates a single-use, time-bound (15-min) reset
   token and sends an email to that admin address containing
   ``$ORIGIN/reset?token=…``. Always returns 202 to the caller (no
   enumeration of admin vs non-admin).
2. **Reset-password endpoint** — POST ``/api/v1/auth/reset-password``
   takes ``{token, new_password}``. Validates the token (signature,
   expiry, single-use marker, ``user.is_superuser`` still True).
   Updates ``hashed_password``. Audit event written either way.
3. **Frontend** — ``/forgot`` page (email form). The page copy reminds
   non-admin users to contact their admin. ``/reset?token=…`` page
   (new password + confirmation). Both behind ``DkPageHeader``, pure
   DKube tokens, light-mode only.
4. **Email template** — short transactional email via the existing
   send chain (SendGrid → Postmark → Resend). Subject:
   "Reset your DClaw admin password". Body: greeting + 1 click-through
   CTA + plain-text fallback URL + 15-min expiry notice + a footer
   reminding them this is an admin-only flow.
5. **Token shape** — JWT signed with ``settings.jwt_secret`` containing
   ``{sub: user_id, purpose: "admin_password_reset", jti: <uuid>, exp: ts}``.
   ``jti`` recorded in a small ``password_reset_tokens`` table so each
   token is single-use. The ``purpose`` claim is checked on consume
   so the token can't be repurposed for non-admin resets.
6. **Rate-limit** — at most 3 forgot-password requests per admin email
   per hour (uses the existing sliding-window QuotaCounter primitive).
7. **Backwards compat** — the hardcoded re-assert path stays for
   emergency recovery in case the email provider is down. Documented
   as such.

**Acceptance:** an admin who has forgotten their password can recover
it without any backend restart. Non-admin users get a 202 + nothing
sent (covered by an integration test).

### A.11.2 Admin-mediated user-password reset

The mirror flow for every non-admin user: an admin clicks "reset
password" on the user's row in ``/admin/users`` → backend generates a
new temp password, emails it to the user (or shows it to the admin
in-band — both modes supported), and sets ``password_reset_required=True``
on the user so they're forced through a first-login change.

**Future scope:**

1. **Endpoint already exists** — POST
   ``/api/v1/admin/users/{id}/reset-password`` (admin-only) is the
   existing primitive. The follow-up here is the email-delivery
   piece + the UI button.
2. **Email template** — separate from the admin recovery email.
   Subject: "Your DClaw account — temporary password". Body: the temp
   password + the login URL + a reminder that they'll be asked to
   change it on first login.
3. **Frontend** — Reset-password button on each row in
   ``/admin/users``; opens a small confirm dialog that lets the admin
   pick "email the user" or "show me the temp password and I'll
   share it manually".

### A.11.3 Email-based authentication / magic links (admin only)

Optional follow-up after A.11.1.

**Concept:** the **admin** types email → backend emails a magic-link →
click-through logs them in for the session. No password.

**Critical scope note:** this is **admin-only**. Non-admin users still
must use the admin-provisioned password + admin-mediated reset flow.

**Future scope:**

1. **Request endpoint** — POST ``/api/v1/auth/magic-link`` with
   ``{email}`` → emails a one-time JWT good for one login.
   ``user.is_superuser`` check identical to the forgot-password flow.
   Same "always 202, no enumeration" pattern.
2. **Consume endpoint** — GET ``/api/v1/auth/magic-link?token=…``
   validates + sets the session (issues a standard JWT cookie + a
   refresh-token row), then 302s to ``/``.
3. **Co-existence with passwords** — both flows work for admin. The
   user table gains an optional ``preferred_auth`` field for admin
   accounts only.
4. **Reuse the password-recovery email template chain.**

### A.11.4 SSO / OIDC (deferred indefinitely)

Already covered in §A.10. Re-stated here so the auth roadmap is
contiguous: Google / Microsoft Entra / Okta / generic OIDC. Triggers
when the first agency-customer asks for it.

### A.11.5 Out of scope even for these themes

- **Self-service signup** — explicitly out for v2.0 (§A.10) and for the
  forseeable future. Admin creates every user.
- **Forgot-password for non-admin users** — explicitly out per the
  core principle above. Admin handles those resets in §A.11.2.
- **Hardware token auth** (FIDO2 / WebAuthn) — too niche for the
  agency-customer profile.
- **TOTP 2FA** — defer to A.11.6 below.
- **SMS-based recovery** — explicitly out (carrier surface area too
  large, fraud risk too high; magic-link is the only alt-auth path).

### A.11.6 2FA / TOTP (future, separate from A.11.1–4)

Optional later: opt-in TOTP enrolment for the admin only, scratch
codes. Out of scope for the email-auth roadmap; tracked separately
when a customer asks.

---

# Appendix B — Implementation Phase Breakdown

> Locked 2026-05-12. Pair-read with the feature spec above. Every Epic, Story, and Task on the GitHub Project board references a section below.

## Scope

- Build the **full v1.2 / v2.0 promise** end-to-end. No deadline cap.
- Every operator workflow runs **from the UI**, not the CLI. Curl recipes in `docs/USER-GUIDE.md` exist only as developer references; the product itself never asks an operator to open a terminal.
- Apply the **DClaw design kit** correctly across every screen — `--dk-*` tokens (where `dk` = "design kit"), `.dk-*` semantic classes, Poppins, light-mode only.
- DClaw Marketing is a standalone product brand. No parent-brand attribution in the product UI.

## Design system — already in place

The historical design ingest under `design/source/` provided the visual system that's already mirrored in `frontend/src/styles/brand.css`. The gap was application: existing pages used generic Tailwind classes instead of the brand vocabulary. Phase 0 fixes that before any new screen ships.

Reference materials in `design/source/project/`:

| Path | Use |
|---|---|
| `BRAND_GUIDELINES.md` | Voice, logo, color, type, components, motion rules |
| `colors_and_type.css` | Token definitions — already mirrored in `frontend/src/styles/brand.css` |
| `preview/*.html` | Component reference cards — eyeball every `<Dk*>` against these |
| `slides/` | Slide master layouts + arch diagram primitives |

---

## Phase map (12 phases)

Each Phase = one **Epic issue** on the project board. Stories and Tasks roll up into their Epic.

> **Sprint cadence (as executed).** Phase 0 + Phase 1 backend + Phase 2 backend + Phase 3 (Creatives Agent) + Phase 4 + parts of Phase 11 landed in **Sprint 1 (v1.0.0)**. Phase 5 + Phase 6 + Phase 7 + Phase 8 + Phase 10 + most of Phase 11 + Theme D4 + Theme H landed in **Sprint 2 (v1.1.0)**. The SP3-* polish lane (all 24 themes) + two-tier admin model + universal slug scheme + left-sidebar nav + auto-merge / auto-close pipeline landed in **Sprint 3 (v1.1.1)**. **Phase 9 (Agent Fleet — real runtime) + Q1 Brand Studio polish + S4-B real generation MCPs + S4-C Conductor controller + S4-D live workflow runs are Sprint 4 (v1.2.0).** See the "Sprint 4 Plan" section above for the breakdown.

### Phase 0 — Design Ground Truth & Component Library
**Why first:** every Phase 1+ screen should be born using the design vocabulary. Retrofitting later is wasteful.

**Stories:**
- 0.1 Import brand assets into `frontend/public/brand/` (logos, icons, customer logos, pillar imagery)
- 0.2 Tailwind token binding (`tailwind.config.ts`) — `bg-brand`, `bg-ink`, `text-fg-1`, `border-brand`, `shadow-brand`, `rounded-pill` map to `--dk-*`; disable `dark:` variants; Poppins as the only sans family
- 0.3 `<Dk*>` component library — `<DkButton>` (pill, primary/secondary/ghost), `<DkCard>` (soft shadow + hover lift), `<DkChip>`, `<DkInput>`, `<DkSelect>`, `<DkTextarea>`, `<DkTable>`, `<DkBadge>`, `<DkDialog>`, `<DkTabs>`, `<DkToast>`, `<DkEyebrow>`, `<DkAvatar>`, `<DkSlider>`, `<DkSwitch>`, `<DkCheckbox>`, `<DkRadioGroup>`, `<DkProgress>`, `<DkSkeleton>`, `<DkEmptyState>`, `<DkPageHeader>`, `<DkBreadcrumb>`, `<DkSidebar>`
- 0.4 `/_design` reference page (admin-only) rendering every component variant — eyeball-comparable with the design's `preview/*.html`
- 0.5 Refactor existing pages to the new vocabulary: login, first-login, dashboard, admin/users, agents/creatives, inbox, campaigns, leads
- 0.6 DClaw logo in nav + favicon
- 0.7 Top-level shell rebuild — sticky header, max-width 1280px container, brand-tinted hover states, motion easing
- 0.8 Voice + casing audit — strip emojis / exclamations from copy; apply Title Case to headings; em-dashes for hard pivots

---

### Phase 1 — Multi-Tenant Foundation (Theme A1, v2.0 §1-2)
**Backend status:** ✅ Done (v1.0.0); hardened in v1.1.1 (two-tier admin, slug scheme, last-admin guard).
**UI status:** ✅ Done — `/admin/users`, `/orgs`, `/orgs/[id]` tabbed detail, Project Setup Wizard, left-sidebar nav.

**Stories:**
- 1.1 Org switcher in top nav; org context wired into client + every API call
- 1.2 `/orgs` list + create + edit + delete
- 1.3 `/orgs/[id]` detail with tabs (Overview / Members / Brand / Knowledge / Goals / Projects)
- 1.4 `/orgs/[id]/members` — invite by email, assign one of the 10 supervision-scope roles (admin / manager / creatives / smm / seo / paid_media / reviewer / analyst / viewer / client), remove
- 1.5 `/orgs/[id]/projects` list
- 1.6 Project Setup Wizard (Q6) — 4-step modal: name + goals → channels → team assignments → trust mode override
- 1.7 `/settings/profile` (name, email, avatar)
- 1.8 `/settings/password` (change password)
- 1.9 `/admin/users` polish — apply design
- 1.10 `/admin/audit-log` — paginated, filterable list of all `AuditEvent` rows
- 1.11 Per-page org-context guard + 403 page

---

### Phase 2 — Theme Q: Brand & Context Ingestion
**Backend status:** ✅ Done (brand-kits, ingest, KG, goals).
**UI status:** 🟡 Partial — Q2 / Q3 / Q4 / Q6 shipped. **Q1 Brand Setup Studio polish is Sprint 4 P0.**

**Stories:**
- 2.1 **Q1 Brand Setup Studio** — `/orgs/[id]/brand`
  - Palette: color pickers for primary / secondary / surfaces / ink (defaulted to brand purple)
  - Type: font picker (default Poppins), weight presets, headline/body samples
  - Voice sliders: formal↔casual, technical↔witty, calm↔energetic
  - Do-say / don't-say lists with add/remove chips
  - Persona builder: cards with name + JTBD + fears + desires
  - Version history with diff view + "Set Active" per version
  - Live preview pane showing a generated post in this brand
- 2.2 **Q2 Input Channel Hub** — `/orgs/[id]/knowledge/sources`
  - URL crawler (sitemap walk, depth limit, include/exclude)
  - File upload (drag-drop, presigned PUT, PDF / DOCX / PPTX / MD / images / SVG / CSV)
  - Git repo clone (URL + branch + path filter)
  - Zip archive upload
  - Per-source status, last-crawled, item count
- 2.3 **Q3 Knowledge Graph** — `/orgs/[id]/knowledge`
  - Document list with kind + status + chunk count
  - Per-document chunks viewer with embedding metadata
  - Semantic search test panel (query → top-K with relevance scores)
  - Stats: docs, chunks, embedding model, total tokens, last refresh
- 2.4 **Q4 Freshness & Re-ingestion** — `/orgs/[id]/knowledge/schedule`
  - Cron per source
  - Diff highlights when content changes (added / removed / modified chunks)
  - "Subscribed agents notified" indicator
- 2.5 **Q5 Goals & Autonomy Posture** — `/orgs/[id]/goals`
  - Business objectives (leads / revenue / awareness) with sliders
  - ICPs picker (multi-select from personas)
  - Brand-safety lines (multi-line textarea + chips)
  - Monthly budget per channel
  - Trust mode picker per action class (Autopilot / Soft / Hard) with override resolver visualization
- 2.6 **Q6 Project Setup Wizard** moved here (also referenced in 1.6) — full flow with project-level brand override + KG inheritance toggle

---

### Phase 3 — Content Generation Pipeline (Theme B)
**Backend status:** 🟡 Partial — Creatives Agent + Assets + B4 Repurpose + B5 A/B Variants + B6 Hook Lab shipped (v1.0.0–v1.1.1). **Image / video / voice / music providers are Sprint 4 P0 (S4-B).**
**UI status:** 🟡 Partial — `/repurpose`, `/variants`, `/hooks`, `/heatmap`, `/library` shipped. Studio Station polish + live preview pane are Sprint 4.

**Stories:**
- 3.1 **B2 Brief editor** — `/projects/[id]/briefs/new`
  - Markdown body + structured fields (objective, hypothesis, target persona, channels, KPIs)
  - Template library (B8) — Copy.ai-style 50+ presets per channel
- 3.2 **B2 Campaign Kanban** — `/campaigns/[id]`
  - Stages: Brief → Generate → Review → Schedule → Live → Report
  - Drag-and-drop between stages with audit logging
- 3.3 **B3 Generation backend adapters**
  - `app/services/generation/text/` — Claude / OpenAI (extend existing)
  - `app/services/generation/image/` — Replicate / Flux / Imagen
  - `app/services/generation/video/` — Runway / Veo / Sora-shape
  - `app/services/generation/voice/` — ElevenLabs / Cartesia
  - `app/services/generation/music/` — Suno / Udio
  - `GenerationRequest` model + lint pass that re-runs on `dont_say` violations + cost tracking
- 3.4 **B3 Generation Station** — `/campaigns/[id]/generate`
  - Kind picker (text / image / video / voice / music)
  - Persona picker from active Brand Kit
  - Prompt builder with template starter
  - Live WS / SSE progress
  - Thumbnail wall with regenerate + edit-prompt-and-retry
- 3.5 **B4 Repurposing Engine** — `/library/[asset]/repurpose`
  - Transcribe (Whisper / Deepgram) for video / audio sources
  - Chapterization + high-energy segment picker
  - Channel-shaped output variants (X thread, LinkedIn carousel PDF, IG reel, YouTube short, TikTok hook, newsletter blurb, SEO meta)
  - FFmpeg + ASS subtitle render
- 3.6 **B5 A/B Studio** — `/campaigns/[id]/ab`
  - Variant gallery with weights
  - Real-time win-rate
  - Auto-promote winner toggle
- 3.7 **B6 Hook & Headline Lab** — `/labs/hooks`
  - Paste draft → 30 hook variants ranked by historical CTR for this workspace
- 3.8 **B7 Brand-Safe Image Editor** *(P2)* — `/editor/[asset_id]`
  - Brand-locked palette + font
  - Layers, text, masks
  - Generative inpainting through the same providers
- 3.9 **A3 surface — Asset Library DAM** — `/library`
  - Grid view with filters (kind / source / brand kit / status)
  - Thumbnail lazy load
  - Search across `Asset.metadata`
  - Presigned download

---

### Phase 4 — Calendar & Scheduling (Theme C1)
**Backend status:** ✅ Done (v1.0.0): ScheduledPost + Celery beat dispatcher + conflict detection.
**UI status:** ✅ Done — `/calendar`.

**Stories:**
- 4.1 `ScheduledPost(workspace_id, channel_id, asset_ids[], copy, scheduled_at, status, parent_campaign_id, tags[])` model + repository
- 4.2 Celery beat scanner — dispatch posts when `scheduled_at <= now AND status='queued'`
- 4.3 Conflict detection — block two LinkedIn posts within 60 min on the same account
- 4.4 Best-time-to-post recommender — per-channel historical engagement model
- 4.5 `/calendar` UI — FullCalendar-style, themed, channel-color-coded chips, day/week/month, "publish now" action, drag-to-reschedule

---

### Phase 5 — Multi-Account Multi-Channel Publishing (Theme C2, v2.0 §6)
**Backend status:** ✅ Done (v1.1.0): SocialAccount + per-account rate limits + 7-provider OAuth scaffold + 13 channel adapters (X / LinkedIn / IG / FB / YouTube / TikTok / Threads / Substack / Bluesky / Reddit / Pinterest / Discord / Mastodon). Fernet-encrypted tokens via per-Org data key (v1.1.1, SP3-6).
**UI status:** ✅ Done — `/channels` connect/disconnect + status. **Real OAuth client credentials are Sprint 4 P0 (S4-F).**

**Stories:**
- 5.1 `SocialAccount` model — multi-account per platform per Org; `(organization_id, platform, handle)` uniqueness; OAuth-grant per account
- 5.2 OAuth flows + publisher adapter for each platform:
  - 5.2.1 X / Twitter
  - 5.2.2 LinkedIn personal + LinkedIn company
  - 5.2.3 Instagram Feed + Reels + Stories
  - 5.2.4 Facebook Page
  - 5.2.5 YouTube Shorts + YouTube long
  - 5.2.6 TikTok
  - 5.2.7 Threads
  - 5.2.8 Reddit
  - 5.2.9 Pinterest
  - 5.2.10 Bluesky
  - 5.2.11 Mastodon
  - 5.2.12 Snapchat
  - 5.2.13 Telegram channels
  - 5.2.14 WhatsApp Business
  - 5.2.15 Discord server announcements
  - 5.2.16 Quora
  - 5.2.17 Medium
  - 5.2.18 Substack
  - 5.2.19 Beehiiv
  - 5.2.20 Ghost
  - 5.2.21 WordPress
  - 5.2.22 Webflow CMS
  - 5.2.23 Spotify for Podcasters
- 5.3 Channel-aware payload shaping (image specs / character limits / hashtag rules / link preview)
- 5.4 Rate-limit guard + exponential retry on 5xx
- 5.5 Per-account health monitoring + auto-reconnect prompts
- 5.6 `/channels` UI — connected accounts grid, last-publish status, error history
- 5.7 `ProjectSocialAccount` join — projects pick a subset of the Org's accounts

---

### Phase 6 — MCP Integration Hub (Theme D)
**Backend status:** ✅ Done (v1.1.0): Connection registry, async MCP client, Fernet-encrypted secrets, 14 concrete adapters (HubSpot / GA4 / Stripe / Ahrefs / Webflow / WordPress / Ghost / Slack / Discord / Notion / Google Drive / Salesforce / Mixpanel / PostHog) + BYO marketplace (v1.1.1, SP3-15) + Theme D4 webhook hub + Automation rules.
**UI status:** ✅ Done — `/integrations` grid + `/integrations/byo`. **Generation MCPs (Replicate / Runway / Suno / ElevenLabs / Cartesia / Deepgram) are Sprint 4 P0 (S4-B).**

**Stories:**
- 6.1 `Connection(workspace_id, server_id, name, kind, auth_type, encrypted_secret_blob, scopes[], status, last_health_at)` + `MCPServer` registry
- 6.2 Fernet-encrypted secret store keyed off per-Org data key (per-Org key encrypted with master KMS key)
- 6.3 Async MCP client (`app/services/mcp/client.py`) — tool-call dispatcher with retry + audit logging
- 6.4 Built-in MCP servers / adapters for ~30 providers:
  - **Social** — X / LinkedIn / IG / FB / YouTube / TikTok / Threads / Bluesky / Reddit / Pinterest
  - **Generation** — Anthropic / OpenAI / Replicate / Runway / Suno / ElevenLabs / Cartesia / Deepgram
  - **Editing / DAM** — Figma / Adobe Express / Canva / Frame.io
  - **Hosting** — Cloudflare Stream / Mux / S3 / R2
  - **CRM** — HubSpot / Salesforce / Pipedrive / Attio / Apollo / Clearbit
  - **Analytics** — GA4 / Mixpanel / Posthog
  - **CMS** — Webflow / WordPress / Ghost / Beehiiv / Substack
  - **Productivity** — Notion / Drive / Slack / Linear / Cal / Zoom
- 6.5 Each MCP exposes uniform tool set: `list_assets` / `get_asset` / `generate(kind, params)` / `edit(asset_id, ops)` / `export(asset_id, format)`
- 6.6 `/integrations` UI — categorized grid, connect modal, OAuth/PAT walkthrough, test-connection
- 6.7 `/integrations/byo` — BYO MCP server URL + auth; tool inspector with JSON-Schema view; per-tool allow/deny
- 6.8 `/webhooks` inbound hub — signed payload verification per source, `Automation` rule dispatch

---

### Phase 7 — Email + Ads + Sequences (Themes C3, C4, E4)
**Backend status:** ✅ Done (v1.1.0): Resend / Postmark / SendGrid + open/click/reply webhooks · Meta + LinkedIn paused-campaign create · Google Ads two-step · SequenceMembership runner + segment evaluator + nightly materializer.
**UI status:** 🟡 Partial — `/admin/email` test send + sequences API. Visual react-flow sequence builder pending.

**Stories:**
- 7.1 `EmailTemplate`, `Audience`, `EmailCampaign`, `EmailSequence` models
- 7.2 SendGrid / Resend / Postmark transactional adapters
- 7.3 Mailchimp / ConvertKit / Beehiiv / Substack newsletter adapters
- 7.4 Open / click / reply webhook ingest
- 7.5 `/email/templates` editor — rich text + merge fields
- 7.6 `/email/sequences/[id]` — react-flow visual builder (steps + delays + conditions + branches)
- 7.7 `AdAccount` / `AdCampaign` / `AdSet` / `AdCreative` models
- 7.8 Meta Ads / Google Ads / LinkedIn Ads / TikTok Ads adapters in `app/services/ads/`
- 7.9 `/ads` cross-platform table + budget planner + performance dashboard
- 7.10 `Sequence` / `SequenceStep` / `SequenceEnrollment` (outbound) — multi-step flows with channel-specific publishers
- 7.11 Audience `Segment(workspace_id, name, filter_dsl_json)` + `AudienceSync` to ad platforms

---

### Phase 8 — Lead 2.0 + CRM Sync + Attribution + Analytics (Themes E + F)
**Backend status:** ✅ Done (v1.1.0–v1.1.1): Lead 2.0 + LeadActivity + enrichment fan-out (SP3-12) + Pipedrive / Attio / HubSpot sync + daily rescore beat · Touchpoint + Conversion + time-decay attribution + `/analytics/sankey` · AnalyticsRollup + daily roll-up · F2 Content Performance Heatmap (SP3-13). **F3 / F4 deferred to Sprint 5+.**
**UI status:** ✅ Done — `/leads`, `/segments`, `/sequences`, `/analytics/attribution`, `/heatmap`, `/admin/analytics`.

**Stories:**
- 8.1 Extend `Lead` — `email`, `phone`, `domain`, `linkedin_url`, `enrichment_json`, `score`, `stage (new|mql|sql|customer|churned)`, `source`, `utm_*`, `last_activity_at`
- 8.2 `LeadActivity` + `LeadNote` models
- 8.3 Enrichment chain (`app/services/enrichment.py`) — Apollo / Clearbit / PDL via MCP, idempotent on `(workspace_id, email)`
- 8.4 CRM two-way sync — HubSpot / Salesforce / Pipedrive / Attio via MCP, writes approval-gated
- 8.5 Segment builder UI (`/segments`, `/segments/[id]`) with AND/OR groups + live count
- 8.6 `Touchpoint` + `Conversion` + `AttributionResult` models
- 8.7 Daily Celery job — first-touch / last-touch / multi-touch (linear / time-decay / Markov) attribution to closed-won
- 8.8 `/analytics/attribution` — Sankey + cohort table
- 8.9 `AnalyticsRollup(scope, key, day, metric_json)` + daily rollup job
- 8.10 **Unified analytics dashboard** — `/` redesigned with brand cards + recharts themed to brand palette, per-channel reach / engagement / conversions / spend / CAC; drill-down into any campaign or post
- 8.11 **F2 Content performance heatmap** — hooks vs CTR, post times vs engagement, persona vs conversion
- 8.12 **F3 Competitor tracker** — handles → weekly snapshots → LLM diff narrative
- 8.13 **F4 Customer-voice mining** — pull reviews / tickets / mentions → cluster themes → surface top quotes

---

### Phase 9 — Agent Fleet (v2.0 §4) — *Sprint 4 headline*
**Backend status:** 🟡 Partial — Conductor scaffold + Creatives + Analyst (weekly narrative) + SEO (depth: site audit / internal-link / ranking delta) shipped (v1.0.0–v1.1.0). **Real Claude Agent SDK runtime + tool fleet + role-Agent end-to-end is Sprint 4 P0 (S4-A, S4-B, S4-C).**
**UI status:** 🟡 Partial — `/agents/seo` + global Conductor chat dock (SP3-14). Stations and full-screen `/conductor` + reasoning-trace replay are Sprint 4.

**Stories:**
- 9.1 Swap inline LLM calls for **Claude Agent SDK** runtime; per-agent system prompts + tool list + memory
- 9.2 **Conductor Agent** + **Manager Station** (`/conductor`) — decompose brief, dispatch to role-Agents, escalation queue, budget burn-down
- 9.3 **SMM Agent** + **Calendar Station integration** — drafts + queues posts, replies to DMs in brand voice, best-time suggestions
- 9.4 **SEO Agent** + **Search Station** (`/seo`) — keyword pipeline (via Ahrefs / SEMrush MCP), topic-cluster planner, outline → draft → editorial → publish, internal-linking suggester, ranking deltas
- 9.5 **Paid Media Agent** + **Spend Station** (`/spend`) — generate ad creative, A/B tests, bandit-shifts budget, auto-kills losers
- 9.6 **Analyst Agent** + **Insights Station** (`/insights`) — daily rollups, anomaly detection, Monday-morning narrative report ("CTR on LinkedIn carousels +18% WoW driven by hook style X")
- 9.7 **Inbox Agent** — drafts replies for X / LinkedIn / IG DMs in brand voice; human one-click sends
- 9.8 **Trend Radar** (`/trends`) — daily LLM run over industry sources (RSS, X lists, Reddit, HN, GitHub trending) → 5 ranked content opportunities with hooks
- 9.9 **Auto-Optimizer** — bandit policy over Variant Sets; auto-reallocate weight to higher-performing variants once significance reached
- 9.10 **Comment Sentiment & Triage** — auto-classify incoming comments (question / complaint / praise / spam), route, suggest replies
- 9.11 Trust-mode resolver — `Org default → Project override → Channel override → Action-level override`; resolved mode shown in UI before any action fires
- 9.12 Approval Inbox upgrade — 4-eye rule (cannot approve own request), per-action reasoning trace, side-by-side variant compare
- 9.13 Reasoning trace replay UI — view any past agent decision (inputs / alternatives / confidence / tool calls / cost)
- 9.14 Docked side panel `<AgentChat>` available on every page + full-screen `/agent`

---

### Phase 10 — Themes J–P Agency Operations
**Backend status:** ✅ Mostly done — J (Org CRUD + retainer + budgets) · K (Kanban via `Project.kanban_json`, SP3-20) · L (time logs SP3-21 + retainer burn-down SP3-22 + invoices SP3-23 + QuickBooks export) · M (weekly + monthly client HTML reports + signed-JWT embeddable dashboards SP3-19) · N (Playbook search + CRUD SP3-18) · P (WorkflowRun resume + branch/approval nodes). **P visual builder UI + O Client Portal are Sprint 4–5.**
**UI status:** ✅ Done — `/time`, `/retainer`, `/invoices`, `/playbooks`, `/kanban` (per-project), `/reports`.

**Stories:**
- 10.1 **J — Client Operations** — Client / Org CRUD, onboarding wizard (collect brand assets / social accounts / persona / goals), per-Org retainers + budgets, per-Org approval workflows
- 10.2 **K — Project Management** — Project templates (Product Launch, SEO Refresh, Brand Revamp, Newsletter Reboot), Kanban + Gantt boards, task dependencies, capacity planning (per-user / per-agent utilization), milestones
- 10.3 **L — Time Tracking & Billing** — Time logs per task / campaign / Org, auto-rollup to retainer burn-down, invoice generation (Stripe + QuickBooks export), billable vs non-billable
- 10.4 **M — Client Reporting** — Auto-generated weekly + monthly PDFs, scheduled email delivery, white-label option (per-Org logo + colors), embeddable read-only dashboard URLs
- 10.5 **N — Knowledge Base & SOPs** — Reusable prompts, briefs, processes, playbooks, AI-searchable across the Org; agents propose new SOPs derived from successful patterns
- 10.6 **P — Workflow Builder** — Visual no-code chain of LLM steps + tool calls + approval gates ("on new lead from HubSpot → enrich → score → if score>80 → draft personalized intro → notify SDR"); Magic Loops / Wordware shape

---

### Phase 11 — Compliance, Reliability, Polish (Theme I) + Theme O Client Portal + Release
**Backend status:** 🟡 Mostly done — I1 QuotaCounter + circuit breaker · I3 cost-cap + `/admin/costs` + `/admin/quotas` · I4 GDPR export. **I2 Sandbox UI polish + O Client Portal + Sentry / Prometheus / OTLP observability dashboards are Sprint 4 (S4-H).**
**UI status:** 🟡 Partial — `/admin/costs`, `/admin/quotas`, `/admin/audit`, `/admin/health` shipped. Observability dashboards + Client Portal pending.

**Stories:**
- 11.1 **I1 Rate-Limit & Quota Manager** — per-channel and per-provider sliding-window quotas + circuit breaker; UI shows "Twitter: 47/300 today"
- 11.2 **I2 Sandbox / Preview Mode** — workspace flip to "dry-run"; every external action recorded but not fired; demo + onboarding use
- 11.3 **I3 Cost Tracking** — aggregate per-workspace LLM / image / video / voice provider spend; daily budgets + soft + hard caps; `/admin/costs`
- 11.4 **I4 Export / GDPR** — workspace data export (zip), right-to-delete, per-record retention policies
- 11.5 **O — Client Portal** *(activates when `Organization.is_external=true`)* — external read + approve + comment access, activity timeline, signed file handoff, calendar sharing
- 11.6 Sentry SDK on backend + frontend; OpenTelemetry → Prometheus + OTLP tracing
- 11.7 Helm chart polish — Bitnami Postgres + Redis + MinIO subcharts, dual-TLS (cert-manager or existingSecret), path-based routing, pre-install / pre-upgrade migration Hook Job
- 11.8 GHCR image publishing on tag; chart published to GHCR or chart-museum
- 11.9 v2.0 cut — semver bump, CHANGELOG, release notes, demo video re-record against new UI

---

## Cross-cutting requirements

Every screen must:
- Use `<Dk*>` components — no raw Tailwind, no shadcn defaults
- Use `--dk-*` tokens — no hard-coded hex anywhere
- Use Poppins (already wired via `next/font/google`)
- Light mode only — no `dark:` variants
- Wire long-running jobs through SSE + `<DkToast>` for completion
- Surface every external action through the Approval Inbox by default
- Add Activity tab (Audit timeline) on every record detail page
- Pass accessibility check — `--dk-purple-500` is large-text only, semantic colors used for status not decoration

## GitHub Project Board structure

Single project: **DClaw Marketing Project**. Custom fields:

| Field | Type | Values |
|---|---|---|
| Status | select | Todo / In Progress / In Review / Done / Blocked / Deferred |
| Phase | select | 0 / 1 / 2 / 3 / 4 / 5 / 6 / 7 / 8 / 9 / 10 / 11 |
| Theme | select | A / B / C / D / E / F / G / H / I / J / K / L / M / N / O / P / Q |
| Track | select | code / design / docs / infra / test / marketing |
| Priority | select | P0 / P1 / P2 |
| Estimate (hrs) | number | — |
| Epic | issue link | — |

Item hierarchy: **12 Epic issues** (one per Phase) → **~80 Stories** → **~400 Tasks** (created as Stories enter In Progress).

Views:
- **Roadmap** — group by Phase, sort by Priority
- **By Theme**
- **By Track**
- **Active Sprint** — filter In Progress + In Review
- **Backlog** — filter Todo + Deferred
- **Bugs** — filter type:bug, sort Priority

## Conventions

- **One PR per Story** wherever possible. Big Stories split into multiple Tasks → one PR each.
- **Continuous commits.** Every medium-to-major change ships its own commit on the branch; nothing batched.
- **Auto-merge.** All PRs labeled `auto-merge`; the poll-and-merge bot lands them after CI is green.
- **Closes #N** keyword in each PR body to auto-close the matching Story.
- **PLAN-v1.2.md** gets `- [x]` checkmarks as features land.
- **No CLAUDE.md drift.** Architecture lock + brand rules stay in `AGENTS.md`.
