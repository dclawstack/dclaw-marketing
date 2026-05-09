# DClaw Marketing

> **A vertical SaaS app for marketing teams** — built on the DClaw Stack.
> Manage campaigns, track leads, and analyze performance in one place.

## Scope

DClaw Marketing is a full-stack marketing platform for **marketing teams and growth hackers**. It covers:

- **Campaign Management** — Create, schedule, and track email, social, PPC, and content campaigns
- **Lead Management** — Capture and manage leads with full lifecycle tracking (new → contacted → qualified → converted)
- **Analytics** — Track impressions, clicks, conversions, and bounces per campaign
- **Dashboard** — Real-time summary of active campaigns, total leads, conversion rates, and total spend

**Tech Stack:** FastAPI (Python 3.11) · Next.js 14 · PostgreSQL · Docker · Kubernetes (Helm)  
**Ports:** Backend `8102` · Frontend `3015` · Database `dclaw_marketing`

---

## v1.0 Features (Current)

- [x] Campaign CRUD — create, read, update, delete campaigns with type (`email`, `social`, `ppc`, `content`) and status filters
- [x] Lead CRUD — manage leads with source tracking and optional campaign association
- [x] Analytics event recording — log impressions, clicks, conversions, and bounces
- [x] Dashboard — summary cards (active campaigns, total leads, conversion rate, spend)
- [x] Campaign detail page — lead list and analytics summary per campaign
- [x] Docker + docker-compose deployment with healthchecks
- [x] Helm chart for Kubernetes deployment
- [x] Alembic database migrations
- [x] Backend test suite (pytest-asyncio)

---

## v1.2 Features

### P0 — Must Have

#### 1. AI Lead Scoring
**Description:** Score each lead from 1–100 based on attributes (company, source, engagement history) to prioritize outreach.
- **Backend:** Scoring service in `app/services/lead_scoring.py`, exposed via `GET /api/v1/leads/{id}/score`
- **Frontend:** Score badge on lead cards and lead detail page

#### 2. Real Analytics Dashboard
**Description:** Replace mock chart data with live aggregated analytics from the `AnalyticsEvent` table.
- **Backend:** Aggregation query in `GET /api/v1/dashboard` returning real counts and time-series trends
- **Frontend:** Live performance chart on Dashboard and Campaign Detail pages

### P1 — Should Have

#### 3. Campaign Send-Time Optimization
**Description:** Suggest the best time to send/activate a campaign based on historical engagement patterns.
- **Backend:** Optimization service in `app/services/campaign_optimizer.py` returning a suggested `start_date`/time
- **Frontend:** "Optimize Schedule" button on the campaign create/edit form

#### 4. Bulk Lead Status Management
**Description:** Select multiple leads and update their status in a single action.
- **Backend:** `PATCH /api/v1/leads/bulk` accepting a list of lead IDs and a target status
- **Frontend:** Checkbox selection + bulk action toolbar on the Leads table

### P2 — Could Have

#### 5. Email Campaign Integration
**Description:** Connect campaigns to an email provider (SendGrid / Mailgun) to send actual emails to associated leads.
- **Backend:** Email service abstraction in `app/services/email.py` with provider config in `app/core/config.py`
- **Frontend:** "Send Campaign" action button on Campaign Detail page

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, Alembic |
| Frontend | Next.js 14, Tailwind CSS, pre-built UI components |
| Database | PostgreSQL (`dclaw_marketing`) |
| Deployment | Docker, docker-compose, Kubernetes (Helm) |
| Testing | pytest, pytest-asyncio==0.24.0 |

---

## Critical Rules for Agents

### DO NOT install shadcn CLI
The scaffold includes pre-built UI components in `frontend/src/components/ui/`. Installing `shadcn` v4 or `@base-ui/react` will break the Tailwind v3 build.

### DO NOT change the Postgres test port
`backend/tests/conftest.py` uses `localhost:5432`. GitHub Actions CI maps the Postgres service to port 5432. Changing this breaks CI.

### DO NOT delete `.github/workflows/ci.yml`
This file is required for GitHub Actions to run tests on every push.

### DO NOT upgrade pytest-asyncio
Keep `pytest-asyncio==0.24.0` pinned in `requirements.txt`. v1.3.0 breaks fixture scoping.

---

## Port Registry

| App | Backend Port | Frontend Port | Database |
|-----|-------------|---------------|----------|
| dclaw-chat | 8090 | 3000 | dclaw_chat |
| dclaw-med | 8092 | 3004 | dclaw_med |
| dclaw-learn | 8093 | 3003 | dclaw_learn |
| dclaw-code | 8094 | 3005 | dclaw_code |
| dclaw-legal | 8099 | 3013 | dclaw_legal |
| dclaw-crm | 8095 | 3006 | dclaw_crm |
| dclaw-finance | 8096 | 3007 | dclaw_finance |
| dclaw-hr | 8097 | 3008 | dclaw_hr |
| **dclaw-marketing** | **8102** | **3015** | **dclaw_marketing** |
| **TBD #10** | **8100** | **3010** | **dclaw_xxx** |

> **Rule:** New apps take the next available port. Update this table when assigning.

---

## Key Files

| File | Purpose |
|------|---------|
| `PRODUCT-SPEC.md` | Domain models, business logic, API endpoints |
| `PLAN-v1.2.md` | v1.2 feature roadmap for coding agents |
| `AGENTS.md` | Architecture rules and development guide |
| `SCALING-PLAYBOOK.md` | Parallel agent workflow |
| `backend/app/core/config.py` | App name, database name |
| `frontend/src/lib/api.ts` | Typed API client |

---

## Contributors

- [Deepro Mallick (@deepro713)](https://github.com/deepro713)
