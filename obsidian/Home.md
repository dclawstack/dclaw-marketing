# DClaw Marketing — Vault Home

> Snapshot taken at **v1.1.1** (Sprint 3 closeout, 2026-05-14).
> The single source of truth for current repo state is `git log` / `gh issue list`; this vault summarises the human-readable shape of the project.

---

## Quick links

- [[Project Overview]] — what DClaw Marketing is and who it's for
- [[Release Timeline]] — v1.0.0 → v1.1.0 → v1.1.1 → v1.2.0 plan
- [[Sprint Timeline]] — Sprint 1, 2, 3 highlights
- [[Architecture]] — components, ports, tech stack
- [[Open Issues]] — what's still open in GitHub
- [[Glossary]] — terms and acronyms
- [[reports/sprint-3-status-2026-05-14|Sprint 3 Status Report (HTML)]]
- [[reports/sprint-2-status-2026-05-13|Sprint 2 Status Report (HTML)]]
- [[reports/sprint-1-status-2026-05-12|Sprint 1 Status Report (HTML)]]

---

## Current posture

| | |
|---|---|
| **Latest release** | `v1.1.1` (Sprint 3 closeout, 2026-05-14) |
| **Plan completion** | ≈ 95 % of `PLAN-v1.2.md` scope |
| **Operator readiness** | ✅ Two-tier admin model, slug scheme, left sidebar, drain-self CI |
| **Open issues** | 5, all marketing collaterals (off-limits to engineering) |
| **Next milestone** | `v1.2.0` — demo posture (Brand Studio polish, real OAuth, observability) |

---

## Working rules (from durable memory)

- **Continuous-commit cadence** — medium-to-major changes get committed as they land; no batching.
- **GitHub Project workflow** — every task: issue → board Todo → In Progress on start → PR with `Closes #N` → Done on merge.
- **Marketing directory off-limits** — `marketing/` tree, issues #49–#53, marketing PRs are owned out-of-band by the operator.
- **Local rebuild after every change** — affected docker container is rebuilt + restarted so `localhost` always shows the latest.
- **Sprint boundaries** — Sprint 1 closed 2026-05-12; Sprint 2 was 2026-05-13; Sprint 3 was 2026-05-12 evening → 2026-05-14.

---

## Repository ground-truth

```
backend/    FastAPI 1.1.1 · 48 routers · 26 models · 33 migrations · 567 tests
frontend/   Next.js 14 · 72 pages · brand-token UI · left-sidebar nav
helm/       Kubernetes Helm chart
docs/       ARCHITECTURE · USER-GUIDE · api/README
obsidian/   This vault
scripts/    RESTORE_RUNBOOK + ops helpers
.github/    CI · auto-merge · release · project-automation workflows
```
