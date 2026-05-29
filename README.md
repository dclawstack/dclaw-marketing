<div align="center">

<img src="frontend/public/brand/logos/dclaw-icon-purple.svg" width="72" alt="DClaw Marketing" />

# DClaw Marketing

**An agent-driven marketing operating system.**  
Set the brand once. Ingest your context. The agents run the operation — you supervise.

[![Release](https://img.shields.io/github/v/release/dclawstack/dclaw-marketing?label=release&color=7660A8)](https://github.com/dclawstack/dclaw-marketing/releases)
[![Tests](https://img.shields.io/badge/tests-local%20gate-7660A8)](CONTRIBUTING.md)
[![Self-hosted](https://img.shields.io/badge/deploy-Helm%20%2B%20K8s-7660A8)](helm/)
[![License](https://img.shields.io/badge/license-TBD-lightgrey)](LICENSE)

</div>

---

## What it is

DClaw Marketing turns a small team — or one operator working with AI agents — into a full marketing function. Humans configure the brand, feed in source material, and supervise a fleet of specialist agents from their **Station**. Every outbound action clears an **Approval Inbox** before it fires. Agents never publish without consent.

The platform ships as a **Helm chart + container images** you install on your own Kubernetes cluster. No vendor lock-in, no SaaS dependency, no data leaving your perimeter.

---

## Capabilities

### Foundation

| Capability | Status |
|---|---|
| Multi-tenant **Organization → Project → Campaign → Asset** hierarchy | ✅ v1.0 |
| Role-based access — 10 supervision scopes (Admin, Manager, Creatives, SMM, SEO, Paid Media, Reviewer, Analyst, Viewer, Client) | ✅ v1.0 |
| Two-tier admin model — superadmin (platform-wide) + org-admin (org-scoped) | ✅ v1.1 |
| Admin-only user provisioning — temp password + mandatory first-login reset + TOTP 2FA | ✅ v1.1 |
| **Brand Kit** — versioned palette, fonts, voice sliders, do/don't-say lists, audience personas | ✅ v1.0 |
| **Knowledge Graph** — ingest URLs, files, Git repos, ZIP archives → pgvector semantic search | ✅ v1.1 |
| Background workers — Celery + Redis, SSE progress streams, dead-letter handling | ✅ v1.0 |
| Object storage — S3-compatible (MinIO in dev, S3/R2/Spaces in prod) with presigned uploads | ✅ v1.0 |
| Approval Inbox — 4-eye rule, per-action reasoning trace, full audit log | ✅ v1.0 |
| Goals + Autonomy Posture — Autopilot / Soft-gate / Hard-gate per action class | ✅ v1.0 |

### Content & Publishing

| Capability | Status |
|---|---|
| **Creatives Agent** — brief in, N variants out (text + image), brand-voice linted | ✅ v1.0 |
| **SEO Agent** — keyword pipeline (Ahrefs MCP), internal-link suggester, ranking-delta tracker | ✅ v1.1 |
| **Analyst Agent** — 3σ anomaly detection, Monday-morning narrative reports | ✅ v1.1 |
| Asset Library (DAM) — filters by kind / source / brand-kit / status, presigned download | ✅ v1.1 |
| Multi-channel publishing — X, LinkedIn, Instagram, TikTok, YouTube, Facebook, Threads, Reddit, Pinterest, Bluesky, Discord, Mastodon, Substack, WordPress, Ghost | ✅ v1.1 |
| OAuth 2.0 flows — LinkedIn, X (PKCE), Instagram, Reddit, Pinterest (PKCE), Discord, Mastodon | ✅ v1.1 |
| Email sequences — Resend / Postmark / SendGrid; drip flows with delay + branch conditions | ✅ v1.1 |
| Ads publisher — Meta, LinkedIn, Google Ads (draft + submit; human approves launch) | ✅ v1.1 |
| Conductor agent (multi-agent orchestration) | 🔜 v1.2 |
| SMM / Paid Media agents + Stations | 🔜 v1.2 |

### MCP Integration Hub

| Category | Adapters |
|---|---|
| **CRM** | HubSpot · Salesforce · Pipedrive · Attio |
| **Analytics** | GA4 · Mixpanel · PostHog |
| **Productivity** | Slack · Notion · Google Drive · Discord |
| **SEO** | Ahrefs |
| **CMS** | Webflow · WordPress · Ghost |
| **Payments** | Stripe · QuickBooks Online |
| **AI / Generation** | Anthropic Claude · OpenAI |

### Leads, CRM & Attribution

| Capability | Status |
|---|---|
| Lead 2.0 — identity, enrichment, scoring, lifecycle stage (new → mql → sql → customer) | ✅ v1.1 |
| CRM two-way sync — HubSpot, Salesforce, Pipedrive, Attio | ✅ v1.1 |
| Segment builder — AND/OR filter DSL, nightly materializer, ad-platform audience sync | ✅ v1.1 |
| Attribution — first-touch, last-touch, time-decay; Sankey view | ✅ v1.1 |

### Agency Operations

| Capability | Status |
|---|---|
| Visual Workflow Builder — LLM-step chains + approval gates + branching nodes | ✅ v1.1 |
| Client reporting — weekly + monthly HTML reports, delivered via MinIO | ✅ v1.1 |
| Rate-limit & quota manager — sliding-window counters, circuit breaker, live UI gauge | ✅ v1.1 |
| Cost tracking — per-org LLM / image / video spend; daily soft + hard caps | ✅ v1.1 |
| GDPR export — full workspace data export (ZIP) + right-to-delete | ✅ v1.1 |

---

## Architecture

```
                           Browser
                              │
                    ┌─────────▼──────────┐
                    │   Next.js 14       │  :3069
                    │   (App Router)     │
                    └─────────┬──────────┘
                              │  JWT bearer
                    ┌─────────▼──────────┐
                    │   FastAPI          │  :8156
                    │   (async Python)   │
                    └──┬──┬──┬───────────┘
                       │  │  │
          ┌────────────┘  │  └──────────────┐
          ▼               ▼                 ▼
     Postgres 16       Redis            MinIO
     + pgvector                        (S3 API)
                          │
                 ┌────────▼────────┐        Anthropic
                 │  Celery worker  │◄──────  / OpenAI
                 │  + Celery Beat  │
                 │                 │
                 │  jobs · agents  │
                 │  sequences      │
                 │  publishing     │
                 │  analytics      │
                 └────────┬────────┘
                          │
                 ┌────────▼────────┐
                 │   MCP Hub       │
                 │   20+ provider  │
                 │   adapters      │
                 └─────────────────┘
```

Full topology, auth flow, and endpoint reference: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## Quickstart

**Prerequisites:** Docker, Docker Compose v2.

```bash
# 1. Clone
git clone https://github.com/dclawstack/dclaw-marketing.git
cd dclaw-marketing

# 2. Configure
cp .env.example .env
# Add ANTHROPIC_API_KEY for live agent runs.
# Without it, agents fall back to deterministic stubs — the full UI still works.

# 3. Start
docker compose up -d
# Brings up: Postgres (pgvector) · Redis · MinIO
#            backend · celery-worker · celery-beat · frontend

# 4. Open
open http://localhost:3069
```

**Default credentials:** `admin@dclaw.io` / `ChangeMeOnFirstLogin!`  
A mandatory password reset runs on first login.

End-to-end walkthrough: [docs/USER-GUIDE.md](docs/USER-GUIDE.md)

---

## Stack

| Layer | Technology |
|---|---|
| **API** | FastAPI · SQLAlchemy 2.0 async · Pydantic v2 · FastAPI-Users |
| **Database** | Postgres 16 + pgvector |
| **Cache / Queue** | Redis · Celery · Celery Beat |
| **Storage** | MinIO (dev) · S3 / R2 / Spaces (prod) via `aiobotocore` |
| **Frontend** | Next.js 14 App Router · Tailwind CSS · `--dk-*` design tokens · Poppins |
| **AI** | Anthropic Claude (agents) · OpenAI (embeddings) |
| **Migrations** | Alembic |
| **Testing** | pytest · pytest-asyncio 0.24.0 |
| **Packaging** | Docker · Helm chart · GHCR container registry |

---

## Deployment

One Helm install supports N Organizations. Postgres, Redis, and MinIO are bundled as subcharts by default — swap to managed services via values flags.

```bash
helm install dclaw-marketing oci://ghcr.io/dclawstack/charts/dclaw-marketing \
  -f values.yaml
```

Alembic migrations run automatically in a pre-upgrade Hook Job — no manual steps on upgrade.

Full chart shape, TLS modes, secrets management, and multi-tenant isolation: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## Documentation

| Document | What's in it |
|---|---|
| [AGENTS.md](AGENTS.md) | Architecture lock — stack choices, anti-patterns, brand rules for coding agents |
| [PLAN-v1.2.md](PLAN-v1.2.md) | Full feature roadmap: themes A–Q, v2.0 vision, tech choices (Appendix A), phase breakdown (Appendix B) |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System topology, auth flow, API surface, agent runtime, Helm chart shape |
| [docs/USER-GUIDE.md](docs/USER-GUIDE.md) | Operator walkthrough — brand setup → ingest → generate → approve → publish |
| [docs/api/README.md](docs/api/README.md) | API reference index — live Swagger at `:8156/docs`, ReDoc at `:8156/redoc` |
| [CHANGELOG.md](CHANGELOG.md) | Release history |
| [scripts/RESTORE_RUNBOOK.md](scripts/RESTORE_RUNBOOK.md) | Disaster recovery — Postgres, MinIO, and credential restore |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for branch naming, commit style, and PR conventions.  
See [GLOSSARY.md](GLOSSARY.md) for domain terminology.

**Rules that apply to all contributors (human and AI):**

1. **Do not install the shadcn CLI** — pre-built components live in `frontend/src/components/ui/`. The CLI breaks the Tailwind v3 build.
2. **Do not change the Postgres test port** — `conftest.py` and `ci.yml` both pin `localhost:5432`.
3. **Do not delete `.github/workflows/ci.yml`** — kills CI on every push.
4. **Do not upgrade `pytest-asyncio`** — pinned at `==0.24.0`; later versions break fixture scoping.
5. **All UI uses `--dk-*` brand tokens** — light mode only, no `dark:` variants, no hardcoded hex. See `frontend/src/styles/brand.css`.

---

## Repository layout

```
dclaw-marketing/
├── backend/               FastAPI app, Celery workers, Alembic migrations
│   ├── app/
│   │   ├── api/v1/        REST endpoints (auth, orgs, users, admin, …)
│   │   ├── auth/          FastAPI-Users config + schemas
│   │   ├── core/          Config, DB session, lifespan
│   │   ├── models/        SQLAlchemy 2.0 models
│   │   ├── services/      Business logic (slugs, email, generation, MCP, …)
│   │   └── workers/       Celery tasks
│   └── tests/
├── frontend/              Next.js 14 App Router
│   ├── public/brand/      DClaw logo SVGs and brand assets
│   └── src/
│       ├── app/           Pages (orgs, admin, settings, agents, …)
│       ├── components/dk/ Canonical DK component library
│       ├── contexts/      Auth + Org React contexts
│       ├── lib/           API client, auth helpers, utils
│       └── styles/        brand.css — single source of truth for --dk-* tokens
├── design/
│   └── source/project/    DKube brand system (guidelines, SKILL.md, slide masters, UI kit)
├── docs/                  ARCHITECTURE.md · USER-GUIDE.md · api/README.md
├── helm/                  Kubernetes Helm chart
├── scripts/               RESTORE_RUNBOOK.md + ops helpers
├── obsidian/              Vault sub-directories (reports, etc.)
└── .github/workflows/     CI · auto-merge · release · project automation
```

---

## Port registry

| App | Backend | Frontend | Database |
|---|---|---|---|
| dclaw-chat | 8090 | 3000 | dclaw_chat |
| dclaw-med | 8092 | 3004 | dclaw_med |
| dclaw-learn | 8093 | 3003 | dclaw_learn |
| dclaw-code | 8094 | 3005 | dclaw_code |
| dclaw-crm | 8095 | 3006 | dclaw_crm |
| dclaw-finance | 8096 | 3007 | dclaw_finance |
| dclaw-hr | 8097 | 3008 | dclaw_hr |
| dclaw-legal | 8099 | 3013 | dclaw_legal |
| **dclaw-marketing** | **8102** | **3015** | **dclaw_marketing** |

---

## Contributors

- [Deepro Mallick (@deepro713)](https://github.com/deepro713)

---

## License

TBD.
