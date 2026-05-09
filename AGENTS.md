# DClaw App — Agent Development Guide

> **Read this file first before making any code changes.**
> This document is the source of truth for architecture, anti-patterns, and development workflow.

## App Identity

**DClaw Marketing** is a vertical SaaS application built on the DClaw Stack.

- **Backend Port:** `8102` (FastAPI)
- **Frontend Port:** `3015` (Next.js)
- **Database:** `dclaw_marketing` (PostgreSQL)
- **Base API Path:** `/api/v1`

## Architecture Lock — DO NOT CHANGE

These are non-negotiable. If an agent suggests changing them, reject it.

### Backend
- **FastAPI** with `lifespan` handler
- **SQLAlchemy 2.0** — `DeclarativeBase` from `app.models.base`, NOT `declarative_base()`
- **Pydantic v2** schemas with `ConfigDict(from_attributes=True)`
- **Async SQLAlchemy** — `create_async_engine` + `AsyncSession`
- **Repository pattern** — all DB access through `app/repositories/`
- **Dependency injection** — `Depends(get_db)`, never manual `AsyncSession`
- **NO MOCK DATA** — never use in-memory `dict`s
- **pytest-asyncio==0.24.0** — pinned version, do not upgrade

### Frontend
- **Next.js 14+ App Router**
- **Tailwind CSS** + **custom UI components** (pre-built in `src/components/ui/`)
- **API client** in `src/lib/api.ts` — typed fetch wrapper
- **Environment variables** — `NEXT_PUBLIC_API_URL` baked at build time. Dockerfile MUST declare `ARG NEXT_PUBLIC_API_URL`.
- **DO NOT install shadcn CLI** — use the pre-built components in `src/components/ui/`
- **Brand system — `frontend/src/styles/brand.css` is the single source of truth.** All colors, type, spacing, radii, shadows, and motion MUST come from `--dk-*` tokens (or the shadcn HSL tokens that are remapped to them in `globals.css`). Never hardcode hex colors. Light mode only — do NOT add a `.dark { }` block, do NOT use `dark:` Tailwind variants. Brand font is **Poppins** (loaded via `next/font/google` in `app/layout.tsx`).

### Docker
- **Backend:** `python:3.11-slim`, non-root `appuser`, healthcheck with `python urllib.request.urlopen()`
- **Frontend:** `node:20-alpine`, port `3015`
- **Compose:** container port MUST match `EXPOSE`/`ENV PORT`

## Directory Structure

```
Marketing/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── main.py
│   │   │   ├── routes/health.py
│   │   │   └── v1/               # App-specific routers
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── database.py       # Base(DeclarativeBase), engine, get_db
│   │   ├── models/
│   │   │   ├── base.py
│   │   │   └── ...               # App-specific models
│   │   ├── repositories/         # CRUD layer
│   │   ├── schemas/              # Pydantic v2
│   │   └── services/             # Business logic / AI
│   ├── alembic/
│   ├── tests/
│   │   ├── conftest.py           # Test DB override, client fixture
│   │   └── __init__.py           # REQUIRED for pytest discovery
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/                  # Next.js App Router
│   │   ├── components/ui/        # Pre-built UI components (see below)
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── input.tsx
│   │   │   ├── label.tsx
│   │   │   ├── badge.tsx
│   │   │   ├── select.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── table.tsx
│   │   │   ├── tabs.tsx
│   │   │   └── avatar.tsx
│   │   └── lib/
│   │       ├── api.ts
│   │       └── utils.ts          # cn() helper
│   └── Dockerfile
├── docker-compose.yml
├── .github/workflows/ci.yml      # DO NOT DELETE
├── helm/
└── .env.example
```

## Pre-Built UI Components

The scaffold includes working UI components in `frontend/src/components/ui/`. **Use these directly.** Do NOT install shadcn CLI or `@base-ui/react`.

