# DClaw Marketing — v2.0 Implementation Plan

> **Status:** master plan, locked 2026-05-12. Source of truth for the GitHub Project board.
> Every Epic, Story, and Task in the board references a section of this file.
> Pair-read with [`PLAN-v1.2.md`](PLAN-v1.2.md) (feature spec) and [`AGENTS.md`](AGENTS.md) (architecture + brand lock).

## Scope

- Build the **full v1.2 / v2.0 promise** end-to-end. No deadline cap.
- Every operator workflow runs **from the UI**, not the CLI. Curl recipes in `docs/USER-GUIDE.md` exist only as developer references; the product itself never asks an operator to open a terminal.
- Apply the **DKube design system** correctly across every screen — `--dk-*` tokens, `.dk-*` semantic classes, Poppins, light-mode only.
- **Product brand stays "DClaw Marketing"**. DKube tokens are the visual system. The DKube cube glyph only appears when representing the parent brand (footer attribution, login page).

## Design system — already in place

The Claude Design ingest (`design/dkube-design-system/`) confirms `frontend/src/styles/brand.css` is **token-identical** to the design's `colors_and_type.css`. The gap is application: existing pages use generic Tailwind classes instead of the brand vocabulary. Phase 0 fixes that before any new screen ships.

Reference materials in `design/dkube-design-system/`:

| Path | Use |
|---|---|
| `BRAND_GUIDELINES.md` | Voice, logo, color, type, components, motion rules — authoritative |
| `colors_and_type.css` | Token definitions — already mirrored in `frontend/src/styles/brand.css` |
| `assets/` | Logo lockups, customer logos, pillar icons, brand imagery |
| `fonts/` | Poppins woff2 (we load via `next/font/google` — bundled set is reference) |
| `preview/*.html` | Component reference cards — eyeball every `<Dk*>` against these |
| `ui_kits/marketing-site/` | Marketing-site React kit — reference for component composition |
| `slides/` | 15 master slide layouts + arch diagram primitives |

---

## Phase map (12 phases)

Each Phase = one **Epic issue** on the project board. Stories and Tasks roll up into their Epic.

### Phase 0 — Design Ground Truth & Component Library
**Why first:** every Phase 1+ screen should be born using the design vocabulary. Retrofitting later is wasteful.

**Stories:**
- 0.1 Import brand assets into `frontend/public/brand/` (logos, icons, customer logos, pillar imagery)
- 0.2 Tailwind token binding (`tailwind.config.ts`) — `bg-brand`, `bg-ink`, `text-fg-1`, `border-brand`, `shadow-brand`, `rounded-pill` map to `--dk-*`; disable `dark:` variants; Poppins as the only sans family
- 0.3 `<Dk*>` component library — `<DkButton>` (pill, primary/secondary/ghost), `<DkCard>` (soft shadow + hover lift), `<DkChip>`, `<DkInput>`, `<DkSelect>`, `<DkTextarea>`, `<DkTable>`, `<DkBadge>`, `<DkDialog>`, `<DkTabs>`, `<DkToast>`, `<DkEyebrow>`, `<DkAvatar>`, `<DkSlider>`, `<DkSwitch>`, `<DkCheckbox>`, `<DkRadioGroup>`, `<DkProgress>`, `<DkSkeleton>`, `<DkEmptyState>`, `<DkPageHeader>`, `<DkBreadcrumb>`, `<DkSidebar>`
- 0.4 `/_design` reference page (admin-only) rendering every component variant — eyeball-comparable with the design's `preview/*.html`
- 0.5 Refactor existing pages to the new vocabulary: login, first-login, dashboard, admin/users, agents/creatives, inbox, campaigns, leads
- 0.6 DKube cube logo in nav (subtle attribution) + favicon
- 0.7 Top-level shell rebuild — sticky header, max-width 1280px container, brand-tinted hover states, motion easing
- 0.8 Voice + casing audit — strip emojis / exclamations from copy; apply Title Case to headings; em-dashes for hard pivots

---

### Phase 1 — Multi-Tenant Foundation (Theme A1, v2.0 §1-2)
**Backend status:** done.
**UI status:** partial (only admin/users + login).

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
**Backend status:** done (brand-kits, ingest, kg, goals).
**UI status:** none.

**Stories:**
- 2.1 **Q1 Brand Setup Studio** — `/orgs/[id]/brand`
  - Palette: color pickers for primary / secondary / surfaces / ink (defaulted to DKube purple)
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
**Backend status:** partial (Creatives Agent + Assets done; image/video/voice/music providers NOT done).
**UI status:** partial (Creatives Station basic — needs upgrade).

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
**Backend status:** NOT done.
**UI status:** NOT done.

**Stories:**
- 4.1 `ScheduledPost(workspace_id, channel_id, asset_ids[], copy, scheduled_at, status, parent_campaign_id, tags[])` model + repository
- 4.2 Celery beat scanner — dispatch posts when `scheduled_at <= now AND status='queued'`
- 4.3 Conflict detection — block two LinkedIn posts within 60 min on the same account
- 4.4 Best-time-to-post recommender — per-channel historical engagement model
- 4.5 `/calendar` UI — FullCalendar-style, themed, channel-color-coded chips, day/week/month, "publish now" action, drag-to-reschedule

---

### Phase 5 — Multi-Account Multi-Channel Publishing (Theme C2, v2.0 §6)
**Backend status:** NOT done.
**UI status:** NOT done.

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
**Backend status:** NOT done.
**UI status:** NOT done.

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
**Backend status:** NOT done.
**UI status:** NOT done.

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
**Backend status:** partial (legacy Lead + analytics stubs).
**UI status:** partial (legacy lead list).

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

### Phase 9 — Agent Fleet (v2.0 §4)
**Backend status:** partial (one agent — Creatives, deterministic-stub fallback).
**UI status:** partial (one station — Creatives basic).

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
**Backend status:** NOT done.
**UI status:** NOT done.

**Stories:**
- 10.1 **J — Client Operations** — Client / Org CRUD, onboarding wizard (collect brand assets / social accounts / persona / goals), per-Org retainers + budgets, per-Org approval workflows
- 10.2 **K — Project Management** — Project templates (Product Launch, SEO Refresh, Brand Revamp, Newsletter Reboot), Kanban + Gantt boards, task dependencies, capacity planning (per-user / per-agent utilization), milestones
- 10.3 **L — Time Tracking & Billing** — Time logs per task / campaign / Org, auto-rollup to retainer burn-down, invoice generation (Stripe + QuickBooks export), billable vs non-billable
- 10.4 **M — Client Reporting** — Auto-generated weekly + monthly PDFs, scheduled email delivery, white-label option (per-Org logo + colors), embeddable read-only dashboard URLs
- 10.5 **N — Knowledge Base & SOPs** — Reusable prompts, briefs, processes, playbooks, AI-searchable across the Org; agents propose new SOPs derived from successful patterns
- 10.6 **P — Workflow Builder** — Visual no-code chain of LLM steps + tool calls + approval gates ("on new lead from HubSpot → enrich → score → if score>80 → draft personalized intro → notify SDR"); Magic Loops / Wordware shape

---

### Phase 11 — Compliance, Reliability, Polish (Theme I) + Theme O Client Portal + Release
**Backend status:** NOT done.
**UI status:** NOT done.

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
