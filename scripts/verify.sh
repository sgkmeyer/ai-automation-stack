#!/usr/bin/env bash
# verify.sh — non-interactive post-deploy smoke check
# Runs VM compose ps, public endpoint checks, and a safe end-to-end memory webhook smoke test.
# Exits non-zero if any check fails.
# Used by: humans after a deploy, CI smoke-test step.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

./scripts/vm-safe.sh --yes ps
./scripts/vm-safe.sh --yes check-external
./scripts/verify-memory-webhook.sh
