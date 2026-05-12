#!/usr/bin/env bash
# Daily MinIO bucket sync to an off-site mirror — §6.13.
#
# Usage:
#   MINIO_HOST=https://primary MINIO_KEY=... MINIO_SECRET=... \
#   OFFSITE_BUCKET=s3://offsite-mirror \
#       ./scripts/backup_minio.sh

set -euo pipefail
: "${MINIO_HOST:?need MINIO_HOST}"
: "${MINIO_KEY:?need MINIO_KEY}"
: "${MINIO_SECRET:?need MINIO_SECRET}"
: "${OFFSITE_BUCKET:?need OFFSITE_BUCKET}"
BUCKET="${BUCKET:-dclaw-marketing}"

# `mc mirror` does an incremental sync — only changed objects move.
# Install mc: brew install minio-mc / https://min.io/docs/minio/linux/reference/minio-mc.html
mc alias set primary "$MINIO_HOST" "$MINIO_KEY" "$MINIO_SECRET"
mc mirror --overwrite --remove "primary/$BUCKET" "$OFFSITE_BUCKET"
echo "Mirrored primary/$BUCKET → $OFFSITE_BUCKET"
