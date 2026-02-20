#!/usr/bin/env bash
# verify.sh — non-interactive stack health check
# Runs VM compose ps + external endpoint checks.
# Exits non-zero if any check fails.
# Used by: humans after a deploy, CI smoke-test step.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

./scripts/vm-safe.sh --yes ps
./scripts/vm-safe.sh --yes check-external
