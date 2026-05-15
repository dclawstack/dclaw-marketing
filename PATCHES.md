# Active Scaffold Patches

> **Hub-master index.** Lists every active org-wide patch held at this hub root.
> Use `./scaffold-sync.sh` to propagate these into each `dclaw-*` repo.
>
> When patches mature, they roll up into `PLAN-v1.3.md` (then `v1.4`, etc.) and
> the patch files retire from this list.

## Conventions

- File naming: `PATCH-YYYY-MM-DD-<short-slug>.md`
- One patch = one concrete, dated change to org-wide guidance
- Patches are **additive** and self-contained — they don't modify earlier patches or PLAN files
- An in-repo copy of a patch may live next to the manifest/code it documents (e.g. `dclaw-platform/PATCH-...md` next to the YAML it explains); the hub-root file is the master

## Active patches

| Patch | Topic | Affects | In-repo copy |
|---|---|---|---|
| `PATCH-2026-05-15-shared-hub-postgres.md` | Shared hub postgres made durable; auto-creates `dclaw_<app>` DB per app | All apps with a DB on hub testbed | `dclaw-platform/PATCH-2026-05-15-shared-hub-postgres.md` |

## Retired patches

_(None yet — first PLAN-v1.3 rollup will list what was folded in.)_

## See also

- `AGENTS.md` (this hub root) — org-wide agent context master
- `dclaw-platform/agents/` — per-role agent prompts
- `dclaw-platform/agents/swarm-dispatch/` — per-app build-prompt dispatcher
- `scaffold-sync.sh` (this hub root) — propagate patches into `dclaw-*` repos
