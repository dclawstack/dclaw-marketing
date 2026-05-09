# Repo Structure — dclaw-marketing

This vault IS the repo root. Links below resolve to actual files in the project.
Remote: [github.com/dclawstack/dclaw-marketing](https://github.com/dclawstack/dclaw-marketing)

## Root docs

- [README](README.md)
- [AGENTS](AGENTS.md)
- [AGENT-PROMPTS](AGENT-PROMPTS.md)
- [PLAN-v1.2](PLAN-v1.2.md)
- [PRODUCT-SPEC](PRODUCT-SPEC.md)
- [PRODUCT-SPEC template](PRODUCT-SPEC.md.template)
- [SCALING-PLAYBOOK](SCALING-PLAYBOOK.md)
- [TEAM-ONBOARDING-GUIDE](TEAM-ONBOARDING-GUIDE.md)
- [Welcome](Welcome.md)

## Infra

- [docker-compose.yml](docker-compose.yml)
- [.env.example](.env.example)
- [.github/workflows/ci.yml](.github/workflows/ci.yml)

## backend/

- [Dockerfile](backend/Dockerfile)
- [requirements.txt](backend/requirements.txt)
- [alembic.ini](backend/alembic.ini)

### backend/alembic/

- [env.py](backend/alembic/env.py)
- [script.py.mako](backend/alembic/script.py.mako)
- [versions/](backend/alembic/versions/)

### backend/app/

- [api/main.py](backend/app/api/main.py)
- [api/routes/](backend/app/api/routes/)
- [api/v1/](backend/app/api/v1/)
- [core/config.py](backend/app/core/config.py)
- [core/database.py](backend/app/core/database.py)
- [models/base.py](backend/app/models/base.py)
- [models/analytics_event.py](backend/app/models/analytics_event.py)
- [models/campaign.py](backend/app/models/campaign.py)
- [models/lead.py](backend/app/models/lead.py)
- [repositories/base_repo.py](backend/app/repositories/base_repo.py)
- [repositories/analytics_event_repo.py](backend/app/repositories/analytics_event_repo.py)
- [repositories/campaign_repo.py](backend/app/repositories/campaign_repo.py)
- [repositories/lead_repo.py](backend/app/repositories/lead_repo.py)
- [schemas/analytics_event.py](backend/app/schemas/analytics_event.py)
- [schemas/campaign.py](backend/app/schemas/campaign.py)
- [schemas/lead.py](backend/app/schemas/lead.py)
- [services/](backend/app/services/)
- [utils/](backend/app/utils/)

### backend/tests/

- [conftest.py](backend/tests/conftest.py)
- [test_analytics.py](backend/tests/test_analytics.py)
- [test_campaigns.py](backend/tests/test_campaigns.py)
- [test_dashboard.py](backend/tests/test_dashboard.py)
- [test_health.py](backend/tests/test_health.py)
- [test_leads.py](backend/tests/test_leads.py)

## frontend/

- [Dockerfile](frontend/Dockerfile)
- [package.json](frontend/package.json)
- [tsconfig.json](frontend/tsconfig.json)
- [next.config.mjs](frontend/next.config.mjs)
- [tailwind.config.ts](frontend/tailwind.config.ts)
- [postcss.config.mjs](frontend/postcss.config.mjs)

### frontend/src/

- [app/layout.tsx](frontend/src/app/layout.tsx)
- [app/page.tsx](frontend/src/app/page.tsx)
- [app/globals.css](frontend/src/app/globals.css)
- [app/campaigns/](frontend/src/app/campaigns/)
- [app/leads/](frontend/src/app/leads/)
- [components/ui/](frontend/src/components/ui/)
- [lib/api.ts](frontend/src/lib/api.ts)
- [lib/utils.ts](frontend/src/lib/utils.ts)

## helm/

- [Chart.yaml](helm/Chart.yaml)
- [values.yaml](helm/values.yaml)
- [templates/deployment.yaml](helm/templates/deployment.yaml)
- [templates/service.yaml](helm/templates/service.yaml)
- [templates/secrets.yaml](helm/templates/secrets.yaml)
- [templates/_helpers.tpl](helm/templates/_helpers.tpl)
- [templates/NOTES.txt](helm/templates/NOTES.txt)
