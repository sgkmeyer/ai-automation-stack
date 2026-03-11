#!/usr/bin/env bash
# Thin CLI over the published memory webhooks.

set -euo pipefail

BASE_URL="${MEMORY_WEBHOOK_BASE_URL:-https://n8n.satoic.com/webhook/memory}"

usage() {
  cat <<'EOF'
Usage:
  scripts/memory-webhook.sh log --text TEXT [--source SOURCE] [--tags a,b]
  scripts/memory-webhook.sh recall --query TEXT [--limit N] [--synthesize true|false]
  scripts/memory-webhook.sh context-get
  scripts/memory-webhook.sh context-set --domain DOMAIN --key KEY --value VALUE
  scripts/memory-webhook.sh context-delete --domain DOMAIN --key KEY
  scripts/memory-webhook.sh document --source-ref REF --file PATH [--title TITLE] [--tags a,b] [--source SOURCE]
  scripts/memory-webhook.sh transcript --source-ref REF --file PATH [--title TITLE] [--summary TEXT] [--participants a,b] [--action-items a,b]

Environment:
  MEMORY_WEBHOOK_BASE_URL  Defaults to https://n8n.satoic.com/webhook/memory

Examples:
  scripts/memory-webhook.sh log --text "Met Sam for coffee" --tags relationship
  scripts/memory-webhook.sh recall --query "coffee with Sam" --limit 3
  scripts/memory-webhook.sh context-set --domain prefs --key coffee --value "flat white"
  scripts/memory-webhook.sh document --source-ref Daily/2026-03-11.md --file ~/vault/Daily/2026-03-11.md
  scripts/memory-webhook.sh transcript --source-ref krisp:demo --file ./meeting.txt --action-items "Send proposal,Book follow-up"
EOF
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
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

post_json() {
  local path="${1:?}"
  local payload="${2:?}"
  curl -fsS \
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
  log)
    text=""
    source="manual"
    tags=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --text) text="${2-}"; shift 2 ;;
        --source) source="${2-}"; shift 2 ;;
        --tags) tags="${2-}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) die "unknown arg for log: $1" ;;
      esac
    done
    require_value "--text" "${text}"
    payload="$(TEXT="${text}" SOURCE="${source}" TAGS_JSON="$(split_csv_json "${tags}")" python3 - <<'PY'
import json
import os

payload = {
    "text": os.environ["TEXT"],
    "source": os.environ["SOURCE"],
    "tags": json.loads(os.environ["TAGS_JSON"]),
}
print(json.dumps(payload))
PY
)"
    post_json "log" "${payload}"
    ;;

  recall)
    query=""
    limit="5"
    synthesize="false"
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --query) query="${2-}"; shift 2 ;;
        --limit) limit="${2-}"; shift 2 ;;
        --synthesize) synthesize="${2-}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) die "unknown arg for recall: $1" ;;
      esac
    done
    require_value "--query" "${query}"
    payload="$(QUERY="${query}" LIMIT="${limit}" SYNTHESIZE="${synthesize}" python3 - <<'PY'
import json
import os

payload = {
    "query": os.environ["QUERY"],
    "limit": int(os.environ["LIMIT"]),
    "synthesize": os.environ["SYNTHESIZE"].lower() == "true",
}
print(json.dumps(payload))
PY
)"
    post_json "recall" "${payload}"
    ;;

  context-get)
    [[ $# -eq 0 ]] || die "context-get takes no arguments"
    post_json "context" '{"action":"get"}'
    ;;

  context-set)
    domain=""
    key=""
    value=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --domain) domain="${2-}"; shift 2 ;;
        --key) key="${2-}"; shift 2 ;;
        --value) value="${2-}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) die "unknown arg for context-set: $1" ;;
      esac
    done
    require_value "--domain" "${domain}"
    require_value "--key" "${key}"
    require_value "--value" "${value}"
    payload="$(DOMAIN="${domain}" KEY="${key}" VALUE="${value}" python3 - <<'PY'
