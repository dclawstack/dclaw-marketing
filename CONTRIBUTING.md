# Contributing to DClaw Marketing

Conventions for branching, commits, and PRs. Read once; it's short.

---

## Branch naming

- `feat/<theme>-<short-name>` — new feature (e.g., `feat/q3-knowledge-graph`)
- `fix/<short-name>` — bug fix
- `chore/<short-name>` — non-feature housekeeping (rename, deps, gitignore)
- `infra/<short-name>` — CI / Helm / Docker / dev-tooling
- `docs/<short-name>` — documentation only
- `hotfix/<short-name>` — emergency main-fix; merges direct

One PR per branch. Keep branches small.

---

## Commit messages

Conventional commits style:

```
<type>(<scope>): <short subject line>

<longer body — wrap at ~72 chars. Explain WHY, not just what.>

Co-Authored-By: <when paired with another author>
```

**Types**: `feat`, `fix`, `chore`, `infra`, `docs`, `test`, `refactor`.
**Scopes** (examples): `a1`, `a2`, `q1`, `agents`, `frontend`, `ci`, `db`.

Examples:
- `feat(q3): pgvector embeddings + KG semantic search + tests`
- `fix(q2): add psycopg2-binary — Celery sync session needs sync driver`
- `chore: gitignore .claude/ runtime state directory`

---

## PR workflow

1. **Cut a branch from latest `main`.** `git fetch origin && git checkout -b feat/...` off `origin/main`.
2. **Commit continuously** — every meaningful unit is its own commit so the history reads as a development timeline.
3. **Open the PR** with body sections: `## Summary` (what + why), `## Test plan` (checklist). Reference closing issues with `Closes #N` keywords.
4. **Label `auto-merge`** if you want the bot to land it when CI is green.
5. **CI must pass** — backend-tests + frontend-build green before merging.
6. **One squash commit per PR** on main. The bot does this automatically.

---

## Tests

> **If a test does not pass, first fix, test, once it is completely fixed, then progress to next.**

- **Every new feature ships with tests in the same PR.** No exceptions for production code paths.
- **Unit tests for pure functions** (parsers, formatters, embedders' stubs, etc.).
- **Integration tests via the FastAPI AsyncClient** for every new route. Verify happy path + at least one error path (403/404/409) + role gates.
- **Mock external services** (Anthropic, OpenAI, S3, Celery dispatch) via `monkeypatch`. Tests must run hermetically — no real API keys required in CI.
- Run locally: `cd backend && python -m pytest -v --tb=short`. CI runs the same.

---

## Critical rules (from README — enforced)

1. **DO NOT install shadcn CLI** — pre-built UI components are in `frontend/src/components/ui/`. Installing the CLI breaks the Tailwind v3 build.
2. **DO NOT change the Postgres test port** — `5432` everywhere.
3. **DO NOT delete `.github/workflows/ci.yml`**.
4. **DO NOT upgrade `pytest-asyncio`** — pinned at `==0.24.0`.
5. **All UI work uses `--dk-*` brand tokens** (`frontend/src/styles/brand.css`). Light mode only.

---

## Migrations

Every model change ships a matching Alembic revision in the same PR. Migration files live in `backend/alembic/versions/`.

Naming: `YYYYMMDD_NNNN_<slug>.py`. `revision`/`down_revision` strings chain explicitly. Generate with `alembic revision --autogenerate -m "<message>"` and inspect / clean up the generated file before committing.

---

## Code review

The Claude PR Review bot auto-reviews every PR. It's advisory — humans (you) merge. The bot's comments are starting points, not blockers.

---

## Releases

- Semver. `v<major>.<minor>.<patch>`.
- Tag with `git tag v0.x.y && git push origin v0.x.y`.
- The `release.yml` workflow builds + pushes container images to GHCR + creates a GitHub Release with auto-generated changelog.
- `main` is always green and tagable.
