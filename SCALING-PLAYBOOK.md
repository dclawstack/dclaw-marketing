# DClaw Stack — Scaling Playbook

> **How to go from 5 apps to 65+ apps using parallel coding agents.**
> Read this before onboarding new team members or spawning agent tabs.

## The Problem We Solved

Building the first 5 apps (`dclaw-chat`, `dclaw-med`, `dclaw-learn`, `dclaw-code`, `dclaw-legal`) taught us:

1. **Every app is 80% identical** — FastAPI + SQLAlchemy 2.0 + Next.js + Docker + Helm
2. **The 20% difference is domain logic** — models, schemas, API endpoints, UI pages
3. **Agents break the same things** — `declarative_base()`, missing `ARG NEXT_PUBLIC_API_URL`, `curl` in healthchecks, in-memory mocks
4. **Serial development is too slow** — One agent building one app at a time = 60+ apps will take forever

## The Solution: Scaffold + Parallel Agents

```
┌─────────────────────────────────────────────────────────────┐
│                    dclaw-scaffold (template)                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Backend   │  │  Frontend   │  │    Infra (Docker)   │  │
│  │  Skeleton   │  │  Skeleton   │  │   Helm / Compose    │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
└─────────┼────────────────┼────────────────────┼─────────────┘
          │                │                    │
          ▼                ▼                    ▼
   ┌────────────┐   ┌────────────┐      ┌────────────┐
   │  Agent #1  │   │  Agent #2  │      │  Agent #3  │
   │  Backend   │   │  Frontend  │      │   DevOps   │
   │  Architect │   │   Builder  │      │   Engineer │
   └─────┬──────┘   └─────┬──────┘      └─────┬──────┘
         │                │                   │
         └────────────────┼───────────────────┘
                          ▼
                   ┌────────────┐
                   │  dclaw-xxx │
                   │   (repo)   │
                   └────────────┘
```

Each new app starts as a **clone of `dclaw-scaffold`**. Three agents work in parallel on the same repo, each owning a slice:

| Agent Role | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| **Backend Architect** | Models, schemas, repositories, API routers, tests, alembic | `PRODUCT-SPEC.md` + scaffold backend | Working FastAPI app with CRUD |
| **Frontend Builder** | Next.js pages, components, API client wiring | `PRODUCT-SPEC.md` + scaffold frontend + backend API contract | Working UI connected to real API |
| **DevOps Engineer** | Docker fine-tuning, Helm values, GitHub Actions, env vars | Scaffold infra + app-specific ports | Production-ready deployment configs |

## Workflow: From Assignment to Working App

### Step 0: Pre-Flight (Human — 5 minutes)

1. **Pick the next app** from the backlog (e.g., `dclaw-crm`)
2. **Reserve ports** from the port registry in `dclaw-scaffold/README.md`
3. **Write `PRODUCT-SPEC.md`** using the template — domain entities, screens, API endpoints
4. **Clone scaffold:**
   ```bash
   git clone https://github.com/dclawstack/dclaw-scaffold.git dclaw-crm
   cd dclaw-crm
   # Replace placeholders: {APP_NAME} → CRM, ports, DB name
   ```
5. **Create GitHub repo** `dclawstack/dclaw-crm` and push the scaffold

### Step 1: Spawn 3 Parallel Agent Tabs (Simultaneous)

Open **3 separate agent conversations** (Claude, Kimi, Cursor, whatever your team uses). Each gets a specialized prompt.

> **Critical:** All 3 agents share the same Git repo. They should commit to **different branches** or work on **different directories** to avoid conflicts:
> - Backend agent → commits to `feat/backend`
> - Frontend agent → commits to `feat/frontend`
> - DevOps agent → commits to `feat/infra`
>
> At the end, merge all branches into `main`.

#### Tab 1: Backend Architect Agent

**Prompt:** (Copy from `AGENT-PROMPTS.md` → "Backend Architect Prompt")

This agent:
- Reads `PRODUCT-SPEC.md` for entity definitions
- Creates models in `app/models/`
- Creates Pydantic schemas in `app/schemas/`
- Creates repositories in `app/repositories/`
- Creates API routers in `app/api/v1/`
- Wires routers in `app/api/main.py`
- Generates alembic migration
- Writes tests in `tests/`
- Commits to `feat/backend`

#### Tab 2: Frontend Builder Agent

**Prompt:** (Copy from `AGENT-PROMPTS.md` → "Frontend Builder Prompt")

This agent:
- Reads `PRODUCT-SPEC.md` for screens and user flows
- Reads the backend routers (from `feat/backend` branch or shared context) for API contract
- Creates pages in `src/app/`
- Creates components in `src/components/`
- Wires API calls in `src/lib/api.ts`
- Commits to `feat/frontend`

> **Pro tip:** Give the frontend agent a snapshot of the backend OpenAPI schema (or just the router files) so it knows the exact endpoint signatures. You can generate this with:
> ```bash
> cd backend && python -c "from app.api.main import app; import json; print(json.dumps(app.openapi()))" > openapi.json
> ```

#### Tab 3: DevOps Engineer Agent

**Prompt:** (Copy from `AGENT-PROMPTS.md` → "DevOps Engineer Prompt")

