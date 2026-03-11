#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/home/ubuntu/ai-automation-stack"
BRANCH="main"

cd "${REPO_DIR}"

if ! git remote get-url origin >/dev/null 2>&1; then
  printf "ERROR: No 'origin' remote configured in %s\n" "${REPO_DIR}" >&2
  exit 1
fi

git fetch origin

# Openclaw runtime files may be owned by the container's 'node' user,
# which prevents git operations by 'ubuntu'. Fix ownership before pull.
if [ -d automation/openclaw ]; then
  sudo chown -R "$(id -u):$(id -g)" automation/openclaw 2>/dev/null || true
fi

# Stash any runtime changes (e.g., Openclaw workspace files modified by TAR)
# so git pull doesn't fail on conflicts.
if ! git diff --quiet || ! git diff --cached --quiet; then
  printf "Stashing local runtime changes...\n"
  git stash push -m "gitops-deploy auto-stash $(date +%F-%H%M%S)"
fi

# Switch to desired branch and pull latest
if git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
  git checkout "${BRANCH}"
else
  git checkout -b "${BRANCH}" "origin/${BRANCH}"
fi

git pull origin "${BRANCH}"

# Re-apply stashed runtime changes (if any), preferring incoming git changes on conflict
if git stash list | head -1 | grep -q "gitops-deploy auto-stash"; then
  printf "Re-applying stashed runtime changes...\n"
  git stash pop || {
    printf "Warning: stash pop had conflicts, dropping stash (git changes take precedence).\n"
    git checkout -- .
    git stash drop || true
  }
fi

# Deploy the automation stack
cd automation

docker compose \
  -f docker-compose.yml \
  -f docker-compose.chromium-native.yml \
  -f docker-compose.chromium-ip.yml \
  up -d --build

# Keep ingress config hot without requiring restarts.
docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile || true

# Fix Openclaw volume ownership (UID can drift across image versions).
# The container runs as 'node' but volume files may be owned by a stale UID.
printf "Checking Openclaw volume ownership...\n"
docker compose exec -u root -T openclaw \
  chown -R node:node /home/node/.openclaw 2>/dev/null && \
  printf "Openclaw .openclaw ownership verified/fixed.\n" || \
  printf "Warning: could not check Openclaw ownership (container may not be ready).\n"

printf "Deployed branch '%s' to %s\n" "${BRANCH}" "${REPO_DIR}"
