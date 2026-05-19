#!/usr/bin/env bash
# verify.sh — non-interactive post-deploy health check
# Runs deploy-blocking health checks only. Freshness/activity audits live in
# separate scripts so stale-but-healthy integrations do not fail routine deploys.
# Used by: humans after a deploy, CI smoke-test step.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

./scripts/vm-safe.sh --yes ps
./scripts/vm-safe.sh --yes check-external
./scripts/verify-memory-webhook.sh

if ! ./scripts/verify-krisp-ingest.sh; then
  printf "%s\n" "WARN verify-krisp-ingest failed; treating as non-blocking freshness/activity signal." >&2
fi
