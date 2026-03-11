#!/usr/bin/env bash

set -euo pipefail

LOCAL_VAULT="${OBSIDIAN_LOCAL_VAULT:-/Users/sgkmeyer/vaults/second-brain}"
REMOTE_HOST="${OBSIDIAN_REMOTE_HOST:-satoic-production}"
REMOTE_PATH="${OBSIDIAN_REMOTE_PATH:-/home/ubuntu/obsidian-vault}"

dry_run="false"
delete_mode="true"
extra_excludes=()

usage() {
  cat <<'EOF'
Usage:
  scripts/sync-obsidian-vault.sh [options]

Options:
  --vault PATH           Local vault path
  --remote-host HOST     SSH host alias or hostname
  --remote-path PATH     Remote mirror path on the VM
  --exclude RELPATH      Additional relative path to exclude (repeatable)
  --dry-run              Show what would change without copying files
  --no-delete            Do not delete files on the VM that were removed locally
  -h, --help             Show this help

Environment:
  OBSIDIAN_LOCAL_VAULT   Defaults to /Users/sgkmeyer/vaults/second-brain
  OBSIDIAN_REMOTE_HOST   Defaults to satoic-production
  OBSIDIAN_REMOTE_PATH   Defaults to /home/ubuntu/obsidian-vault

Examples:
  scripts/sync-obsidian-vault.sh --dry-run
  scripts/sync-obsidian-vault.sh
  scripts/sync-obsidian-vault.sh --exclude Attachments/ --exclude Templates/
EOF
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --vault) LOCAL_VAULT="${2-}"; shift 2 ;;
    --remote-host) REMOTE_HOST="${2-}"; shift 2 ;;
    --remote-path) REMOTE_PATH="${2-}"; shift 2 ;;
    --exclude) extra_excludes+=("${2-}"); shift 2 ;;
    --dry-run) dry_run="true"; shift ;;
    --no-delete) delete_mode="false"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

[[ -d "${LOCAL_VAULT}" ]] || die "local vault not found: ${LOCAL_VAULT}"

rsync_args=(
  -az
  --mkpath
  --itemize-changes
  --human-readable
  --exclude=.obsidian/
  --exclude=.git/
  --exclude=.DS_Store
  --exclude=.Trash/
  --exclude=.trash/
)

if [[ "${delete_mode}" == "true" ]]; then
  rsync_args+=(--delete)
fi

if [[ "${dry_run}" == "true" ]]; then
  rsync_args+=(--dry-run)
fi

if [[ ${#extra_excludes[@]} -gt 0 ]]; then
  for exclude_path in "${extra_excludes[@]}"; do
    rsync_args+=("--exclude=${exclude_path}")
  done
fi

printf 'Syncing vault\n'
printf '  local:  %s\n' "${LOCAL_VAULT}"
printf '  remote: %s:%s\n' "${REMOTE_HOST}" "${REMOTE_PATH}"
if [[ "${dry_run}" == "true" ]]; then
  printf '  mode:   dry-run\n'
fi

rsync "${rsync_args[@]}" \
  "${LOCAL_VAULT}/" \
  "${REMOTE_HOST}:${REMOTE_PATH}/"

printf 'Mirror sync complete.\n'
printf 'Next step: ssh %s '\''find %s -maxdepth 2 -type f | sort | sed -n "1,50p"'\''\n' \
  "${REMOTE_HOST}" \
  "${REMOTE_PATH}"
