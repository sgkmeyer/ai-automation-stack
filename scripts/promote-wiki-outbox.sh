#!/usr/bin/env bash

set -euo pipefail

LOCAL_VAULT="${OBSIDIAN_LOCAL_VAULT:-/Users/sgkmeyer/vaults/second-brain}"
LOCAL_REVIEW_QUEUE="${OBSIDIAN_WIKI_REVIEW_QUEUE:-${LOCAL_VAULT}/_review/wiki-proposals}"

proposal_id=""
force="false"

usage() {
  cat <<'EOF'
Usage:
  scripts/promote-wiki-outbox.sh --proposal-id UUID [--force]

Environment:
  OBSIDIAN_LOCAL_VAULT       Defaults to /Users/sgkmeyer/vaults/second-brain
  OBSIDIAN_WIKI_REVIEW_QUEUE Defaults to <vault>/_review/wiki-proposals
EOF
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --proposal-id) proposal_id="${2-}"; shift 2 ;;
    --force) force="true"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown arg: $1" ;;
  esac
done

[[ -n "${proposal_id}" ]] || die "--proposal-id is required"
[[ -d "${LOCAL_VAULT}" ]] || die "local vault not found: ${LOCAL_VAULT}"
[[ -d "${LOCAL_REVIEW_QUEUE}" ]] || die "local review queue not found: ${LOCAL_REVIEW_QUEUE}"

metadata_path="${LOCAL_REVIEW_QUEUE}/metadata/${proposal_id}.json"
[[ -f "${metadata_path}" ]] || die "proposal metadata not found: ${metadata_path}"

proposal_info="$(
PROPOSAL_METADATA_PATH="${metadata_path}" python3 - <<'PY'
import json
import os
from pathlib import Path

path = Path(os.environ["PROPOSAL_METADATA_PATH"])
payload = json.loads(path.read_text())
print(payload["page_ref"])
print(payload["title"])
print(payload.get("reviewed_at") or payload.get("updated_at") or "")
print(payload.get("review_actor", {}).get("actor_id") or "")
PY
)"

page_ref="$(printf '%s\n' "${proposal_info}" | sed -n '1p')"
title="$(printf '%s\n' "${proposal_info}" | sed -n '2p')"
reviewed_at="$(printf '%s\n' "${proposal_info}" | sed -n '3p')"
review_actor="$(printf '%s\n' "${proposal_info}" | sed -n '4p')"

source_page_path="${LOCAL_REVIEW_QUEUE}/pages/${page_ref}"
target_page_path="${LOCAL_VAULT}/${page_ref}"

[[ -f "${source_page_path}" ]] || die "proposal page not found: ${source_page_path}"

if [[ -f "${target_page_path}" && "${force}" != "true" ]]; then
  die "canonical page already exists: ${target_page_path} (use --force to overwrite)"
fi

mkdir -p "$(dirname "${target_page_path}")"
cp "${source_page_path}" "${target_page_path}"

log_path="${LOCAL_VAULT}/wiki/log.md"
mkdir -p "$(dirname "${log_path}")"
if [[ ! -f "${log_path}" ]]; then
  cat > "${log_path}" <<'EOF'
# Wiki Log

Append-only record of notable wiki maintenance events.
EOF
fi

printf '\n- %s promoted `%s` from approved proposal `%s` into `%s`' \
  "${reviewed_at:-unknown-time}" \
  "${title}" \
  "${proposal_id}" \
  "${page_ref}" >>"${log_path}"

if [[ -n "${review_actor}" ]]; then
  printf ' (review actor: `%s`)' "${review_actor}" >>"${log_path}"
fi
printf '\n' >>"${log_path}"

printf 'Promoted approved proposal\n'
printf '  proposal: %s\n' "${proposal_id}"
printf '  source:   %s\n' "${source_page_path}"
printf '  target:   %s\n' "${target_page_path}"
