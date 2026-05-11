# Project Dashboard

Live view of the build status. The GitHub Project Board is authoritative; this page summarizes it for the vault.

## Live links

- **Project Board:** https://github.com/orgs/dclawstack/projects/1
- **All issues:** https://github.com/dclawstack/dclaw-marketing/issues
- **Open PRs:** https://github.com/dclawstack/dclaw-marketing/pulls
- **Actions runs:** https://github.com/dclawstack/dclaw-marketing/actions

## Deadline & cadence

- **Deadline:** Friday **2026-05-15 23:59** IST
- **Presentation day:** Saturday 2026-05-16 (morning buffer for last-minute fixes)
- **Working rhythm:** Claude Code pushes feature branches → opens PR with `auto-merge` label → CI green → PR merges itself → issues auto-tracked on the board

## Phase plan

| Phase | Scope | Target |
|---|---|---|
| **0. Baseline** | CRM rename · A0 alembic baseline · A1 Auth/Org/User/Project · A2 Celery+Redis · A3 S3/MinIO · A4 Audit+Approval · Helm chart rebuild | Tue–Wed |
| **1. Theme Q — Foundation** | Q1 Brand Setup Studio · Q2 Input Channel Hub · Q3 Knowledge Graph · Q5 Goals · Q6 Project Wizard | Wed–Thu |
| **2. Agent runtime + Creatives MVP** | Claude Agent SDK · Conductor shell · Creatives Agent end-to-end · Approval Inbox UI | Thu |
| **3. Role fleet (stretch)** | SMM · SEO · Paid Media · Analyst agents + their Stations | Fri |
| **4. Multi-channel publishing** | `SocialAccount` model · X / LinkedIn / IG adapters (mock) · Resend email (real) | Fri |
| **5. Docs + marketing + release** | README · USER-GUIDE · ARCHITECTURE · API ref · slides · one-pager · video script + recording · `v0.1.0-mvp` tag | Fri 22:00–23:59 |

## Custom field cheat sheet

The Project board has these custom fields. Click any column header in a Board view to group/filter by them:

- **Status** — Todo / In Progress / Done
- **Priority** — P0 (must) / P1 (should) / P2 (could) / Done
- **Track** — Code / Docs / Marketing / Infra / Planning
- **Phase** — Phase 0 / Phase 1 / Phase 2 / Phase 3 / Phase 4 / Phase 5 / Phase 6 / Done
- **Due Date** — Date the task must complete
- **Estimate Hours** — Rough effort

## Daily milestones

| Milestone | Due | Issues attached |
|---|---|---|
| Tue 2026-05-12 EOD | 23:59 today | CRM rename · A0 alembic · GH Actions project-automation |
| Wed 2026-05-13 EOD | end of Wednesday | A1 Auth · A2 Celery · A3 Storage · A4 Audit · Helm rebuild · Q1 Brand Setup · Q2 Input Hub · Q3 KG · Q5 Goals · auto-merge workflow |
| Thu 2026-05-14 EOD | end of Thursday | Q4 Freshness (P1) · Q6 Project Wizard · Phase 2 agents · release workflow |
| Fri 2026-05-15 — DEADLINE | **23:59 — submission** | Phase 3 agents · Phase 4 publishing · all docs · all marketing · `v0.1.0-mvp` tag |
| Sat 2026-05-16 — Presentation | morning | Buffer for last-minute fixes before the demo |

## Manual prerequisites (one-time)

These need a human (you):

- [ ] Add `PROJECT_TOKEN` repo secret (fine-grained PAT, Projects: Read+Write) — enables auto-add to project workflow
- [ ] Toggle Settings → General → Pull Requests → **Allow auto-merge** — enables the auto-merge workflow
- [ ] Merge **PR #58** (the workflows PR itself can't auto-merge until the workflow is on `main`) — one-time bootstrap
- [ ] Create 6 views on the Project board via UI (see [[Welcome]] for spec)

Once those are in place, the entire dev loop runs without manual hops.

## What's already shipped

See the **closed issues** filtered by `phase:Done`:
- v1.0 scaffold (Campaign / Lead / AnalyticsEvent CRUD, frontend pages, tests, CI)
- Brand system (DKube tokens, Poppins, light-mode-only) — [[PLAN-v1.2#Brand|see plan]]
- v2.0 vision addendum + Appendix A tech choices — merged in PR #8
- GitHub Project board, fields, milestones, labels, 49 issues
- Repo→Project link

## What's next

See the open issues sorted by Priority + Due Date. The "🔥 Now — P0 only" view on the board is the focused list.
