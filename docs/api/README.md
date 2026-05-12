# API Reference

Interactive API documentation is built into the FastAPI backend.

## Live (when the stack is running)

- **Swagger UI** — http://localhost:8102/docs
- **ReDoc** — http://localhost:8102/redoc
- **OpenAPI JSON** — http://localhost:8102/openapi.json

## Static export

The committed [`docs/api/openapi.json`](openapi.json) file is a snapshot
of the OpenAPI schema for the latest release. Regenerate after schema
changes with:

```bash
cd backend
python scripts/export_openapi.py
# Writes ../docs/api/openapi.json
```

## Endpoint groups

| Prefix | Purpose | Auth |
|---|---|---|
| `/health/` | Liveness / readiness | none |
| `/api/v1/auth/*` | Login, refresh, password reset, verify (FastAPI-Users) | mixed |
| `/api/v1/me`, `/me/password` | Current user profile + mandatory first-login reset | bearer |
| `/api/v1/admin/users/*` | Admin user CRUD with temp-password issuance | superuser |
| `/api/v1/orgs`, `/orgs/{id}`, `/orgs/{id}/memberships` | Organization CRUD + membership | mixed |
| `/api/v1/orgs/{id}/projects/*` | Project CRUD + memberships | role-gated |
| `/api/v1/orgs/{id}/brand-kits/*` | Versioned Brand Kits (Theme Q1) | role-gated |
| `/api/v1/orgs/{id}/goals` | Goals / constraints / autonomy posture (Theme Q5) | role-gated |
| `/api/v1/assets/*` | Object storage — presigned upload + metadata | bearer |
| `/api/v1/ingest/*` | File ingestion → text → chunks (Theme Q2) | role-gated |
| `/api/v1/kg/search`, `/kg/stats` | Knowledge Graph semantic search (Theme Q3) | org member |
| `/api/v1/jobs/*`, `/jobs/{id}/stream` (SSE) | Background-job state | bearer |
| `/api/v1/agents/creatives/generate` | Creatives Agent run | role-gated |
| `/api/v1/approvals/*` | Approval queue (Hard-gate decisions) | role-gated |
| `/api/v1/campaigns`, `/leads`, `/analytics`, `/dashboard` | Legacy v1.0 routes | none (TBD) |

For URL parameters, request bodies, and response shapes, see the
interactive docs above or the committed `openapi.json`.

## Auth header

All `/api/v1/*` endpoints (except `/auth/*` themselves) expect:

```
Authorization: Bearer <jwt-access-token>
```

Get a token from `POST /api/v1/auth/jwt/login` with form-encoded
`username` (email) + `password`.

## Response shapes

The schema uses Pydantic v2 with strict typing. UUID fields are
strings (RFC 4122). Datetimes are ISO 8601 with timezone. Enums are
serialised as their string values (e.g., `"queued"`, `"approved"`).
