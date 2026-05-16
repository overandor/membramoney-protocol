#!/bin/bash
# Membra Money Protocol — Database Backup Script
# Usage: ./scripts/backup_db.sh [s3_bucket]

set -euo pipefail

BUCKET="${1:-membramoney-backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="membramoney_${TIMESTAMP}.sql.gz"

echo "Starting database backup: ${BACKUP_FILE}"

# Dump and compress
pg_dump -h localhost -U membra -d membramoney | gzip > "/tmp/${BACKUP_FILE}"

# Upload to S3
aws s3 cp "/tmp/${BACKUP_FILE}" "s3://${BUCKET}/backups/${BACKUP_FILE}"

# Cleanup local
rm -f "/tmp/${BACKUP_FILE}"

echo "Backup complete: s3://${BUCKET}/backups/${BACKUP_FILE}"
