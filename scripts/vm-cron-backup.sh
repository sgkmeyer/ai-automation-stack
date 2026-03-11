#!/usr/bin/env bash
# vm-cron-backup.sh — Automated daily backup, runs ON the VM via cron.
#
# Creates:
#   /home/ubuntu/backups/automation-full-YYYY-MM-DD.tar.gz   (config, compose, secrets)
#   /home/ubuntu/backups/automation-db-YYYY-MM-DD.tar.gz     (Postgres volume)
#
# Retains the last KEEP_DAYS days of backups, deletes older ones.
#
# Crontab entry (daily at 03:00 UTC):
#   0 3 * * * /home/ubuntu/ai-automation-stack/scripts/vm-cron-backup.sh >> /home/ubuntu/backups/cron-backup.log 2>&1
set -euo pipefail

BACKUP_DIR="/home/ubuntu/backups"
KEEP_DAYS=7
TODAY="$(date +%F)"
TIMESTAMP="$(date '+%F %T %Z')"

CFG_ARCHIVE="${BACKUP_DIR}/automation-full-${TODAY}.tar.gz"
DB_ARCHIVE="${BACKUP_DIR}/automation-db-${TODAY}.tar.gz"

mkdir -p "${BACKUP_DIR}"

echo "--- backup start: ${TIMESTAMP} ---"

# 1. Config backup (follows symlink)
if sudo tar -hczf "${CFG_ARCHIVE}" -C /home/ubuntu automation; then
  echo "OK  config: ${CFG_ARCHIVE} ($(du -h "${CFG_ARCHIVE}" | cut -f1))"
else
  echo "FAIL config backup"
  exit 1
fi

# 2. Postgres volume backup
if docker run --rm \
  -v automation_db_storage:/data \
  -v "${BACKUP_DIR}:/backup" \
  busybox tar czf "/backup/automation-db-${TODAY}.tar.gz" /data; then
  echo "OK  db: ${DB_ARCHIVE} ($(du -h "${DB_ARCHIVE}" | cut -f1))"
else
  echo "FAIL db backup"
  exit 1
fi

# 3. Ensure Openclaw directory ownership is correct for container (node = UID 1000).
# The tar command runs as root and can cause access-time changes that trigger
# Openclaw's config reload; ensure ownership stays at 1000:1000.
sudo chown -R 1000:1000 /home/ubuntu/ai-automation-stack/automation/openclaw 2>/dev/null || true

# 4. Prune old backups
find "${BACKUP_DIR}" -name "automation-full-*.tar.gz" -mtime +${KEEP_DAYS} -delete -print | while read -r f; do
  echo "PRUNED ${f}"
done
find "${BACKUP_DIR}" -name "automation-db-*.tar.gz" -mtime +${KEEP_DAYS} -delete -print | while read -r f; do
  echo "PRUNED ${f}"
done

echo "--- backup complete: $(date '+%F %T %Z') ---"
echo ""
