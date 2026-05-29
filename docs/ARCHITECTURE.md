# Architecture

Engineering deep-dive into how DClaw Marketing v0.1 is built. Pairs with [PLAN-v1.2.md](../PLAN-v1.2.md) (the strategic plan) and [AGENTS.md](../AGENTS.md) (the rules for agents working in this repo).

---

## Topology

```
                       ┌──────────────────────────────┐
                       │  Browser                      │
                       │  Next.js 14 (App Router)      │
                       │  :3069                        │
                       └─────────────┬─────────────────┘
                                     │ HTTPS + JWT Bearer
                                     ▼
            ┌────────────────────────────────────────────────────┐
            │  FastAPI (backend) :8156                            │
            │  ─────────────────────────────────────              │
            │  Auth (FastAPI-Users JWT)                           │
            │  REST: /me /admin /orgs /projects /assets           │
            │        /ingest /kg /agents /approvals /goals        │
            │        /brand-kits /jobs (+ SSE stream)             │
            │  Lifespan: init_db() — alembic upgrade head        │
            │            + bootstrap admin                        │
            └─┬──────────────────┬────────────────────┬──────────┘
              │                  │                    │
              ▼                  ▼                    ▼
       ┌──────────────┐   ┌─────────────┐    ┌─────────────────┐
       │ Postgres 16  │   │  Redis 7    │    │  MinIO          │
       │ + pgvector   │   │  (broker +  │    │  (S3 API)       │
       │ :5432        │   │   cache)    │    │  :9000          │
       └──────────────┘   │  :6379      │    └─────────────────┘
                          └─────┬───────┘             ▲
                                │                     │
                                ▼                     │
                       ┌────────────────────┐         │
                       │  Celery Worker     │─────────┘
                       │  (sync, 2 conc.)   │   (sync boto3)
                       │  app.worker.tasks  │
                       └─────┬──────────────┘
                             │
                             ▼
                     ┌──────────────────┐
                     │  Celery Beat     │
                     │  (cron scheduler)│
                     └──────────────────┘

External egress (when API keys are configured):
  api.anthropic.com   — Creatives Agent generation (Claude)
  api.openai.com      — text-embedding-3-small for KG embeddings
  api.resend.com      — transactional emails (A1 invites, future)
```

Without `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`, both fall back to deterministic stub providers. The full demo flow works offline.

---

## Tenancy model

```
Organization                       Top tenancy tier
├── Members (User × role)          OrgMembership
├── Brand Kits (versioned)         BrandKit (+ Persona children)
├── Goals / Constraints / Posture  on Organization row
├── Connected social accounts      SocialAccount (v0.2)
└── Projects                       Project
    ├── Members (User × role)      ProjectMembership
    ├── Campaigns                  Campaign
    │   ├── Leads                  Lead
    │   └── Analytics events       AnalyticsEvent
    ├── ApprovalRequests           ApprovalRequest
    ├── IngestionSources           IngestionSource → DocumentChunks
    ├── Assets                     Asset (org-scoped)
    └── Jobs                       Job (org + initiator)
```

**External-client future**: `Organization.is_external = true` flips on Client Portal UI (v0.2+). Same data model — different access surface.

---

## Roles (supervision scopes)

10 roles, used at both Org and Project level. Same enum (`OrganizationRole`) reused so a user can be `Manager` on Org but `Creatives` on a specific Project.

| Role | Can do |
|---|---|
| `admin` | Everything in the Org. User mgmt, integrations, billing. |
| `manager` | Conductor supervision; all Projects; final approver. |
| `creatives` | Creatives Agent supervision; brand kits; assets. |
| `social_media_manager` | SMM Agent supervision; calendar; channel mgmt (v0.2). |
| `seo_specialist` | SEO Agent supervision; blog pipeline (v0.2). |
| `paid_media_specialist` | Paid Media Agent supervision (v0.2). |
| `reviewer` | Approval-only. Read + comment + approve / reject. |
| `analyst` | Read-only across analytics; can build reports (v0.2). |
| `viewer` | Read-only on assigned items. |
| `client` *(external, future)* | Portal-restricted read + approve. |

Authorization is enforced **per route** via `Depends(current_active_user)` + per-Org membership lookups. The agent layer additionally checks the user's role for that Org before kicking off a run.

---

## Data layer

**Postgres 16 + pgvector** (single instance for v0.1). Schema is alembic-managed. All migrations live in `backend/alembic/versions/`.

