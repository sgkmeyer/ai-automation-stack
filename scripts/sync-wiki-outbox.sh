#!/usr/bin/env bash

set -euo pipefail

LOCAL_VAULT="${OBSIDIAN_LOCAL_VAULT:-/Users/sgkmeyer/vaults/second-brain}"
REMOTE_HOST="${OBSIDIAN_REMOTE_HOST:-satoic-production}"
REMOTE_OUTBOX="${OBSIDIAN_WIKI_OUTBOX_REMOTE_PATH:-/home/ubuntu/ai-automation-stack/automation/wiki-proposals/outbox}"
LOCAL_REVIEW_QUEUE="${OBSIDIAN_WIKI_REVIEW_QUEUE:-${LOCAL_VAULT}/_review/wiki-proposals}"

dry_run="false"

usage() {
  cat <<'EOF'
Usage:
  scripts/sync-wiki-outbox.sh [--dry-run]

Environment:
  OBSIDIAN_LOCAL_VAULT           Defaults to /Users/sgkmeyer/vaults/second-brain
  OBSIDIAN_REMOTE_HOST           Defaults to satoic-production
  OBSIDIAN_WIKI_OUTBOX_REMOTE_PATH
                                 Defaults to /home/ubuntu/ai-automation-stack/automation/wiki-proposals/outbox
  OBSIDIAN_WIKI_REVIEW_QUEUE     Defaults to <vault>/_review/wiki-proposals
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) dry_run="true"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) printf 'error: unknown arg: %s\n' "$1" >&2; exit 1 ;;
  esac
done

mkdir -p "${LOCAL_REVIEW_QUEUE}"

rsync_args=(-az --mkpath --itemize-changes --human-readable)
if [[ "${dry_run}" == "true" ]]; then
  rsync_args+=(--dry-run)
fi

printf 'Syncing wiki proposal outbox\n'
printf '  remote: %s:%s\n' "${REMOTE_HOST}" "${REMOTE_OUTBOX}"
printf '  local:  %s\n' "${LOCAL_REVIEW_QUEUE}"

rsync "${rsync_args[@]}" \
  "${REMOTE_HOST}:${REMOTE_OUTBOX}/" \
  "${LOCAL_REVIEW_QUEUE}/"

printf 'Wiki proposal sync complete.\n'
