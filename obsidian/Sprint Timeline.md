# Sprint Timeline

## Sprint 1 — Foundations (2026-05-09 → 2026-05-12)

**Closeout:** PR #151 (status PDF) · tag `v1.0.0` (renamed from `v0.1.0-mvp`).
**Theme:** From empty scaffold to first end-to-end demo flow.

- Phase 1 — Skeleton: Docker stack (FastAPI 8102 / Next.js 3015 / Postgres+pgvector / Redis / MinIO / Celery)
- Phase 2 — Auth + Multi-tenancy: fastapi-users JWT, Org/Project/Membership models, admin-only user creation
- Phase 3 — Approval Inbox: 4-eye approval queue
- Phase 4 — Agent Fleet scaffold: Conductor + Creatives Agent
- Theme Q — Brand & Knowledge: versioned BrandKit, file/url ingestion, pgvector embeddings, KG search
- Theme C1 — Scheduled posts: calendar + dispatcher
- Frontend baseline: top-nav, Approval Inbox, Brand Kit page, Knowledge Sources, Agents, Library, Calendar

**Numbers:** ~150 PRs · ~310 tests · 52% of plan.

**Report:** [[reports/sprint-1-status-2026-05-12]]

---

## Sprint 2 — Feature-complete (2026-05-13)

**Closeout:** PR #211 · tag `v1.1.0` (renamed from `v0.2.0`).
**Theme:** From scaffold to feature-complete in one 8-hour autonomous stretch.

- Phase 5 — Multi-Account Publishing: Substack, Facebook, Threads, TikTok, YouTube + OAuth scaffold for 7 providers
- Phase 6 — MCP Integration Hub: 14 concrete adapters (HubSpot, GA4, Stripe, Ahrefs, Webflow, WordPress, Ghost, Slack, Discord, Notion, Google Drive, Salesforce, Mixpanel, PostHog)
- Phase 7 — Email + Ads + Sequences: Resend/Postmark/SendGrid webhooks, Meta/Google/LinkedIn ads, SequenceMembership runner
- Phase 8 — Lead 2.0 + CRM: Pipedrive/Attio sync, daily rescore, time-decay attribution + Sankey
- Phase 9 — Agent Fleet expansion: Analyst agent (3σ anomaly), KG write-back loop
- Phase 10 — Agency Ops: QuickBooks invoices, WorkflowRun resume, weekly/monthly client reports
- Phase 11 — Compliance: QuotaCounter, cost-cap evaluator, GDPR export, audit browser
- Theme H — SEO depth: site audit, internal-link suggester, ranking delta
- Theme D4 — Webhooks + Automation rules

**Numbers:** ~60 PRs · ~510 tests · 90% of plan.

**Report:** [[reports/sprint-2-status-2026-05-13]]

---

## Sprint 3 — Operator-ready (2026-05-12 → 2026-05-14)

**Closeout:** PR #279 · tag `v1.1.1`.
**Theme:** Hardening. Make the feature-complete v1.1.0 stack safe and operable.

- **Admin model** — two-tier (bootstrap + per-org), centralized guards, last-admin protection, audit + notify
- **Slug scheme** — universal `u-/o-/s-` with 6-hex; migration re-slugs every row
- **Navigation** — left sidebar with domain grouping
- **Create-user-with-org** — one dialog: user + multi-org assignment + inline new-org
- **CI pipeline** — auto-merge + auto-close drains itself (squash PR body fix + issues:write permission)
- **SP3-1 → SP3-24** — 24-theme polish lane (Wizard, Variants, Hooks, Repurpose, Heatmap, BYO MCP, Kanban, Time, Retainer, Invoices, ConfigDict sweep, etc.)
- **Release rename** — `v0.1.0-mvp` → `v1.0.0` / `v0.2.0` → `v1.1.0` so version line aligns with PLAN-v1.2

**Numbers:** 44 PRs · 567 tests · 95% of plan.

**Report:** [[reports/sprint-3-status-2026-05-14]]

---

## Sprint 4 — Demo posture (planned)

**Target:** `v1.2.0`. The stakeholder demo release.

P0 lanes:
- Brand Setup Studio polish — end-to-end guidelines-PDF-to-versioned-BrandKit
- Real OAuth credentials wired — LinkedIn / X / Instagram operator-supplied + verified end-to-end
- TOTP enrollment UI — `/settings/2fa` with QR + recovery codes
- Marketing collateral (operator-owned): one-pager, slides, demo script, demo video, launch posts

P1 lanes:
- Observability dashboards (Grafana, Sentry tags, queue depth in `/admin/health`)
- User-guide refresh + PDF

P2 lanes:
- v1 legacy router consolidation
- BrandKitInsight bandit ranking
- Per-tenant LLM provider override
- Playwright frontend test suite
- Audit retention pruner
