#!/usr/bin/env bash
# restore.sh — Restore the Satoic automation stack from DR backup archives.
#
# Run this ON the VM after bootstrap-vm.sh has been run.
# Expects two archive files (from vm-cron-backup.sh or vm-safe.sh dr-backup):
#   1. automation-full-*.tar.gz  (config, compose, secrets, Openclaw runtime)
#   2. automation-db-*.tar.gz    (Postgres volume data)
#
# Usage:
#   sudo ./scripts/restore.sh <config-archive> <db-archive>
#
# Example:
#   sudo ./scripts/restore.sh \
#     /home/ubuntu/backups/automation-full-2026-03-10.tar.gz \
#     /home/ubuntu/backups/automation-db-2026-03-10.tar.gz
set -euo pipefail

say() { printf "\n==> %s\n" "$*"; }
warn() { printf "WARNING: %s\n" "$*"; }

REPO_DIR="/home/ubuntu/ai-automation-stack"
AUTOMATION_DIR="${REPO_DIR}/automation"
DEPLOY_USER="ubuntu"

# ---------- Argument validation ----------
if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <config-archive.tar.gz> <db-archive.tar.gz>" >&2
  exit 1
fi

CFG_ARCHIVE="$1"
DB_ARCHIVE="$2"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "ERROR: Run this script as root (or with sudo)." >&2
  exit 1
fi

for f in "${CFG_ARCHIVE}" "${DB_ARCHIVE}"; do
  if [[ ! -f "${f}" ]]; then
    echo "ERROR: Archive not found: ${f}" >&2
    exit 1
  fi
done

if [[ ! -d "${REPO_DIR}" ]]; then
  echo "ERROR: Repo not found at ${REPO_DIR}. Run bootstrap-vm.sh first." >&2
  exit 1
fi

# ---------- Pre-restore safety ----------
say "Pre-restore checks..."

# Stop the stack if running
COMPOSE_DIR="${AUTOMATION_DIR}"
if [[ -d "${COMPOSE_DIR}" ]] && docker compose -f "${COMPOSE_DIR}/docker-compose.yml" ps --quiet 2>/dev/null | head -1 | grep -q .; then
  say "Stopping running stack..."
  cd "${COMPOSE_DIR}"
  docker compose \
    -f docker-compose.yml \
    -f docker-compose.chromium-native.yml \
    -f docker-compose.chromium-ip.yml \
    down || true
fi

# ---------- 1. Restore config ----------
say "Restoring config from ${CFG_ARCHIVE}..."

# The archive contains an 'automation/' directory at its root.
# Extract to a temp location, then overlay onto the repo's automation/ dir.
RESTORE_TMP="$(mktemp -d)"
tar -xzf "${CFG_ARCHIVE}" -C "${RESTORE_TMP}"

# The archive is created with `tar -hczf ... -C /home/ubuntu automation`,
# so the top-level dir inside is 'automation/'.
if [[ -d "${RESTORE_TMP}/automation" ]]; then
  EXTRACTED="${RESTORE_TMP}/automation"
else
  # Fallback: archive might have different structure
  EXTRACTED="${RESTORE_TMP}"
fi

# Restore secrets and runtime config that are gitignored
# (these are the files that can't be recovered from git)
RESTORE_FILES=(
  ".env"
  "openclaw/config.json"
  "openclaw/credentials"
  "openclaw/devices"
  "openclaw/identity"
  "openclaw/telegram"
  "openclaw/secrets"
)

restored=0
for item in "${RESTORE_FILES[@]}"; do
  src="${EXTRACTED}/${item}"
  dst="${AUTOMATION_DIR}/${item}"
  if [[ -e "${src}" ]]; then
    # Create parent directory if needed
    mkdir -p "$(dirname "${dst}")"
    if [[ -d "${src}" ]]; then
      cp -a "${src}" "${dst}"
    else
      cp -a "${src}" "${dst}"
    fi
    echo "  Restored: ${item}"
    restored=$((restored + 1))
  fi
done

echo "Restored ${restored} items from config archive."

# Fix ownership — general files owned by deploy user, but Openclaw dir
# must be owned by UID 1000 (container's 'node' user).
chown -R "${DEPLOY_USER}:${DEPLOY_USER}" "${AUTOMATION_DIR}"
chown -R 1000:1000 "${AUTOMATION_DIR}/openclaw" 2>/dev/null || true
chmod 600 "${AUTOMATION_DIR}/.env" 2>/dev/null || true

rm -rf "${RESTORE_TMP}"

# ---------- 2. Restore Postgres volume ----------
say "Restoring Postgres data from ${DB_ARCHIVE}..."

# Ensure the volume exists
docker volume create automation_db_storage 2>/dev/null || true

# The DB archive contains /data/* (Postgres data directory).
# Restore it into the automation_db_storage volume.
docker run --rm \
  -v automation_db_storage:/data \
  -v "$(dirname "${DB_ARCHIVE}"):/backup:ro" \
  busybox sh -c "
    rm -rf /data/*
    tar -xzf /backup/$(basename "${DB_ARCHIVE}") -C /
  "

echo "Postgres volume restored."

# ---------- 3. Verify ----------
say "Restore complete. Verifying..."

echo "Config files:"
for item in "${RESTORE_FILES[@]}"; do
  dst="${AUTOMATION_DIR}/${item}"
  if [[ -e "${dst}" ]]; then
    echo "  OK  ${item}"
  else
    warn "MISSING  ${item}"
  fi
done

echo ""
echo "Docker volumes:"
docker volume ls --filter name=automation_db_storage --format "  {{.Name}}: {{.Driver}}"

# ---------- Done ----------
say "Restore complete!"
echo ""
echo "Next steps:"
echo "  1. Review .env:            cat ${AUTOMATION_DIR}/.env"
echo "  2. Review Openclaw config: cat ${AUTOMATION_DIR}/openclaw/config.json"
echo "  3. Deploy the stack:       sudo -u ${DEPLOY_USER} ${REPO_DIR}/scripts/gitops-deploy.sh"
echo "  4. Verify endpoints:"
echo "       curl -I https://n8n.satoic.com"
echo "       curl -I https://openclaw.satoic.com"
echo "       curl -I https://portainer.satoic.com"
echo ""
echo "Note: n8n credentials (Gmail, Google Drive, HubSpot) are encrypted in the DB."
echo "They will work as long as N8N_ENCRYPTION_KEY in .env matches the original."
echo "If the key was lost, credentials must be re-created manually in n8n."
