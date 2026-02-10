#!/usr/bin/env bash
set -euo pipefail

SRC_DIR="/Users/sgkmeyer/ai-automation-stack/automation"
DEST_DIR="/Users/sgkmeyer/ai-automation-stack/automation_redacted"

rm -rf "${DEST_DIR}"
mkdir -p "${DEST_DIR}"

# Copy everything except secret/runtime paths
rsync -av \
  --exclude '.env' \
  --exclude 'volumes/' \
  --exclude 'caddy_data/' \
  --exclude 'caddy_config/' \
  "${SRC_DIR}/" "${DEST_DIR}/"

# Add a placeholder env template if available
if [ -f "/Users/sgkmeyer/ai-automation-stack/automation/.env.example" ]; then
  cp "/Users/sgkmeyer/ai-automation-stack/automation/.env.example" "${DEST_DIR}/.env.example"
fi

# Add README for redacted bundle
cat <<'TXT' > "${DEST_DIR}/REDACTED_README.txt"
This folder is a redacted copy of the automation stack.
Excluded:
- .env (secrets)
- volumes/ (runtime data)
- caddy_data/ (TLS certs)
- caddy_config/ (Caddy state)

Use this for sharing or review without leaking secrets.
TXT

printf "Redacted copy created at: %s\n" "${DEST_DIR}"
