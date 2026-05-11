# Repo Structure — dclaw-marketing

This vault IS the repo root. Links below resolve to actual files.
Remote: [github.com/dclawstack/dclaw-marketing](https://github.com/dclawstack/dclaw-marketing) · Project: [DClaw Marketing Project](https://github.com/orgs/dclawstack/projects/1)

## Obsidian vault entry points

- [[Welcome]] — vault landing
- [[PROJECT-DASHBOARD]] — live build dashboard
- [[GLOSSARY]] — terms used across the docs
- [[Repo Structure]] — you are here

## Top-level docs

- [[PLAN-v1.2|PLAN-v1.2]] — **source of truth.** Includes v1.2 roadmap + v2.0 Vision addendum + Appendix A (tech choices & Helm shape)
- [[AGENTS|AGENTS]] — architecture rules for coding agents; brand-system enforcement
- [[AGENT-PROMPTS|AGENT-PROMPTS]] — agent system prompts (scaffold legacy; may be re-purposed)
- [[PRODUCT-SPEC|PRODUCT-SPEC]] — domain spec
- [[README|README]] — public-facing project intro
- [[SCALING-PLAYBOOK|SCALING-PLAYBOOK]] — scaffold meta-doc (left as-is from template)
- [[TEAM-ONBOARDING-GUIDE|TEAM-ONBOARDING-GUIDE]] — scaffold meta-doc (left as-is from template)

## Configuration

- [.env.example](.env.example)
- [.gitignore](.gitignore)
- [docker-compose.yml](docker-compose.yml)

## .github/

- [workflows/ci.yml](.github/workflows/ci.yml) — pytest + lint
- [workflows/claude.yml](.github/workflows/claude.yml) — @claude bot trigger
- [workflows/claude-code-review.yml](.github/workflows/claude-code-review.yml) — auto PR review
- *coming via [PR #58](https://github.com/dclawstack/dclaw-marketing/pull/58):*
  - `workflows/project-automation.yml` — auto-add issues/PRs to Project #1
  - `workflows/auto-merge.yml` — auto-merge on `auto-merge` label
  - `workflows/release.yml` — build + push images on `v*.*.*` tag

## backend/

- [Dockerfile](backend/Dockerfile)
- [requirements.txt](backend/requirements.txt)
- [alembic.ini](backend/alembic.ini)

### backend/alembic/

- [env.py](backend/alembic/env.py)
- [script.py.mako](backend/alembic/script.py.mako)
- [versions/](backend/alembic/versions/) — *empty; baseline migration coming in issue [#19](https://github.com/dclawstack/dclaw-marketing/issues/19)*

### backend/app/

- [api/main.py](backend/app/api/main.py) — FastAPI app entry
- [api/routes/health.py](backend/app/api/routes/health.py)
- [api/v1/campaigns.py](backend/app/api/v1/campaigns.py)
- [api/v1/leads.py](backend/app/api/v1/leads.py)
- [api/v1/analytics.py](backend/app/api/v1/analytics.py)
- [core/config.py](backend/app/core/config.py)
- [core/database.py](backend/app/core/database.py)
- [models/base.py](backend/app/models/base.py)
- [models/campaign.py](backend/app/models/campaign.py) · [models/lead.py](backend/app/models/lead.py) · [models/analytics_event.py](backend/app/models/analytics_event.py)
- [repositories/](backend/app/repositories/) — Campaign / Lead / AnalyticsEvent repos
- [schemas/](backend/app/schemas/) — Pydantic v2 schemas
- [services/](backend/app/services/) — *empty; populated phase-by-phase*
- [utils/](backend/app/utils/)

### backend/tests/

- [conftest.py](backend/tests/conftest.py)
- [test_health.py](backend/tests/test_health.py) · [test_campaigns.py](backend/tests/test_campaigns.py) · [test_leads.py](backend/tests/test_leads.py) · [test_analytics.py](backend/tests/test_analytics.py) · [test_dashboard.py](backend/tests/test_dashboard.py)

## frontend/

- [Dockerfile](frontend/Dockerfile)
- [package.json](frontend/package.json) · [tsconfig.json](frontend/tsconfig.json) · [next.config.mjs](frontend/next.config.mjs)
- [tailwind.config.ts](frontend/tailwind.config.ts)
- [postcss.config.mjs](frontend/postcss.config.mjs)

### frontend/src/

- [app/layout.tsx](frontend/src/app/layout.tsx) — root layout, loads Poppins via `next/font`
- [app/page.tsx](frontend/src/app/page.tsx) — Dashboard
- [app/globals.css](frontend/src/app/globals.css) — imports brand.css, remaps shadcn HSL tokens to DKube palette
- [app/campaigns/](frontend/src/app/campaigns/) · [app/leads/](frontend/src/app/leads/)
- [components/ui/](frontend/src/components/ui/) — pre-built shadcn-style components (Button, Card, Input, Dialog, Table, Tabs, …)
- [lib/api.ts](frontend/src/lib/api.ts) — typed fetch client
- [lib/utils.ts](frontend/src/lib/utils.ts) — `cn()` helper
- [styles/brand.css](frontend/src/styles/brand.css) — **single source of truth** for design tokens (DKube palette, type, spacing, radii, shadows, motion)

## helm/

- [Chart.yaml](helm/Chart.yaml) — *currently named `dclaw-crm` (from scaffold); rename to `dclaw-marketing` in issue [#18](https://github.com/dclawstack/dclaw-marketing/issues/18)*
- [values.yaml](helm/values.yaml)
- [templates/deployment.yaml](helm/templates/deployment.yaml)
- [templates/service.yaml](helm/templates/service.yaml)
- [templates/secrets.yaml](helm/templates/secrets.yaml)
- [templates/_helpers.tpl](helm/templates/_helpers.tpl)
- [templates/NOTES.txt](helm/templates/NOTES.txt)