import json
import os

print(json.dumps({
    "action": "set",
    "domain": os.environ["DOMAIN"],
    "key": os.environ["KEY"],
    "value": os.environ["VALUE"],
}))
PY
)"
    post_json "context" "${payload}"
    ;;

  context-delete)
    domain=""
    key=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --domain) domain="${2-}"; shift 2 ;;
        --key) key="${2-}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) die "unknown arg for context-delete: $1" ;;
      esac
    done
    require_value "--domain" "${domain}"
    require_value "--key" "${key}"
    payload="$(DOMAIN="${domain}" KEY="${key}" python3 - <<'PY'
import json
import os

print(json.dumps({
    "action": "delete",
    "domain": os.environ["DOMAIN"],
    "key": os.environ["KEY"],
}))
PY
)"
    post_json "context" "${payload}"
    ;;

  document)
    source_ref=""
    file_path=""
    title=""
    tags=""
    source="obsidian"
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --source-ref) source_ref="${2-}"; shift 2 ;;
        --file) file_path="${2-}"; shift 2 ;;
        --title) title="${2-}"; shift 2 ;;
        --tags) tags="${2-}"; shift 2 ;;
        --source) source="${2-}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) die "unknown arg for document: $1" ;;
      esac
    done
    require_value "--source-ref" "${source_ref}"
    require_value "--file" "${file_path}"
    payload="$(SOURCE="${source}" SOURCE_REF="${source_ref}" TITLE="${title}" TAGS_JSON="$(split_csv_json "${tags}")" CONTENT_JSON="$(read_file_json "${file_path}")" python3 - <<'PY'
import json
import os
from pathlib import Path

source_ref = os.environ["SOURCE_REF"]
title = os.environ["TITLE"] or Path(source_ref).stem
payload = {
    "source": os.environ["SOURCE"],
    "source_ref": source_ref,
    "source_type": Path(source_ref).suffix.lstrip(".") or "md",
    "title": title,
    "content": json.loads(os.environ["CONTENT_JSON"]),
    "tags": json.loads(os.environ["TAGS_JSON"]),
}
print(json.dumps(payload))
PY
)"
    post_json "ingest/document" "${payload}"
    ;;

  transcript)
    source_ref=""
    file_path=""
    title=""
    summary=""
    participants=""
    action_items=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --source-ref) source_ref="${2-}"; shift 2 ;;
        --file) file_path="${2-}"; shift 2 ;;
        --title) title="${2-}"; shift 2 ;;
        --summary) summary="${2-}"; shift 2 ;;
        --participants) participants="${2-}"; shift 2 ;;
        --action-items) action_items="${2-}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) die "unknown arg for transcript: $1" ;;
      esac
    done
    require_value "--source-ref" "${source_ref}"
    require_value "--file" "${file_path}"
    payload="$(SOURCE_REF="${source_ref}" TITLE="${title}" SUMMARY="${summary}" PARTICIPANTS_JSON="$(split_csv_json "${participants}")" ACTION_ITEMS_JSON="$(split_csv_json "${action_items}")" TRANSCRIPT_JSON="$(read_file_json "${file_path}")" python3 - <<'PY'
import json
import os

payload = {
    "source_ref": os.environ["SOURCE_REF"],
    "title": os.environ["TITLE"] or None,
    "summary": os.environ["SUMMARY"] or None,
    "transcript_text": json.loads(os.environ["TRANSCRIPT_JSON"]),
    "participants": json.loads(os.environ["PARTICIPANTS_JSON"]),
    "action_items": json.loads(os.environ["ACTION_ITEMS_JSON"]),
}
print(json.dumps(payload))
PY
)"
    post_json "ingest/transcript" "${payload}"
    ;;

  -h|--help|help)
    usage
    ;;

  *)
    die "unknown command: ${command}"
    ;;
esac
