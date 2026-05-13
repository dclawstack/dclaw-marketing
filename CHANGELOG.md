# Changelog

All notable changes to this project. Format roughly follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) + [SemVer](https://semver.org/).

---

## [Unreleased]

—

---

## [1.1.0] — 2026-05-13 — *Sprint 2 closeout*

> **Naming note.** The roadmap doc is titled `PLAN-v1.2.md` (carried over from the original spec); this release is `v1.1.0` per the post-MVP versioning. Future plan-doc revisions will be retitled to remove the confusion.

Sixty-plus PRs across Phases 2 / 5 / 6 / 7 / 8 / 9 / 10 / 11 plus Theme D4 + Theme H SEO depth + a complete A.11 auth-roadmap doc. Everything except the explicitly user-owned marketing collaterals (#52 demo video, #53 launch posts) is in. Builds on `v1.0.0` (the first end-to-end demo flow).

### Added — backend (post-rc1 stretch, #194–#210)
- **§6.2 KG write-back loop** — `BrandKitInsight` model + CRUD (`#194`); composer that injects top-K insights into the Creatives Agent system prompt (`#197`).
- **§6.6 Workflow templates** — `Workflow.is_template` + clone endpoint (`#196`).
- **Theme H — SEO depth** — site audit / internal-link suggester / ranking-delta tracker + daily Celery beat tasks + 4 API endpoints, backed by the Ahrefs MCP adapter (`#195`).
- **§6.7 MCP batch 4** — Salesforce / Mixpanel / PostHog adapters (`#202`).
- **A4 follow-up** — read-only audit-event browser API + pagination + filters (`#204`).
- **Phase 11 / I1 dashboard** — live `QuotaCounter` browse endpoint with pct-used + is-breaker pre-computed (`#207`).
- **Theme Q2 follow-up — URL ingestion** — pure-Python HTML→text stripper + new `ingest_url` Celery task + `POST /api/v1/ingest/urls` + `process_ingestion_source` dispatcher (`#205`).

### Added — frontend (post-rc1 stretch, #194–#210)
- New top-level pages: `/agents/seo` (`#198`), `/brand-insights` (`#199`), `/workflows` templates section + clone + toggle (`#201`), `/admin/health` (`#203`), `/admin/audit` (`#204`), `/admin/costs` (real, wired) + `/admin/quotas` (real, wired) (`#207`), `/knowledge` Knowledge Console (`#206`) with drag-drop file upload (`#208`).
- "Authorize via OAuth" button + `?oauth_error=` surface on `/channels` (`#200`).
- "Ingest into KG" button on `/library` asset cards (part of `#206`).
- Top-nav surfaces Knowledge / SEO / Workflows / Analytics (`#209`).

### Added — earlier Sprint 2 work (folded in from the prior rc1 enumeration)

### Added — backend

- **Phase 5 — Multi-Account Publishing**
  - Substack drafts (`#162`), Facebook Pages + Meta Threads (`#163`), TikTok Business + YouTube multipart upload (`#164`).
  - OAuth 2.0 scaffold + 7-provider registry (LinkedIn, X with PKCE, Instagram, Reddit with Basic, Pinterest with PKCE, Discord, Mastodon per-instance) (`#186`). State signed via JWT (10-min); access tokens stored on `SocialAccount._interim_access_token` for v1.
- **Phase 6 — MCP Integration Hub**
  - 11 concrete per-server adapters batched 3×: HubSpot / GA4 / Stripe (`#182`), Ahrefs / Webflow / WordPress / Ghost (`#183`), Slack / Discord / Notion / Google Drive (`#184`). Stub fallback inherited from the protocol layer.
- **Phase 7 — Email + Ads + Sequences**
  - Inbound email-event webhooks for Resend / Postmark / SendGrid with per-provider signature verification + LeadActivity bridge (`#168`).
  - Meta + LinkedIn paused-campaign create adapters (`#166`); Google Ads two-step create with developer-token + login-customer-id headers (`#167`).
  - `SequenceMembership` model + every-5-min sequence runner; segment-filter evaluator + nightly materializer (`#178`).
- **Phase 8 — Lead 2.0 + CRM + Attribution**
  - Pipedrive + Attio two-way sync adapters (`#165`).
  - Daily lead-rescore beat task with auto stage promotion (mql / sql / customer thresholds) (`#169`).
  - Time-decay attribution model + `/analytics/sankey` endpoint (`#177`).
- **Phase 9 — Agent Fleet**
  - 3σ rolling-baseline anomaly detector + weekly Monday-morning Analyst narrative (`#174`).
- **Phase 10 — Agency Operations**
  - QuickBooks Online invoice adapter (`#173`).
  - WorkflowRun resume + approval/branch node implementations + `POST /workflow-runs/{id}/resume` (`#176`).
  - Weekly + monthly client HTML reports uploaded to MinIO (`#191`).
- **Phase 11 — Compliance + Reliability**
  - Sliding-window QuotaCounter writer + circuit breaker (`#170`).
  - Cost-cap evaluator with warn/blocked states + per-action confidence threshold (`#175`).
  - GDPR export MinIO persistence + HTTP request/download endpoints (`#171`).
  - Sentry SDK + JSON structured logging bootstrap + `/health/dependencies` probe (`#192`).
  - Hardcoded admin recovery credentials + restart-recovery flow + A.11 future-auth roadmap (`#180`).
  - Hard-delete users from `/admin/users` with typed-confirm dialog (`#181`).
- **Phase 2 / Knowledge Graph**
  - Weekly Q4 freshness re-ingestion (`#179`); Q2 live pollers for Notion / Drive / Git / web (`#185`).
- **Theme D4 — Generic Webhook Receiver + Automation Rules** (`#172`)
  - New `Webhook` / `WebhookEvent` / `Automation` models + signed-payload public endpoint + every-30-sec automation runner.
- **Phase 6 / §6.11 — Approval pings** to Slack / Discord via the MCP adapters (`#190`).
- **Org-delete primitive** (`#161`).

### Added — frontend

- 8 new pages in batch 1 (`#187`): `/workflows`, `/workflows/[id]`, `/workflows/runs/[id]` (with Resume), `/invoices`, `/invoices/[id]`, `/time` tracker, `/playbooks`, `/analytics` root with hero cards + inline Sankey bar chart.
- 5 new pages in batch 2 (`#188`) — the **Client Portal** at `/client/*`: Overview, Approvals (inline Approve/Reject), read-only Schedule, asset Content gallery, white-label Analytics.
- 4 editor pages in batch 3 (`#189`): `/projects/[id]/briefs/new`, `/segments/new`, `/email/sequences/new`, `/ads/[id]`.

### Ops

- `scripts/backup_postgres.sh` + `scripts/backup_minio.sh` + `scripts/RESTORE_RUNBOOK.md` (`#192`).
- A.11 future auth-roadmap doc in `PLAN-v1.2.md` covering admin-only password recovery + admin-mediated user resets + magic-link auth.

### Deferred past 1.2

- Snapchat / Telegram publishers (low priority).
- React-flow visual editors for sequence + workflow + segment (plain forms cover the use case for v1).
- Markov-chain attribution (per-conversion is no-op; population-level model follows).
- Helm chart rebuild (existing chart works for the v1.0 deployment surface).
- True PDF output for client reports (HTML is browser-printable today).

---

## [1.0.0] — *MVP*

The first release. End-to-end demo flow works: log in → set brand → ingest context → generate content → approve in Inbox.

### Added — backend
- **Phase 0 — Baseline**
  - A0 Alembic baseline migration capturing the v1.0 schema (campaigns / leads / analytics_events).
  - A1 Auth & tenancy: FastAPI-Users with JWT + refresh; admin-only user creation with one-shot temp passwords + mandatory first-login reset. `User`, `Organization`, `OrganizationMembership`, `Project`, `ProjectMembership` models with 10 supervision-scope roles.
  - A2 Background jobs: Celery + Redis worker, `Job` model with progress + SSE stream endpoint at `/api/v1/jobs/{id}/stream`.
  - A3 Object storage: S3-compatible abstraction (MinIO in dev) with presigned-upload protocol. `Asset` model.
  - A4 Audit & governance: `AuditEvent` + `ApprovalRequest` models, 4-eye rule, full Approval API at `/api/v1/approvals`.
- **Phase 1 — Foundation (Theme Q)**
  - Q1 Brand Kits: versioned per-Org brand identity (palette/fonts/voice/positioning) + Personas. Active-version semantics.
  - Q2 Ingestion: file-upload → text-extract → chunk pipeline. Supports text/markdown/csv/json/xml/yaml/pdf. Runs via Celery with live progress.
  - Q3 Knowledge Graph: pgvector extension, 1536-dim embeddings on document chunks, IVFFlat ANN index, semantic-search API at `/api/v1/kg/search`.
  - Q5 Goals & Constraints: per-Org JSON columns for business objectives, brand-safety constraints, and per-action autonomy posture overrides.
- **Phase 2 — Agents**
  - Creatives Agent v1: direct Anthropic SDK call wrapper with deterministic SHA-256 stub fallback. End-to-end brief → BrandKit fetch → KG retrieval → variant generation → ApprovalRequests created. Hard-gated; never publishes directly.

### Added — frontend
- Auth flow: `/login`, `/first-login` (mandatory reset).
- Admin user management at `/admin/users` (create with temp password, reset, revoke).
- Creatives Station at `/agents/creatives` — kick off agent runs.
- Approval Inbox at `/inbox` — approve / reject pending agent outputs with optional reasons.
- Typed API client (`lib/api.ts`) covering all backend endpoints.
- `AuthGuard` + `AppShell` with role-aware nav.
- Brand-system enforcement: Poppins font, light-mode-only, DClaw design-kit tokens (`brand.css`).

### Added — infra
- Helm chart scaffolded (renamed from `dclaw-crm` to `dclaw-marketing`).
- `docker-compose.yml` brings up the full stack: Postgres (pgvector) + Redis + MinIO + backend + celery-worker + celery-beat + frontend.
- GitHub Actions:
  - `ci.yml` — backend pytest + frontend build on every PR.
  - `auto-merge.yml` — poll-and-merge bot (workaround for org-level disabled native auto-merge).
  - `project-automation.yml` — auto-add issues/PRs to the Project board.
  - `project-status-sync.yml` — keep Project Status field in sync with issue/PR state.
  - `release.yml` — build + push container images + GitHub Release on `v*.*.*` tags.
  - `claude.yml`, `claude-code-review.yml` — @claude bot for issues + auto PR review.
- Comprehensive test suite: ~100 tests across auth, admin, orgs, projects, jobs, storage, approvals, brand kits, ingestion, KG, agents, goals.

### Added — docs
- README with quickstart, status, architecture overview, port registry.
- USER-GUIDE.md — end-to-end demo walkthrough with curl recipes.
- ARCHITECTURE.md — engineering deep-dive (topology, tenancy, data layer, auth, Celery, storage, KG, agents, observability, deployment).
- CONTRIBUTING.md — branch / commit / PR conventions.
- PLAN-v1.2.md — full roadmap including v2.0 Vision addendum + Appendix A tech choices.
- Obsidian vault at repo root (Welcome.md, GLOSSARY.md, PROJECT-DASHBOARD.md, Repo Structure.md).

### Notable design decisions
- **Tenancy first.** Every persistence layer is Org-scoped from day one (some columns NULLABLE in v0.1; tightened in v0.2).
- **Hard-gate on outbound by default.** Per PLAN-v1.2 §v2.0 §5.2, no agent publishes without explicit human approval.
- **Stub-friendly externals.** Anthropic and OpenAI calls fall back to deterministic stubs when no API key is set — CI is hermetic, dev works offline.
- **Light-mode only.** DClaw brand tokens are the only style source. No `dark:` Tailwind variants anywhere.
- **Admin-only user creation.** No self-signup; admins create users with temp passwords. First-login forces a reset.

### Known v0.1 limitations
- Helm chart minimal — full Bitnami subcharts + dual-TLS for v0.2.
- Multi-channel publishing is mocked; real X/LinkedIn/IG/etc. adapters in v0.2.
- Only Creatives Agent exists; SMM/SEO/Paid Media/Analyst agents are v0.2.
- Conductor agent (multi-agent orchestration) is v0.2 / Phase 3.
- Legacy v1.0 `/api/v1/campaigns`, `/leads`, `/analytics` routes don't yet require Org/Project context.

[1.1.0]: https://github.com/dclawstack/dclaw-marketing/releases/tag/v1.1.0
[1.0.0]: https://github.com/dclawstack/dclaw-marketing/releases/tag/v1.0.0