| Revision | What |
|---|---|
| `20260512_0001` | Baseline — campaigns / leads / analytics_events (v1.0 schema captured) |
| `20260512_0002` | Auth — users / organizations / projects / memberships; tenancy FKs added to legacy tables |
| `20260512_0003` | Jobs table (Celery state) |
| `20260512_0004` | Assets table (S3 metadata) |
| `20260512_0005` | Audit events + approval requests |
| `20260512_0006` | Brand kits + personas |
| `20260512_0007` | Ingestion sources + document chunks |
| `20260512_0008` | pgvector extension + embedding column on chunks + IVFFlat ANN index |
| `20260513_0001` | Org goals/constraints/autonomy_posture JSON columns |

`alembic upgrade head` is run automatically on app start via `init_db()`. For production via Helm, this happens in a `pre-install` / `pre-upgrade` Job (the chart wires this in v0.2).

**Tenant isolation** is row-level: every tenant-scoped table has `organization_id` (sometimes nullable in v0.1; tightened to NOT NULL in v0.2 when all routes are Org-scoped). API-layer access checks gate cross-Org reads.

---

## Auth flow

```
1. POST /api/v1/auth/jwt/login (OAuth2 form)
   → 200 { access_token }
2. Client stores token in localStorage
3. Every subsequent request: Authorization: Bearer <token>
4. FastAPI-Users decodes + validates → injects User into request
5. Route-specific deps (current_active_user, current_superuser) gate access
```

**First-login mandatory reset**: admin-created users have `password_reset_required=True`. The frontend AuthGuard redirects them to `/first-login` until they call `POST /me/password`.

**Password rules** (FastAPI-Users `UserManager.validate_password`):
- ≥ 10 chars
- Cannot equal the email local-part
- Cannot equal the current password on reset

**Argon2** hashing throughout.

---

## Background work — Celery + Job model

Every long-running operation gets a `Job` row tracking status + progress.

```
queued → running → succeeded | failed | canceled
              ▲                  │
              └──── progress 0..1 ───┘
```

**SSE stream** at `GET /api/v1/jobs/{id}/stream` lets the frontend live-watch a Job by polling the DB every 500ms and emitting changes.

**Tasks** registered in `app/worker/tasks/`:

| Task | Purpose |
|---|---|
| `sleep_and_progress` | Smoke test |
| `ingest_asset` | Q2 ingestion: fetch from S3 → extract text → chunk → embed → store as DocumentChunks |

The sync engine for Celery is a separate SQLAlchemy engine (`SyncSession`) derived from `settings.database_url` with the `+asyncpg` suffix stripped. Uses `psycopg2-binary`.

---

## Storage

S3-compatible. Configured via `S3_ENDPOINT` / `S3_ACCESS_KEY` / `S3_SECRET_KEY` / `S3_BUCKET` env vars.

**Upload protocol** (3 hops):

1. `POST /assets/upload` → server creates Asset row (status `uploading`) + returns presigned PUT URL
2. Client PUTs bytes directly to S3 — server never sees them
3. `POST /assets/{id}/confirm` → server `HEAD`s the object, records size + etag, flips status to `ready`

**Storage key shape**: `orgs/<org_id_or_global>/<kind>/<uuid>.<ext>`. Org-prefixed for defense in depth.

---

## Knowledge Graph

The agent's memory. Every ingested document is chunked + embedded into a `DocumentChunk` row with a 1536-dim `embedding` column.

**Embedding provider**: OpenAI `text-embedding-3-small` if `OPENAI_API_KEY` is set, else deterministic SHA-256 stub.

**ANN index**: IVFFlat with `vector_cosine_ops` (100 lists). Fast cosine similarity over the embedding column.

**Query path** (`POST /api/v1/kg/search`):
1. Embed the user's query text
2. `ORDER BY embedding <=> :query_vector` (cosine distance) on `document_chunks` scoped to the Org
3. Return top-k chunks with `similarity = 1 - distance`

---

## Agents (Phase 2)

**Creatives Agent** (v0.1 — direct Claude API, no Agent SDK):

```
Brief (user)
   │
   ▼
Active BrandKit (per-Org)    KG retrieval (top-5)
   │                              │
   └────────────┬─────────────────┘
                ▼
       System + User prompt
                │
                ▼
      Anthropic SDK (or stub)
                │
                ▼
       parse_variants() → N strings
                │
                ▼
     ApprovalRequest × N (status=pending)
                │
                ▼
     Approval Inbox UI (`/inbox`)
```

Variants are **never published directly** — the Hard-gate rule (PLAN-v1.2 §v2.0 §5.2) routes everything through the Approval Inbox.

**Future** (v0.2+): Claude Agent SDK + MCP for proper sub-agent orchestration, tool use, multi-turn reasoning traces. The Conductor agent + SMM/SEO/Paid Media/Analyst agents follow.

---

## Approval queue & audit

Every consequential action (approve, reject, future publish) writes an `AuditEvent`:

