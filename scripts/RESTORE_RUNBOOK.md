# Restore runbook — DClaw Marketing

Pre-launch convenience doc. Pairs with `backup_postgres.sh` + `backup_minio.sh`.

## 1. What's backed up

| Layer       | Tool                          | Output                                  | Cadence                    |
|-------------|-------------------------------|-----------------------------------------|----------------------------|
| Postgres    | `pg_dump` (compressed)        | `backups/postgres/dclaw-<ts>.sql.gz`    | Daily (cron), 30-day keep  |
| MinIO       | `mc mirror --overwrite`       | An offsite bucket                       | Daily (cron), continuous   |
| Code        | Git remote (GitHub)           | The dclaw-marketing repo                | Every push                 |
| Encrypted   | Fernet-encrypted              | `tenant_encryption_master_key` env var  | Outside-the-system secret  |
| credentials |                               |                                         |                            |

The Fernet master key is the **only** out-of-band item the operator
must safeguard separately. Lose it → every encrypted Connection /
OAuth-token blob becomes unrecoverable. Store it in 1Password / Vault
/ AWS Secrets Manager, never in the same place as the DB backup.

## 2. Restore Postgres from a backup

```
# 1. Bring the stack up but with backend OFF (so init_db doesn't race).
docker compose up -d postgres redis minio

# 2. Drop + recreate the DB.
docker compose exec -T postgres psql -U postgres -c "DROP DATABASE IF EXISTS dclaw_marketing"
docker compose exec -T postgres psql -U postgres -c "CREATE DATABASE dclaw_marketing"

# 3. Restore.
gunzip -c backups/postgres/dclaw-YYYYMMDD-HHMMSS.sql.gz \
  | docker compose exec -T postgres psql -U postgres -d dclaw_marketing

# 4. Bring the backend up.
docker compose up -d backend
```

## 3. Restore MinIO from offsite mirror

```
mc alias set primary  "$MINIO_HOST"   "$KEY" "$SECRET"
mc alias set offsite  "$OFFSITE_HOST" "$KEY" "$SECRET"
mc mirror --overwrite "offsite/dclaw-marketing" "primary/dclaw-marketing"
```

## 4. Verify

After restore:

- Log in with `admin@dclaw.io` (the bootstrap admin re-asserts the
  password from `bootstrap_admin_temp_password` on first start).
- Hit `GET /health/dependencies` — every check should return
  `{"ok": true}`.
- Pick one Lead in the UI; verify activity timeline + GDPR-export
  audit trail roundtrip.

## 5. What an off-prem cold-start looks like

A new-server build that needs to come up from cold:

1. Provision Postgres + Redis + MinIO + the backend + frontend
   containers via the existing `docker-compose.yml`.
2. Restore Postgres (§2).
3. Restore MinIO (§3).
4. Set `tenant_encryption_master_key` to the safeguarded original.
5. Smoke-test §4.

Time budget: typical small-org backup (≤ 1 GB Postgres, ≤ 5 GB MinIO)
is ~10 minutes end-to-end.
