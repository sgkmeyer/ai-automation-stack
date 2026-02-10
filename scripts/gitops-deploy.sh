#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/home/ubuntu/ai-automation-stack"
BRANCH="main"

cd "${REPO_DIR}"

git fetch origin
# Switch to desired branch and pull latest
if git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
  git checkout "${BRANCH}"
else
  git checkout -b "${BRANCH}" "origin/${BRANCH}"
fi

git pull origin "${BRANCH}"

# Deploy the automation stack
cd automation

docker compose up -d

printf "Deployed branch '%s' to %s\n" "${BRANCH}" "${REPO_DIR}"