This agent:
- Updates `docker-compose.yml` with correct app-specific ports
- Updates `helm/values.yaml` and `helm/templates/` with app name and image repos
- Ensures `frontend/Dockerfile` has `ARG NEXT_PUBLIC_API_URL`
- Ensures backend healthcheck uses `urllib.request.urlopen()` not `curl`
- Sets up `.github/workflows/ci.yml` with correct working directories
- Updates `.env.example` with app-specific defaults
- Commits to `feat/infra`

### Step 2: Integration (Human — 10 minutes)

1. **Merge all branches:**
   ```bash
   git checkout main
   git merge feat/backend feat/frontend feat/infra
   ```
2. **Resolve conflicts** (usually minimal — each agent touched different files)
3. **Run local smoke test:**
   ```bash
   docker compose up -d
   # Wait for healthchecks
   curl http://localhost:{BACKEND_PORT}/health/
   curl http://localhost:{FRONTEND_PORT}/
   ```
4. **Push to GitHub:**
   ```bash
   git push origin main
   ```

### Step 3: QA Agent (Optional — 4th Tab)

If you have capacity, spawn a 4th agent:

**Prompt:** "Review the merged codebase. Write missing tests. Verify all endpoints return 200. Check for the anti-patterns in `AGENTS.md`."

This agent:
- Runs `pytest` and reports coverage
- Checks for `MOCK_*` dicts
- Verifies `ARG NEXT_PUBLIC_API_URL` exists
- Checks healthcheck commands
- Opens PRs with fixes

## Parallelization Math

| Approach | Time per app | 10 apps | 60 apps |
|----------|-------------|---------|---------|
| Serial (1 agent) | ~4 hours | 40 hours | 240 hours |
| Parallel (3 agents + human) | ~1.5 hours | 15 hours | 90 hours |
| **Speedup** | **2.7x** | **2.7x** | **2.7x** |

> Note: "Time per app" includes human integration time. The actual agent work happens in parallel, so wall-clock time is closer to **45 minutes per app** if all 3 agents finish simultaneously.

## Port Registry

Update this when assigning new apps:

| App | Backend | Frontend | Postgres DB |
|-----|---------|----------|-------------|
| dclaw-chat | 8090 | 3000 | dclaw_chat |
| dclaw-med | 8092 | 3004 | dclaw_med |
| dclaw-learn | 8093 | 3003 | dclaw_learn |
| dclaw-code | 8094 | 3005 | dclaw_code |
| dclaw-legal | 8099 | 3013 | dclaw_legal |
| **TBD #6** | **8101** | **3014** | **dclaw_xxx** |
| **TBD #7** | **8102** | **3015** | **dclaw_xxx** |

## Anti-Patterns Checklist (Before Pushing)

Run this checklist on every new app:

- [ ] `app/models/base.py` uses `DeclarativeBase`, NOT `declarative_base()`
- [ ] `app/core/database.py` imports `Base` from `app.models.base`
- [ ] No in-memory `MOCK_*` dicts anywhere
- [ ] All repositories use `BaseRepository` pattern
- [ ] All routers use `Depends(get_db)`
- [ ] `frontend/Dockerfile` declares `ARG NEXT_PUBLIC_API_URL` before `RUN npm run build`
- [ ] `docker-compose.yml` backend healthcheck uses `python urllib.request.urlopen()`
- [ ] `docker-compose.yml` frontend healthcheck uses `wget -q --spider`
- [ ] `package-lock.json` is committed after any `npm install`
- [ ] Alembic migration exists for all models
- [ ] Tests exist for all endpoints
- [ ] `AGENTS.md` and `PLAN-v1.2.md` are customized (not still have `{APP_NAME}` placeholders)

## Team Onboarding Checklist (Per New Member)

Give each new team member:

1. [ ] GitHub org invite to `dclawstack`
2. [ ] Write access to their assigned repo(s)
3. [ ] Link to this `SCALING-PLAYBOOK.md`
4. [ ] Link to `dclaw-scaffold` repo
5. [ ] Their app's `PRODUCT-SPEC.md`
6. [ ] Their app's reserved ports from the registry
7. [ ] Copy of `AGENT-PROMPTS.md`
8. [ ] Slack/Discord channel for integration questions

## Recommended Next 10 Apps

Based on common vertical SaaS demand:

1. **dclaw-crm** — Customer relationship management
2. **dclaw-finance** — Invoicing, expenses, bookkeeping
3. **dclaw-hr** — Employee directory, time-off, payroll
4. **dclaw-inventory** — Stock tracking, warehouses, suppliers
5. **dclaw-project** — Task management, Gantt charts, team collaboration
6. **dclaw-support** — Ticketing, knowledge base, customer support
7. **dclaw-marketing** — Email campaigns, landing pages, analytics
8. **dclaw-real-estate** — Property listings, tenant management
9. **dclaw-event** — Event planning, registration, scheduling
10. **dclaw-recruitment** — Job postings, candidate pipeline, interviews

## Long-Term: Shared Libraries (Phase 2)

After 15+ apps, extract shared code to eliminate drift:

| Library | What It Contains | Impact |
|---------|-----------------|--------|
| `dclaw-core` (PyPI) | `Base`, `get_db`, `BaseRepository`, config loader | ~200 lines per app |
| `@dclawstack/design-kit` (npm) | shadcn/ui components, theme, layout shell | ~15 components per app |
| `@dclawstack/api-client` (npm) | Typed fetch wrapper, error handling, auth headers | ~100 lines per app |

Until then, the scaffold is the source of truth. Update `dclaw-scaffold` when you discover new anti-patterns or improvements.
