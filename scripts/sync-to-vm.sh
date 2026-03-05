#!/usr/bin/env bash
set -euo pipefail

VM_USER="ubuntu"
VM_HOST="satoic-production"
VM_PATH="/home/${VM_USER}/automation/"
LOCAL_PATH="/Users/sgkmeyer/ai-automation-stack/automation/"
IGNORE_FILE="/Users/sgkmeyer/ai-automation-stack/.syncignore"
ASSUME_YES=false

if [[ "${1:-}" == "--yes" ]]; then
  ASSUME_YES=true
fi

confirm() {
  local prompt="${1:?}"
  local reply=""
  if ${ASSUME_YES}; then
    return 0
  fi
  read -r -p "${prompt} [y/N] " reply || true
  [[ "${reply}" == "y" || "${reply}" == "Y" ]]
}

# Optional: set KEY_PATH to a private key file, or leave empty to use ssh-agent/config
KEY_PATH="${KEY_PATH:-}"

if [ ! -d "${LOCAL_PATH}" ]; then
  printf "ERROR: Local path not found: %s\n" "${LOCAL_PATH}" >&2
  exit 1
fi

SSH_CMD="ssh"
if [ -n "${KEY_PATH}" ]; then
  if [ ! -f "${KEY_PATH}" ]; then
    printf "ERROR: KEY_PATH file not found: %s\n" "${KEY_PATH}" >&2
    exit 1
  fi
  SSH_CMD="ssh -i ${KEY_PATH}"
fi

rsync -avz --delete \
  --exclude-from "${IGNORE_FILE}" \
  --exclude '.git/' \
  -e "${SSH_CMD}" \
  --dry-run \
  "${LOCAL_PATH}" \
  "${VM_USER}@${VM_HOST}:${VM_PATH}"

if ! confirm "Proceed with rsync --delete to ${VM_USER}@${VM_HOST}:${VM_PATH}?"; then
  printf "Cancelled.\n"
  exit 0
fi

rsync -avz --delete \
  --exclude-from "${IGNORE_FILE}" \
  --exclude '.git/' \
  -e "${SSH_CMD}" \
  "${LOCAL_PATH}" \
  "${VM_USER}@${VM_HOST}:${VM_PATH}"
