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

# Openclaw runtime files are owned by the container's 'node' user (UID 1000),
# which prevents git operations by 'ubuntu' (UID 1001). Fix ownership before pull.
if [ -d automation/openclaw ]; then
  sudo chown -R "$(id -u):$(id -g)" automation/openclaw 2>/dev/null || true
fi

# Stash any runtime changes so git checkout/pull doesn't fail on conflicts.
if ! git diff --quiet || ! git diff --cached --quiet; then
  printf "Stashing local runtime changes...\n"
  git stash push -m "gitops-deploy-dev auto-stash $(date +%F-%H%M%S)"
fi

# Switch to dev branch and pull latest
if git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
  git checkout "${BRANCH}"
else
  git checkout -b "${BRANCH}" "origin/${BRANCH}"
fi

git pull origin "${BRANCH}"

# Re-apply stashed runtime changes (if any), preferring incoming git changes on conflict
if git stash list | head -1 | grep -q "gitops-deploy-dev auto-stash"; then
  printf "Re-applying stashed runtime changes...\n"
  git stash pop || {
    printf "Warning: stash pop had conflicts, dropping stash (git changes take precedence).\n"
    git checkout -- .
    git stash drop || true
  }
fi

# Deploy the dev stack (isolated volumes, port 5679, Tailscale-only access)
cd automation

docker compose \
  -f docker-compose.yml \
  -f docker-compose.chromium-native.yml \
  -f docker-compose.chromium-ip.yml \
  -f docker-compose.dev.yml \
  --project-name automation-dev \
  up -d --build --scale caddy=0

# Fix Openclaw volume ownership (container runs as 'node' = UID 1000).
printf "Fixing Openclaw directory ownership (UID 1000:1000)...\n"
sudo chown -R 1000:1000 "${REPO_DIR}/automation/openclaw" 2>/dev/null && \
  printf "Openclaw .openclaw ownership fixed.\n" || \
  printf "Warning: could not fix Openclaw ownership.\n"

printf "Deployed branch '%s' (dev stack) to %s\n" "${BRANCH}" "${REPO_DIR}"
printf "Dev n8n accessible at http://100.82.169.113:5679 (Tailscale only)\n"
