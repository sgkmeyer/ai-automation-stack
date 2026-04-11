#!/usr/bin/env bash
# Thin CLI over direct memory-api wiki endpoints.

set -euo pipefail

BASE_URL="${MEMORY_API_BASE_URL:-http://memory-api:8100}"
TOKEN="${MEMORY_API_TOKEN:-}"

usage() {
  cat <<'EOF'
Usage:
  scripts/wiki-api.sh health
  scripts/wiki-api.sh search --query TEXT [--limit N] [--page-types a,b]
  scripts/wiki-api.sh page --page-ref wiki/projects/example.md
  scripts/wiki-api.sh propose --page-type TYPE --title TITLE [--content TEXT | --content-file PATH] [--source-refs a,b] [--tags a,b] [--slug SLUG] [--page-ref PATH] [--confidence LEVEL]
  scripts/wiki-api.sh proposals [--status pending_review|approved|rejected] [--limit N]
  scripts/wiki-api.sh review --proposal-id UUID --action approve|reject
  scripts/wiki-api.sh lint [--limit N]

Environment:
  MEMORY_API_BASE_URL       Defaults to http://memory-api:8100
  MEMORY_API_TOKEN          Required. Sent as Bearer token.
  MEMORY_DEFAULT_ACTOR_TYPE
  MEMORY_DEFAULT_ACTOR_ID
  MEMORY_DEFAULT_SESSION_ID
  MEMORY_DEFAULT_SOURCE_CLIENT
  MEMORY_DEFAULT_REASON
EOF
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

require_token() {
  [[ -n "${TOKEN}" ]] || die "MEMORY_API_TOKEN is required"
}

require_value() {
  local name="${1:?}"
  local value="${2-}"
  [[ -n "${value}" ]] || die "missing required value for ${name}"
}

split_csv_json() {
  local csv="${1-}"
  CSV_VALUE="${csv}" python3 - <<'PY'
import json
import os

raw = os.environ.get("CSV_VALUE", "")
items = [item.strip() for item in raw.split(",") if item.strip()]
print(json.dumps(items))
PY
}

read_file_json() {
  local path="${1:?}"
  [[ -f "${path}" ]] || die "file not found: ${path}"
  FILE_PATH="${path}" python3 - <<'PY'
import json
import os
from pathlib import Path

path = Path(os.environ["FILE_PATH"]).expanduser()
print(json.dumps(path.read_text()))
PY
}

actor_env_json() {
  python3 - <<'PY'
import json
import os

payload = {
    "actor_type": os.environ.get("MEMORY_DEFAULT_ACTOR_TYPE") or None,
    "actor_id": os.environ.get("MEMORY_DEFAULT_ACTOR_ID") or None,
    "session_id": os.environ.get("MEMORY_DEFAULT_SESSION_ID") or None,
    "source_client": os.environ.get("MEMORY_DEFAULT_SOURCE_CLIENT") or None,
    "reason": os.environ.get("MEMORY_DEFAULT_REASON") or None,
}
print(json.dumps({key: value for key, value in payload.items() if value is not None}))
PY
}

get_with_auth() {
  local path="${1:?}"
  require_token
  curl -fsS \
    -H "Authorization: Bearer ${TOKEN}" \
    "${BASE_URL}/${path}"
  printf '\n'
}

post_with_auth() {
  local path="${1:?}"
  local payload="${2:?}"
  require_token
  curl -fsS \
    -H "Authorization: Bearer ${TOKEN}" \
    -H 'Content-Type: application/json' \
    -X POST \
    "${BASE_URL}/${path}" \
    -d "${payload}"
  printf '\n'
}

command="${1-}"
[[ -n "${command}" ]] || {
  usage
  exit 1
}
shift

case "${command}" in
  health)
    [[ $# -eq 0 ]] || die "health takes no arguments"
    get_with_auth "wiki/health"
    ;;

  search)
    query=""
    limit="5"
    page_types=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --query) query="${2-}"; shift 2 ;;
        --limit) limit="${2-}"; shift 2 ;;
        --page-types) page_types="${2-}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) die "unknown arg for search: $1" ;;
      esac
    done
    require_value "--query" "${query}"
    payload="$(QUERY="${query}" LIMIT="${limit}" PAGE_TYPES_JSON="$(split_csv_json "${page_types}")" python3 - <<'PY'
import json
import os

print(json.dumps({
    "query": os.environ["QUERY"],
    "limit": int(os.environ["LIMIT"]),
    "page_types": json.loads(os.environ["PAGE_TYPES_JSON"]),
}))
PY
)"
    post_with_auth "wiki/search" "${payload}"
    ;;

  page)
    page_ref=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --page-ref) page_ref="${2-}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) die "unknown arg for page: $1" ;;
      esac
    done
    require_value "--page-ref" "${page_ref}"
    payload="$(PAGE_REF="${page_ref}" python3 - <<'PY'
