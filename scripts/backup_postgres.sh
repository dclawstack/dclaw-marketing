#!/usr/bin/env bash
# Daily Postgres logical backup — §6.13.
#
# Usage:
#   ./scripts/backup_postgres.sh [retention_days]
#
# Defaults: retention 30 days. Writes to ./backups/postgres/.
# Restore via:
#   psql -h $PGHOST -U $PGUSER -d dclaw_marketing < backup-YYYYMMDD.sql

set -euo pipefail
RETENTION="${1:-30}"
DEST="${BACKUP_DIR:-./backups/postgres}"
mkdir -p "$DEST"
TS="$(date -u +%Y%m%d-%H%M%S)"
FILE="$DEST/dclaw-$TS.sql"
docker compose exec -T postgres pg_dump -U postgres dclaw_marketing > "$FILE"
gzip -9 "$FILE"
find "$DEST" -name 'dclaw-*.sql.gz' -mtime "+$RETENTION" -delete
echo "Backup: ${FILE}.gz"
