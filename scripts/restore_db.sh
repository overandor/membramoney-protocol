#!/bin/bash
# Membra Money Protocol — Database Restore Script
# Usage: ./scripts/restore_db.sh s3://bucket/backups/file.sql.gz

set -euo pipefail

S3_PATH="${1}"
if [ -z "$S3_PATH" ]; then
    echo "Usage: $0 s3://bucket/backups/file.sql.gz"
    exit 1
fi

TMP_FILE="/tmp/restore_$(date +%s).sql.gz"

echo "Downloading backup from ${S3_PATH}..."
aws s3 cp "${S3_PATH}" "${TMP_FILE}"

echo "Restoring database..."
gunzip -c "${TMP_FILE}" | psql -h localhost -U membra -d membramoney

rm -f "${TMP_FILE}"
echo "Restore complete."