```
{
  organization_id,
  actor_kind: user | agent | system,
  actor_user_id | actor_agent: "creatives_agent_v1",
  action_type: "approval.approved" | "approval.rejected" | ...,
  target_type, target_id,
  payload_json,
  result: success | failure,
  ip_address, user_agent,
  approval_request_id (back-link)
}
```

**4-eye rule**: a user cannot decide on their own ApprovalRequest. Agent-initiated requests have no human "owner" so any admin/manager/reviewer can decide.

---

## Frontend

Next.js 14 App Router. Brand-themed via `frontend/src/styles/brand.css` (DClaw design-kit tokens — light mode only).

**Routes**:

| Route | Purpose |
|---|---|
| `/login`, `/first-login` | Auth flow |
| `/` | Dashboard |
| `/agents/creatives` | Creatives Station — kick off agent runs |
| `/inbox` | Approval Inbox — decide pending items |
| `/admin/users` | Admin user management |
| `/campaigns`, `/leads` | Legacy v1.0 views (still wired) |

**State**: React hooks. Token in `localStorage`. `AuthGuard` client component redirects unauthenticated users to `/login` and password-reset-required users to `/first-login`.

---

## Observability (v0.1 minimal)

| Concern | Where |
|---|---|
| Backend logs | stdout (structured JSON in v0.2) |
| Frontend errors | Browser console (Sentry in v0.2) |
| Healthchecks | `/health/` (liveness), `/health/ready` (readiness — coming in v0.2) |
| Metrics | Prometheus exporter — coming in v0.2 |
| Tracing | OpenTelemetry → OTLP — coming in v0.2 |

---

## Testing strategy

**Backend** (pytest + pytest-asyncio):

- Unit tests for pure functions (embeddings stub, text chunking, password generation, variant parsing)
- Integration tests via httpx AsyncClient against the real FastAPI app + real Postgres + pgvector
- External services (S3, Celery dispatch, Anthropic, OpenAI) **mocked via monkeypatch** so tests run hermetically with zero external dependencies
- `conftest.py` drops + recreates all tables per test via `Base.metadata.drop_all/create_all` + `CREATE EXTENSION IF NOT EXISTS vector`

Test count by file: see `backend/tests/test_*.py`. Aggregate ~100 tests as of v0.1.

**Frontend**: build-time TypeScript checks via `npm run build` (no runtime tests yet — added in v0.2 via Playwright).

**CI** (`.github/workflows/ci.yml`):
- pgvector/pgvector:pg16 Postgres service
- `python -m pytest -v --tb=short` for backend
- `npm run build` for frontend

Plus **poll-and-merge bot** (`.github/workflows/auto-merge.yml`) which merges PRs labeled `auto-merge` once all status checks pass — works around the org-level block on GitHub's native auto-merge.

---

## Deployment

**Dev**: `docker compose up -d` — full stack on a laptop.

**Prod (target — v0.2)**: Helm chart at `helm/dclaw-marketing`. Customer brings a pre-existing Kubernetes cluster (k8s 1.28+); `helm install dclaw-marketing dclaw/dclaw-marketing` deploys everything. Bundled defaults for Postgres / Redis / MinIO via subcharts; production customers override with managed services (RDS, ElastiCache, S3).

See PLAN-v1.2.md §Appendix A.2 for the full chart shape.

---

## Sprint 4 additions (v1.1.2)

- **Model Registry** (`ModelProvider`, `ModelEntry`, `ModelCallLog`,
  `OrgModelAssignment`, `UserModelPreference`) under
  `app.models.model_registry` + `model_call_log` + `model_assignment`.
- **Model Resolver** (`app/services/model_resolver.py`) — single
  resolution point with priority chain `user → org → pool → env → stub`.
- **Agent Runtime** (`app/agents/runtime.py`) — resolver-aware
  completion + Conductor decomposition; called by `agents/roles.py`
  with seven curated role-agent system prompts.
- **Approval 4-eye + trace replay** — `approvers_required` /
  `approvers_user_ids_json` on `ApprovalRequest`; trace stitched from
  `ModelCallLog.request_id`.
- **Generation adapters** (`app/services/generation_adapters.py`) —
  Replicate / Runway / Suno / ElevenLabs / Cartesia / Deepgram.
- **Workflow Runner** — sandbox harness + 5 production templates +
  failure playbook.
- **Observability** — `app/core/otel.py` OTLP tracing initializer;
  Grafana dashboard JSON under `monitoring/grafana/`.
- **Frontend surfaces** — `/admin/models`, `/conductor`,
  `/workflows/templates`, `/settings/2fa` and the in-Conductor
  `ModelSettingsPanel` + `InlineModelSelector` + `ModelGateBanner`.
