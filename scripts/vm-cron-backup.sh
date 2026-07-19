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
TMP_CFG_ARCHIVE="${CFG_ARCHIVE}.tmp"
TMP_DB_ARCHIVE="${DB_ARCHIVE}.tmp"

mkdir -p "${BACKUP_DIR}"

echo "--- backup start: ${TIMESTAMP} ---"

# 1. Config backup (follows symlink).
# Exclude volatile OpenClaw runtime caches so changing temp/plugin files do not
# fail the backup while the live agent is active.
rm -f "${TMP_CFG_ARCHIVE}"
if sudo tar --warning=no-file-changed --ignore-failed-read -hczf "${TMP_CFG_ARCHIVE}" \
  --exclude='automation/openclaw/agents/*/agent/codex-home/tmp' \
  --exclude='automation/openclaw/plugin-runtime-deps' \
  --exclude='automation/openclaw/plugin-skills' \
  --exclude='automation/openclaw/npm/node_modules' \
  --exclude='automation/openclaw/npm/projects/*/node_modules' \
  --exclude='automation/openclaw/logs' \
  --exclude='automation/openclaw/tasks' \
  --exclude='automation/openclaw/delivery-queue' \
  -C /home/ubuntu automation; then
  mv "${TMP_CFG_ARCHIVE}" "${CFG_ARCHIVE}"
  sudo tar -tzf "${CFG_ARCHIVE}" >/dev/null
  echo "OK  config: ${CFG_ARCHIVE} ($(du -h "${CFG_ARCHIVE}" | cut -f1))"
else
  rm -f "${TMP_CFG_ARCHIVE}"
  echo "FAIL config backup"
  exit 1
fi

# 2. Postgres volume backup
rm -f "${TMP_DB_ARCHIVE}"
if docker run --rm \
  -v automation_db_storage:/data \
  -v "${BACKUP_DIR}:/backup" \
  busybox tar czf "/backup/$(basename "${TMP_DB_ARCHIVE}")" /data; then
  mv "${TMP_DB_ARCHIVE}" "${DB_ARCHIVE}"
  tar -tzf "${DB_ARCHIVE}" >/dev/null
  echo "OK  db: ${DB_ARCHIVE} ($(du -h "${DB_ARCHIVE}" | cut -f1))"
else
  rm -f "${TMP_DB_ARCHIVE}"
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
find "${BACKUP_DIR}" -name "automation-*.tar.gz.tmp" -delete -print | while read -r f; do
  echo "PRUNED ${f}"
done
find "${BACKUP_DIR}" -name "automation-*.tar.gz" -size 0 -delete -print | while read -r f; do
  echo "PRUNED empty ${f}"
done

echo "--- backup complete: $(date '+%F %T %Z') ---"
echo ""