Available components:
- `Button` — variants: default, destructive, outline, secondary, ghost, link
- `Card` — Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter
- `Input` — standard text input
- `Label` — form label
- `Badge` — variants: default, secondary, destructive, outline
- `Select` — native select with onValueChange support
- `Dialog` — modal with trigger, content, header, title
- `Table` — Table, TableHeader, TableBody, TableRow, TableHead, TableCell
- `Tabs` — Tabs, TabsList, TabsTrigger, TabsContent
- `Avatar` — Avatar, AvatarImage, AvatarFallback

## Anti-Patterns — NEVER DO

| Anti-Pattern | Why It Breaks Things | Correct Alternative |
|--------------|---------------------|---------------------|
| `declarative_base()` in `database.py` | Separate metadata → zero tables | `from app.models.base import Base` |
| `curl` in healthcheck on `python:*-slim` | No `curl` → silent failure | `python -c "import urllib.request; urllib.request.urlopen(...)"` |
| In-memory `MOCK_*` dicts | Data lost on restart | Create repository + real DB |
| Missing `ARG NEXT_PUBLIC_API_URL` | Wrong API URL baked in | Add `ARG NEXT_PUBLIC_API_URL` before build |
| Manual `get_db()` with `__anext__()` | Session leaks | `Depends(get_db)` |
| Hardcoded `localhost:PORT` | Breaks Docker/K8s | Use `process.env.NEXT_PUBLIC_API_URL` |
| No alembic migration for new models | Schema drift | `alembic revision --autogenerate` |
| **Installing `shadcn` CLI v4** | Breaks Tailwind v3 build | Use pre-built components in scaffold |
| **Using `@base-ui/react`** | Incompatible with Tailwind v3 | Use pre-built components in scaffold |
| **Using non-standard Postgres port in tests** | CI service maps 5432 only | Always use `localhost:5432` in conftest.py |
| **Upgrading `pytest-asyncio`** | v1.3.0 breaks fixture scoping | Keep `pytest-asyncio==0.24.0` pinned |
| **Deleting `.github/workflows/ci.yml`** | No CI runs, no quality gate | Leave CI workflow intact |

## Database Rules

1. All models MUST inherit from `Base` in `app.models.base`
2. All models MUST use `Mapped[...]` and `mapped_column()`
3. **Never use `default_factory=` in `mapped_column()`** — use `default=` instead
3. Relationships MUST specify `lazy="selectin"`
4. All new tables MUST get an alembic migration
5. Use `ondelete="CASCADE"` for child tables
6. Use `ondelete="SET NULL"` for optional references

## How to Add a Feature

1. **Read this file** and `PLAN-v1.2.md`
2. **Backend:**
   - Add/update model in `app/models/`
   - Add/update schema in `app/schemas/`
   - Add repository in `app/repositories/`
   - Add/update router in `app/api/v1/`
   - Add tests in `tests/`
   - Generate alembic migration
3. **Frontend:**
   - Add API types/functions to `src/lib/api.ts`
   - Add page in `src/app/` or component using pre-built UI components
4. **Docker:** Verify `docker compose config` and `docker compose up -d`
5. **Commit** with conventional commit message

## Testing Requirements

- Every new repository MUST have tests
- Every new router endpoint MUST be covered
- Use `pytest-asyncio` with `async` test functions and `@pytest.mark.asyncio`
- Use `httpx.AsyncClient` with `ASGITransport`
- Override `get_db` dependency with test session in `conftest.py`
- Tests MUST use `localhost:5432` for PostgreSQL (CI requirement)

## Port Registry

| App | Backend | Frontend | Postgres DB |
|-----|---------|----------|-------------|
| dclaw-chat | 8090 | 3000 | dclaw_chat |
| dclaw-med | 8092 | 3004 | dclaw_med |
| dclaw-learn | 8093 | 3003 | dclaw_learn |
| dclaw-code | 8094 | 3005 | dclaw_code |
| dclaw-legal | 8099 | 3013 | dclaw_legal |
| dclaw-crm | 8095 | 3006 | dclaw_crm |
| dclaw-finance | 8096 | 3007 | dclaw_finance |
| dclaw-hr | 8097 | 3008 | dclaw_hr |
| **TBD #9** | **8098** | **3009** | **dclaw_xxx** |
| **TBD #10** | **8100** | **3010** | **dclaw_xxx** |
