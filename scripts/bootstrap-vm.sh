#!/usr/bin/env bash
# bootstrap-vm.sh — Set up a fresh VPS for the Satoic automation stack.
#
# Run this ON the new VM as root (or with sudo).
# Assumes a clean Ubuntu 22.04+ (aarch64 or amd64).
#
# What it does:
#   1. Installs Docker + Docker Compose plugin
#   2. Installs Tailscale
#   3. Clones the repo
#   4. Creates the automation symlink
#   5. Prompts for secrets (.env, openclaw/config.json)
#   6. Installs the automated backup timer
#
# Usage:
#   curl -sL <raw-github-url>/scripts/bootstrap-vm.sh | sudo bash
#   — or —
#   scp scripts/bootstrap-vm.sh user@new-vm:/tmp/ && ssh user@new-vm 'sudo bash /tmp/bootstrap-vm.sh'
set -euo pipefail

REPO_URL="git@github.com:sgkmeyer/ai-automation-stack.git"
REPO_DIR="/home/ubuntu/ai-automation-stack"
AUTOMATION_DIR="/home/ubuntu/automation"
BACKUP_DIR="/home/ubuntu/backups"
DEPLOY_USER="ubuntu"

say() { printf "\n==> %s\n" "$*"; }
warn() { printf "WARNING: %s\n" "$*"; }

# ---------- Pre-flight ----------
say "Checking prerequisites..."
if [[ "$(id -u)" -ne 0 ]]; then
  echo "ERROR: Run this script as root (or with sudo)." >&2
  exit 1
fi

if ! id "${DEPLOY_USER}" &>/dev/null; then
  echo "ERROR: User '${DEPLOY_USER}' does not exist. Create it first." >&2
  exit 1
fi

# ---------- 1. Docker ----------
say "Installing Docker..."
if command -v docker &>/dev/null; then
  echo "Docker already installed: $(docker --version)"
else
  apt-get update -qq
  apt-get install -y -qq ca-certificates curl gnupg
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list
  apt-get update -qq
  apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  usermod -aG docker "${DEPLOY_USER}"
  systemctl enable --now docker
  echo "Docker installed: $(docker --version)"
fi

# ---------- 2. Tailscale ----------
say "Installing Tailscale..."
if command -v tailscale &>/dev/null; then
  echo "Tailscale already installed: $(tailscale version | head -1)"
else
  curl -fsSL https://tailscale.com/install.sh | sh
  echo "Tailscale installed. Run 'sudo tailscale up' to authenticate."
fi

# ---------- 3. Clone repo ----------
say "Setting up repository..."
if [[ -d "${REPO_DIR}" ]]; then
  echo "Repo already exists at ${REPO_DIR}"
else
  # Ensure SSH key is available for GitHub
  if [[ ! -f "/home/${DEPLOY_USER}/.ssh/id_ed25519" ]] && [[ ! -f "/home/${DEPLOY_USER}/.ssh/id_rsa" ]]; then
    warn "No SSH key found for ${DEPLOY_USER}. You may need to set up a deploy key for GitHub."
    warn "Generate one with: sudo -u ${DEPLOY_USER} ssh-keygen -t ed25519 -C 'vm-deploy-key'"
  fi
  sudo -u "${DEPLOY_USER}" git clone "${REPO_URL}" "${REPO_DIR}"
  echo "Cloned to ${REPO_DIR}"
fi

# ---------- 4. Automation symlink ----------
say "Creating automation symlink..."
if [[ -L "${AUTOMATION_DIR}" ]]; then
  echo "Symlink already exists: $(ls -la "${AUTOMATION_DIR}")"
elif [[ -d "${AUTOMATION_DIR}" ]]; then
  warn "${AUTOMATION_DIR} exists as a directory (not a symlink)."
  warn "If migrating, move it aside: mv ${AUTOMATION_DIR} ${AUTOMATION_DIR}.old"
else
  ln -s "${REPO_DIR}/automation" "${AUTOMATION_DIR}"
  chown -h "${DEPLOY_USER}:${DEPLOY_USER}" "${AUTOMATION_DIR}"
  echo "Created: ${AUTOMATION_DIR} -> ${REPO_DIR}/automation"
fi

# ---------- 5. Secrets ----------
say "Checking secrets..."
ENV_FILE="${REPO_DIR}/automation/.env"
OPENCLAW_CONFIG="${REPO_DIR}/automation/openclaw/config.json"

if [[ -f "${ENV_FILE}" ]]; then
  echo ".env exists ($(wc -l < "${ENV_FILE}") lines)"
else
  if [[ -f "${REPO_DIR}/automation/.env.example" ]]; then
    cp "${REPO_DIR}/automation/.env.example" "${ENV_FILE}"
    chmod 600 "${ENV_FILE}"
    chown "${DEPLOY_USER}:${DEPLOY_USER}" "${ENV_FILE}"
    warn ".env created from template. EDIT IT NOW with real values:"
    warn "  sudo -u ${DEPLOY_USER} nano ${ENV_FILE}"
  else
    warn "No .env found and no .env.example available."
    warn "Create ${ENV_FILE} manually before deploying."
  fi
fi

if [[ -f "${OPENCLAW_CONFIG}" ]]; then
  echo "openclaw/config.json exists"
else
  warn "openclaw/config.json not found."
  warn "Restore it from a DR backup or run 'openclaw onboard' after first deploy."
fi

# ---------- 6. Backup directory + systemd timer ----------
say "Setting up automated backups..."
mkdir -p "${BACKUP_DIR}"
chown "${DEPLOY_USER}:${DEPLOY_USER}" "${BACKUP_DIR}"

SYSTEMD_SRC="${REPO_DIR}/scripts/systemd"
if [[ -f "${SYSTEMD_SRC}/satoic-backup.service" ]]; then
  cp "${SYSTEMD_SRC}/satoic-backup.service" /etc/systemd/system/
  cp "${SYSTEMD_SRC}/satoic-backup.timer" /etc/systemd/system/
  systemctl daemon-reload
  systemctl enable --now satoic-backup.timer
  echo "Backup timer installed (daily at 03:00 UTC)"
else
  warn "systemd unit files not found in repo. Backups not configured."
fi

# ---------- 7. SSH hardening (GitHub Actions CI) ----------
say "Notes for CI setup..."
echo "If using GitHub Actions for GitOps deploys:"
echo "  1. Add the CI public key to /home/${DEPLOY_USER}/.ssh/authorized_keys"
echo "  2. Set GitHub secret VM_SSH_KNOWN_HOSTS with this VM's host key:"
echo "     ssh-keyscan -t ed25519 <this-vm-tailscale-ip>"
echo "  3. Set GitHub secret VM_TAILSCALE_HOST to this VM's Tailscale IP"

# ---------- Done ----------
say "Bootstrap complete!"
echo ""
echo "Next steps:"
echo "  1. Authenticate Tailscale:  sudo tailscale up"
echo "  2. Edit secrets:            sudo -u ${DEPLOY_USER} nano ${ENV_FILE}"
echo "  3. Restore Openclaw config: (from DR backup or run openclaw onboard)"
echo "  4. Deploy the stack:        sudo -u ${DEPLOY_USER} ${REPO_DIR}/scripts/gitops-deploy.sh"
echo "  5. Verify:                  curl -I https://n8n.satoic.com"
echo ""
echo "If restoring from a DR backup, run restore.sh BEFORE step 4:"
echo "  ${REPO_DIR}/scripts/restore.sh <config-archive> <db-archive>"
