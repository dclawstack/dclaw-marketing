# Architecture

## System diagram

```
Browser ─►  Next.js 14 (frontend, :3069)         [left-sidebar nav · brand tokens · admin]
                │
                │ /api/* rewrite proxy
                │   container: BACKEND_INTERNAL_URL=http://backend:8156
                │   local dev: NEXT_PUBLIC_API_URL
                ▼
            FastAPI 1.1.1 (backend, :8156)        [48 routers · 567 tests]
                │
   ┌────────────┼────────────┬─────────────┬──────────────┬───────────────┐
   ▼            ▼            ▼             ▼              ▼               ▼
 Postgres   Redis        MinIO         Anthropic       OpenAI         MCP Hub
 +pgvector  (cache +    (S3 API,       (Claude         (embeddings)   (14 adapters)
            Celery)     presigned)      Opus 4.7)
                │
                ▼  task queue
            Celery worker + Celery Beat
            (ingestion · agent runs · sequence runner · daily lead-rescore
             weekly Analyst narrative · monthly client reports · GDPR export
             KG embeddings · SEO daily pipeline)
```

## Component inventory

| Layer | Count | Location |
|-------|-------|----------|
| Backend routers | 48 | `backend/app/api/v1/` |
| Backend models | 26 | `backend/app/models/` |
| Alembic migrations | 33 | `backend/alembic/versions/` |
| Frontend pages | 72 | `frontend/src/app/**/page.tsx` |
| Test files | 77 | `backend/tests/` |
| Test functions | 567 | (pytest-asyncio) |

## Stack

| Layer | Tech |
|-------|------|
| Frontend | Next.js 14 (App Router) · React 18 · Tailwind v3 · shadcn-style components (no CLI) |
| Brand | `--dk-*` purple-palette tokens in `frontend/src/styles/brand.css` · Poppins · JetBrains Mono |
| Backend | FastAPI · SQLAlchemy 2.0 async · Pydantic v2 (`ConfigDict`) · Alembic · fastapi-users JWT |
| DB | Postgres 15 + pgvector for embeddings |
| Cache / queue | Redis + Celery (worker + beat) |
| Object storage | MinIO (S3-compatible, presigned uploads) |
| LLM | Anthropic Claude Opus 4.7 (default) · OpenAI for embeddings · provider swappable |
| Encryption | Fernet (operator-held master key) for SocialAccount tokens at rest |
| Auth | JWT (fastapi-users) · magic-link · TOTP columns shipped, UI in Sprint 4 |
| MCP | 14 adapters + BYO marketplace |
| Container | Docker Compose (dev) · Helm chart (prod) |
| CI | GitHub Actions: ci.yml · auto-merge.yml · project-status-sync.yml · release.yml |

## Port registry (DClaw vertical-app family)

| App | Backend | Frontend | DB |
|-----|---------|----------|----|
| dclaw-chat | 8090 | 3000 | dclaw_chat |
| dclaw-med | 8092 | 3004 | dclaw_med |
| dclaw-learn | 8093 | 3003 | dclaw_learn |
| dclaw-code | 8094 | 3005 | dclaw_code |
| dclaw-crm | 8095 | 3006 | dclaw_crm |
| dclaw-finance | 8096 | 3007 | dclaw_finance |
| dclaw-hr | 8097 | 3008 | dclaw_hr |
| dclaw-legal | 8099 | 3013 | dclaw_legal |
| **dclaw-marketing** | **8102** | **3015** | **dclaw_marketing** |

## Frontend surfaces (selected)

- `/dashboard` · `/orgs` · `/orgs/[id]` (tabbed)
- `/inbox` (Approval Inbox)
- `/library` · `/knowledge` · `/knowledge/sources/[id]`
- `/agents` · `/agents/seo` · `/brand` · `/brand-insights`
- `/channels` · `/campaigns` · `/calendar` · `/workflows`
- `/hooks` · `/variants` · `/repurpose` · `/heatmap` · `/pages` · `/playbooks`
- `/time` · `/retainer` · `/invoices`
- `/admin/users` · `/admin/audit` · `/admin/costs` · `/admin/quotas` · `/admin/health` · `/admin/integrations`

## Critical agent rules

1. **No shadcn CLI** — pre-built UI components live in `frontend/src/components/ui/`. CLI install breaks Tailwind v3.
2. **No Postgres test-port change** — `conftest.py` + `ci.yml` both use `localhost:5432`.
3. **No deleting `.github/workflows/ci.yml`** — kills CI.
4. **No `pytest-asyncio` upgrades** — pinned at `==0.24.0`; later versions break fixture scoping.
5. **All UI uses `--dk-*` brand tokens.** Light mode only. No hard-coded hex. No `dark:` variants.

## Related

- [[Project Overview]]
- [[Glossary]]
- [[Release Timeline]]