import json
import os

print(json.dumps({"page_ref": os.environ["PAGE_REF"]}))
PY
)"
    post_with_auth "wiki/page" "${payload}"
    ;;

  propose)
    page_type=""
    title=""
    content=""
    content_file=""
    source_refs=""
    tags=""
    slug=""
    page_ref=""
    confidence=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --page-type) page_type="${2-}"; shift 2 ;;
        --title) title="${2-}"; shift 2 ;;
        --content) content="${2-}"; shift 2 ;;
        --content-file) content_file="${2-}"; shift 2 ;;
        --source-refs) source_refs="${2-}"; shift 2 ;;
        --tags) tags="${2-}"; shift 2 ;;
        --slug) slug="${2-}"; shift 2 ;;
        --page-ref) page_ref="${2-}"; shift 2 ;;
        --confidence) confidence="${2-}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) die "unknown arg for propose: $1" ;;
      esac
    done
    require_value "--page-type" "${page_type}"
    require_value "--title" "${title}"
    if [[ -z "${content}" && -n "${content_file}" ]]; then
      content="$(CONTENT_FILE="${content_file}" python3 - <<'PY'
import os
from pathlib import Path

path = Path(os.environ["CONTENT_FILE"]).expanduser()
print(path.read_text())
PY
)"
    fi
    require_value "--content/--content-file" "${content}"
    payload="$(PAGE_TYPE="${page_type}" TITLE="${title}" CONTENT="${content}" SOURCE_REFS_JSON="$(split_csv_json "${source_refs}")" TAGS_JSON="$(split_csv_json "${tags}")" SLUG="${slug}" PAGE_REF="${page_ref}" CONFIDENCE="${confidence}" ACTOR_JSON="$(actor_env_json)" python3 - <<'PY'
import json
import os

payload = {
    "page_type": os.environ["PAGE_TYPE"],
    "title": os.environ["TITLE"],
    "content": os.environ["CONTENT"],
    "source_refs": json.loads(os.environ["SOURCE_REFS_JSON"]),
    "tags": json.loads(os.environ["TAGS_JSON"]),
}
if os.environ["SLUG"]:
    payload["slug"] = os.environ["SLUG"]
if os.environ["PAGE_REF"]:
    payload["page_ref"] = os.environ["PAGE_REF"]
if os.environ["CONFIDENCE"]:
    payload["confidence"] = os.environ["CONFIDENCE"]
payload.update(json.loads(os.environ["ACTOR_JSON"]))
print(json.dumps(payload))
PY
)"
    post_with_auth "wiki/proposals" "${payload}"
    ;;

  proposals)
    status=""
    limit="20"
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --status) status="${2-}"; shift 2 ;;
        --limit) limit="${2-}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) die "unknown arg for proposals: $1" ;;
      esac
    done
    payload="$(STATUS="${status}" LIMIT="${limit}" python3 - <<'PY'
import json
import os

payload = {"limit": int(os.environ["LIMIT"])}
if os.environ["STATUS"]:
    payload["status"] = os.environ["STATUS"]
print(json.dumps(payload))
PY
)"
    post_with_auth "wiki/proposals/list" "${payload}"
    ;;

  review)
    proposal_id=""
    action=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --proposal-id) proposal_id="${2-}"; shift 2 ;;
        --action) action="${2-}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) die "unknown arg for review: $1" ;;
      esac
    done
    require_value "--proposal-id" "${proposal_id}"
    require_value "--action" "${action}"
    payload="$(PROPOSAL_ID="${proposal_id}" ACTION="${action}" ACTOR_JSON="$(actor_env_json)" python3 - <<'PY'
import json
import os

payload = {
    "proposal_id": os.environ["PROPOSAL_ID"],
    "action": os.environ["ACTION"],
}
payload.update(json.loads(os.environ["ACTOR_JSON"]))
print(json.dumps(payload))
PY
)"
    post_with_auth "wiki/proposals/review" "${payload}"
    ;;

  lint)
    limit="50"
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --limit) limit="${2-}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) die "unknown arg for lint: $1" ;;
      esac
    done
    payload="$(LIMIT="${limit}" python3 - <<'PY'
import json
import os

print(json.dumps({"limit": int(os.environ["LIMIT"])}))
PY
)"
    post_with_auth "wiki/lint" "${payload}"
    ;;

  -h|--help|help)
    usage
    ;;

  *)
    die "unknown command: ${command}"
    ;;
esac
