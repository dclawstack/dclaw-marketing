# PATCH 2026-05-15 — Shared hub postgres (durable + auto-init)

**Scope:** Hub testbed (Mac Studio K3s) only. Does **not** apply to end-user installs — those ship each app with its own bundled database.

**Status:** Active patch. Will roll up into `PLAN-v1.3.md` when matured.

**Owner:** SRE / Platform.

**Supersedes:** the pre-2026-05-15 behaviour where `dclaw/postgres` ran without a PVC, scaled to 0, and only initialized `dclaw_learn`.

---

## What changed

The shared `dclaw/postgres` Deployment is now **durable** (10 Gi `local-path` PVC) and **auto-initialises every dclaw_* database** on first boot. Apps running on the hub no longer have to create their own database manually.

| Item | Before | After |
|---|---|---|
| Storage | none (ephemeral) | `postgres-data` PVC, 10 Gi, `local-path` SC |
| Databases on first boot | `dclaw_learn` only | `dclaw_agent`, `dclaw_chat`, `dclaw_design`, `dclaw_flow`, `dclaw_learn`, `dclaw_research`, `dclaw_video` |
| Replicas | 0 | 1 (strategy: `Recreate` because PVC is RWO) |
| Probes | none | `pg_isready` readiness + liveness |
| Manifest location | inline in cluster only | `dclaw-platform/services/postgres/postgres-shared.yaml` |

The init script is idempotent (`CREATE DATABASE ... WHERE NOT EXISTS ...\gexec`) so the manifest can be re-applied safely.

---

## What this means for your app

If your app runs on the hub and needs a database, **nothing changes in your code**. Your `DATABASE_URL` continues to work as scaffolded:

```
postgresql+asyncpg://dclaw:dclaw@dclaw-<app>-db-rw:5432/dclaw_<app>
```

The naming convention is:

- **Service:** `dclaw-<app>-db-rw` (ExternalName, aliases to `postgres.dclaw.svc.cluster.local`)
- **Database:** `dclaw_<app>` (created automatically on first postgres boot)
- **User / Password:** `dclaw` / `dclaw` (shared across all apps; **hub-only**, not for production)

So `dclaw-agent` → uses DB `dclaw_agent`, `dclaw-chat` → uses DB `dclaw_chat`, etc.

## Are you a new app not on the list?

If your new app is the 8th, 9th, ... addition to the dclaw stack and needs its own database on the hub:

1. **Add your ExternalName service** in your app's Helm chart so `dclaw-<app>-db-rw` resolves to `postgres.dclaw.svc.cluster.local`. (The shared chart at `dclaw-platform/helm/dclaw-app/` ships this by default — you may already have it.)
2. **Add your DB name** to the init script at `dclaw-platform/services/postgres/postgres-shared.yaml` (append `dclaw_<yourapp>` to the `DBS=(...)` array).
3. **Re-apply** the manifest: `kubectl apply -f dclaw-platform/services/postgres/postgres-shared.yaml`. The init script's `CREATE DATABASE ... WHERE NOT EXISTS` will skip existing DBs and only create your new one if you `exec` into the running pod afterwards (since init scripts only run on first PGDATA init):
   ```bash
   kubectl exec -n dclaw deploy/postgres -- \
     psql -U dclaw -d postgres -c "CREATE DATABASE dclaw_<yourapp>;"
   ```
4. **Update your app's** `DATABASE_URL` to `postgresql+asyncpg://dclaw:dclaw@dclaw-<yourapp>-db-rw:5432/dclaw_<yourapp>`.

## Are you packaging your app for an end-user install?

**Stop following this patch.** End-user installers (single-app or app-store) must ship their **own** database, because users do not have access to this hub.

- For a single-app installer: include `postgres` as a service in your app's `docker-compose.yml`, with a unique user / password the user can change.
- For app-store install via dpanel: your Helm chart should include an embedded `postgres` Deployment + PVC (or rely on a chart dependency like `bitnami/postgresql`) — never assume a shared `dclaw/postgres` exists on the user's machine.

---

## Verify

```bash
# postgres pod is up
kubectl get pod -n dclaw -l app=postgres

# all 7 DBs exist
kubectl exec -n dclaw deploy/postgres -- psql -U dclaw -l | grep dclaw_

# your app can connect (replace dclaw-agent-backend with your deploy name)
kubectl rollout restart deploy/dclaw-agent-backend -n dclaw
kubectl get pod -n dclaw -l app=dclaw-agent-backend
```

## Reverse

```bash
kubectl delete -f ~/DClaw-Stack/dclaw-platform/services/postgres/postgres-shared.yaml
# Data on the PVC is destroyed (Reclaim=Delete on local-path SC).
# To preserve data first, run pg_dump from inside the pod and copy out.
```

---

## Why this is a patch, not a scaffold edit

Per the org rule, `AGENTS.md` and `PLAN-v1.2.md` are immutable in place. New infra guidance ships as a dated patch file like this one. When this convention proves stable (no further churn, all 7 apps actually using it), it gets folded into `PLAN-v1.3.md` and this file retires.

**Related:** `dclaw-platform/services/postgres/postgres-shared.yaml` (the manifest this patch documents).
