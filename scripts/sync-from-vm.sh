#!/usr/bin/env bash
set -euo pipefail

VM_USER="ubuntu"
VM_HOST="satoic-production"
VM_PATH="/home/${VM_USER}/automation/"
LOCAL_PATH="/Users/sgkmeyer/ai-automation-stack/automation/"
IGNORE_FILE="/Users/sgkmeyer/ai-automation-stack/.syncignore"

# Optional: set KEY_PATH to a private key file, or leave empty to use ssh-agent/config
KEY_PATH="${KEY_PATH:-}"

if [ ! -d "${LOCAL_PATH}" ]; then
  mkdir -p "${LOCAL_PATH}"
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
  -e "${SSH_CMD}" \
  "${VM_USER}@${VM_HOST}:${VM_PATH}" \
  "${LOCAL_PATH}"
