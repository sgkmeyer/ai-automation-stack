#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/home/ubuntu/ai-automation-stack"
BRANCH="dev"

cd "${REPO_DIR}"

if ! git remote get-url origin >/dev/null 2>&1; then
  printf "ERROR: No 'origin' remote configured in %s\n" "${REPO_DIR}" >&2
  exit 1
fi

git fetch origin

# Switch to dev branch and pull latest
if git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
  git checkout "${BRANCH}"
else
  git checkout -b "${BRANCH}" "origin/${BRANCH}"
fi

git pull origin "${BRANCH}"

# Deploy the dev stack (isolated volumes, port 5679, Tailscale-only access)
cd automation

docker compose \
  -f docker-compose.yml \
  -f docker-compose.chromium-native.yml \
  -f docker-compose.chromium-ip.yml \
  -f docker-compose.dev.yml \
  --project-name automation-dev \
  up -d

printf "Deployed branch '%s' (dev stack) to %s\n" "${BRANCH}" "${REPO_DIR}"
printf "Dev n8n accessible at http://100.82.169.113:5679 (Tailscale only)\n"
