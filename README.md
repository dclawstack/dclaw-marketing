# DClaw Marketing

> **An agent-driven marketing operating system.**
> Set the brand once. Ingest your context. The agents do the work; you supervise.

DClaw Marketing turns a small team (or one operator + AI agents) into a full marketing function. Humans set the brand kit and feed in source material; AI agents draft content, schedule posts, run ads, and surface analytics. Humans supervise their **Station** and approve outbound actions in an **Approval Inbox** — agents never publish without consent.

---

## Quickstart (5 minutes)

```bash
# 1. Clone
git clone https://github.com/dclawstack/dclaw-marketing.git
cd dclaw-marketing

# 2. Configure environment
cp .env.example .env
# Optional: edit .env to set ANTHROPIC_API_KEY, OPENAI_API_KEY for real
# LLM calls. Without them, the agents and embeddings fall back to
# deterministic stubs so you can still run the full demo flow.

# 3. Bring up the stack
docker compose up -d
# Starts: Postgres (pgvector) · Redis · MinIO · backend · celery-worker · celery-beat · frontend

# 4. Open the app
open http://localhost:3015
# Default admin: admin@dclaw.io / ChangeMeOnFirstLogin!
# (You'll be forced to set a new password on first login.)
```

→ Full walkthrough in [docs/USER-GUIDE.md](docs/USER-GUIDE.md).

---

## What's inside

| Capability | Status |
|---|---|
| **Multi-tenant Org / Project hierarchy** with role-based access | ✅ v0.1 |
| **Admin-only user creation** with temp passwords + mandatory first-login reset | ✅ v0.1 |
| **Brand Kit** (versioned palette / fonts / voice / personas) | ✅ v0.1 |
| **File ingestion** → text chunks → semantic embeddings → Knowledge Graph | ✅ v0.1 |
| **Creatives Agent** — brief in, N variants out, each routed to Approval Inbox | ✅ v0.1 |
| **Approval Inbox** with audit log + 4-eye rule | ✅ v0.1 |
| **Background workers** (Celery + Redis) for long-running jobs + SSE progress streams | ✅ v0.1 |
| **Object storage** (S3-compatible; MinIO in dev) with presigned uploads | ✅ v0.1 |
| **Goals + Constraints + Autonomy Posture** per Org for agent guard-rails | ✅ v0.1 |
| Multi-channel publishing (X, LinkedIn, IG, …) | 🔜 v0.2 |
| SMM / SEO / Paid Media / Analyst agents | 🔜 v0.2 |
| Conductor agent (multi-agent orchestration) | 🔜 v0.2 |

---

## Architecture at a glance

```
Browser  ─►  Next.js 14 (frontend, :3015)
                    │
                    ▼  JWT bearer
              FastAPI (backend, :8102)
                    │
            ┌───────┼──────────┬─────────┬──────────┐
            ▼       ▼          ▼         ▼          ▼
       Postgres   Redis     MinIO   Anthropic    OpenAI
       (+pgvector)         (S3 API)  (Claude)  (embeddings)
                    │
                    ▼  task queue
              Celery worker + Celery Beat
              (ingestion, agent runs, scheduled jobs)
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full picture.

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
│   │   ├── services/      Business logic (slugs, email, generation, …)
│   │   └── workers/       Celery tasks
│   └── tests/
├── frontend/              Next.js 14 App Router
│   ├── public/brand/      DClaw logo SVGs and brand assets
│   └── src/
│       ├── app/           Pages (orgs, admin, settings, …)
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

## Critical rules for agents (humans + AI) working in this repo

1. **DO NOT install shadcn CLI** — pre-built UI components in `frontend/src/components/ui/`. Installing the CLI breaks the Tailwind v3 build.
2. **DO NOT change the Postgres test port** — `conftest.py` and `ci.yml` both use `localhost:5432`.
3. **DO NOT delete `.github/workflows/ci.yml`** — kills CI on every push.
4. **DO NOT upgrade `pytest-asyncio`** — pinned at `==0.24.0`; later versions break fixture scoping.
5. **All UI work uses `--dk-*` brand tokens.** Light mode only. No hard-coded hex. No `dark:` variants. See `frontend/src/styles/brand.css`.

---

## Key files

| File | Purpose |
|------|---------|
| [PLAN-v1.2.md](PLAN-v1.2.md) | Roadmap (v1.2 + v2.0 Vision + Appendix A tech choices) |
| [AGENTS.md](AGENTS.md) | Architecture rules + anti-patterns |
| [docs/USER-GUIDE.md](docs/USER-GUIDE.md) | How to use the platform end-to-end |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture deep-dive |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Branch / commit / PR conventions |
| [CHANGELOG.md](CHANGELOG.md) | Release history |
| `backend/app/core/config.py` | All env-driven config |
| `frontend/src/styles/brand.css` | DClaw design-kit tokens (single source of truth) |

---

## Port Registry (across the DClaw vertical-app family)

| App | Backend | Frontend | Database |
|-----|---------|----------|----------|
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
