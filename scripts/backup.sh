#!/usr/bin/env bash
# backup.sh — take a full DR backup (VM config + DB + local copy + manifest)
# Wraps vm-safe.sh dr-backup with a clean one-word interface.
# Run this before any significant change to the stack.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

./scripts/vm-safe.sh dr-backup
