#!/usr/bin/env bash

set -euo pipefail

LOCAL_VAULT="${OBSIDIAN_LOCAL_VAULT:-/Users/sgkmeyer/vaults/second-brain}"
LOCAL_WIKI_ROOT="${OBSIDIAN_LOCAL_WIKI_ROOT:-${LOCAL_VAULT}/wiki}"
REMOTE_HOST="${OBSIDIAN_REMOTE_HOST:-satoic-production}"
REMOTE_WIKI_PATH="${OBSIDIAN_REMOTE_WIKI_PATH:-/home/ubuntu/ai-automation-stack/automation/wiki-vault/wiki}"

dry_run="false"

usage() {
  cat <<'EOF'
Usage:
  scripts/sync-live-wiki-mirror.sh [--dry-run]

Environment:
  OBSIDIAN_LOCAL_VAULT      Defaults to /Users/sgkmeyer/vaults/second-brain
  OBSIDIAN_LOCAL_WIKI_ROOT  Defaults to <vault>/wiki
  OBSIDIAN_REMOTE_HOST      Defaults to satoic-production
  OBSIDIAN_REMOTE_WIKI_PATH Defaults to /home/ubuntu/ai-automation-stack/automation/wiki-vault/wiki
EOF
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) dry_run="true"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown arg: $1" ;;
  esac
done

[[ -d "${LOCAL_WIKI_ROOT}" ]] || die "local wiki root not found: ${LOCAL_WIKI_ROOT}"

rsync_args=(-az --mkpath --delete --itemize-changes --human-readable)
if [[ "${dry_run}" == "true" ]]; then
  rsync_args+=(--dry-run)
fi

printf 'Syncing live wiki mirror\n'
printf '  local:  %s\n' "${LOCAL_WIKI_ROOT}"
printf '  remote: %s:%s\n' "${REMOTE_HOST}" "${REMOTE_WIKI_PATH}"

rsync "${rsync_args[@]}" \
  "${LOCAL_WIKI_ROOT}/" \
  "${REMOTE_HOST}:${REMOTE_WIKI_PATH}/"

printf 'Live wiki mirror sync complete.\n'
