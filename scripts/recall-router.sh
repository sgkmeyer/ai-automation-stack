#!/usr/bin/env bash
# Thin CLI over the internal unified recall router.

set -euo pipefail

BASE_URL="${MEMORY_API_BASE_URL:-http://memory-api:8100}"
TOKEN="${MEMORY_API_TOKEN:-}"

usage() {
  cat <<'EOF'
Usage:
  scripts/recall-router.sh --query TEXT [--limit N]

Environment:
  MEMORY_API_BASE_URL  Defaults to http://memory-api:8100
  MEMORY_API_TOKEN     Required. Sent as Bearer token.
EOF
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

query=""
limit="5"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --query)
      query="${2-}"
      shift 2
      ;;
    --limit)
      limit="${2-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown arg: $1"
      ;;
  esac
done

[[ -n "${query}" ]] || die "missing required --query"
[[ -n "${TOKEN}" ]] || die "MEMORY_API_TOKEN is required"

payload="$(QUERY="${query}" LIMIT="${limit}" python3 - <<'PY'
import json
import os

print(json.dumps({
    "query": os.environ["QUERY"],
    "limit": int(os.environ["LIMIT"]),
}))
PY
)"

curl -fsS \
  -H "Authorization: Bearer ${TOKEN}" \
  -H 'Content-Type: application/json' \
  -X POST \
  "${BASE_URL}/router/recall" \
  -d "${payload}"
printf '\n'
