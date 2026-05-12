# Changelog

All notable changes to this project. Format roughly follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) + [SemVer](https://semver.org/).

---

## [Unreleased]

—

---

## [0.1.0] — 2026-05-15 — *MVP*

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
- Brand-system enforcement: Poppins font, light-mode-only, DKube design tokens (`brand.css`).

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
- **Light-mode only.** DKube brand tokens are the only style source. No `dark:` Tailwind variants anywhere.
- **Admin-only user creation.** No self-signup; admins create users with temp passwords. First-login forces a reset.

### Known v0.1 limitations
- Helm chart minimal — full Bitnami subcharts + dual-TLS for v0.2.
- Multi-channel publishing is mocked; real X/LinkedIn/IG/etc. adapters in v0.2.
- Only Creatives Agent exists; SMM/SEO/Paid Media/Analyst agents are v0.2.
- Conductor agent (multi-agent orchestration) is v0.2 / Phase 3.
- Legacy v1.0 `/api/v1/campaigns`, `/leads`, `/analytics` routes don't yet require Org/Project context.

[0.1.0]: https://github.com/dclawstack/dclaw-marketing/releases/tag/v0.1.0
