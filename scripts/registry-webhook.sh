#!/usr/bin/env bash
# Thin CLI over the published registry webhooks.

set -euo pipefail

BASE_URL="${REGISTRY_WEBHOOK_BASE_URL:-https://n8n.satoic.com/webhook/registry}"
SECRET="${REGISTRY_WEBHOOK_SECRET:-}"

usage() {
  cat <<'EOF'
Usage:
  scripts/registry-webhook.sh capture --url URL [--note TEXT] [--tags a,b] [--capture-channel NAME]
  scripts/registry-webhook.sh query --query TEXT [--limit N] [--page N] [--mode answer|list|summary] [--review-state STATE] [--source-kind KIND] [--topics a,b] [--user-tags a,b]
  scripts/registry-webhook.sh list [--limit N] [--page N] [--sort newest|oldest] [--review-state STATE] [--source-kind KIND] [--topics a,b] [--user-tags a,b]
  scripts/registry-webhook.sh review --item-id UUID --action mark_reviewed|archive|mark_inbox
  scripts/registry-webhook.sh process --item-id UUID [--reprocess true|false]

Environment:
  REGISTRY_WEBHOOK_BASE_URL  Defaults to https://n8n.satoic.com/webhook/registry
  REGISTRY_WEBHOOK_SECRET    Required. Sent as x-registry-webhook-secret.

Examples:
  scripts/registry-webhook.sh capture --url "https://example.com" --note "good GTM example"
  scripts/registry-webhook.sh query --query "AI GTM" --limit 3
  scripts/registry-webhook.sh list --review-state inbox --limit 3 --sort oldest
  scripts/registry-webhook.sh review --item-id 11111111-1111-1111-1111-111111111111 --action archive
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

require_secret() {
  [[ -n "${SECRET}" ]] || die "REGISTRY_WEBHOOK_SECRET is required"
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

post_json() {
  local path="${1:?}"
  local payload="${2:?}"
  require_secret
  curl -fsS \
    -H 'Content-Type: application/json' \
    -H "x-registry-webhook-secret: ${SECRET}" \
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
  capture)
    url=""
    note=""
    tags=""
    capture_channel="manual"
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --url) url="${2-}"; shift 2 ;;
        --note) note="${2-}"; shift 2 ;;
        --tags) tags="${2-}"; shift 2 ;;
        --capture-channel) capture_channel="${2-}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) die "unknown arg for capture: $1" ;;
      esac
    done
    require_value "--url" "${url}"
    payload="$(URL="${url}" NOTE="${note}" TAGS_JSON="$(split_csv_json "${tags}")" CAPTURE_CHANNEL="${capture_channel}" python3 - <<'PY'
import json
import os

payload = {
    "url": os.environ["URL"],
    "note": os.environ["NOTE"] or None,
    "tags": json.loads(os.environ["TAGS_JSON"]),
    "capture_channel": os.environ["CAPTURE_CHANNEL"],
}
print(json.dumps(payload))
PY
)"
    post_json "capture" "${payload}"
    ;;

  query)
    query=""
    limit="10"
    page="1"
    mode="answer"
    review_state=""
    source_kind=""
    topics=""
    user_tags=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --query) query="${2-}"; shift 2 ;;
        --limit) limit="${2-}"; shift 2 ;;
        --page) page="${2-}"; shift 2 ;;
        --mode) mode="${2-}"; shift 2 ;;
        --review-state) review_state="${2-}"; shift 2 ;;
        --source-kind) source_kind="${2-}"; shift 2 ;;
        --topics) topics="${2-}"; shift 2 ;;
        --user-tags) user_tags="${2-}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) die "unknown arg for query: $1" ;;
      esac
    done
    require_value "--query" "${query}"
    payload="$(QUERY="${query}" LIMIT="${limit}" PAGE="${page}" MODE="${mode}" REVIEW_STATE="${review_state}" SOURCE_KIND="${source_kind}" TOPICS_JSON="$(split_csv_json "${topics}")" USER_TAGS_JSON="$(split_csv_json "${user_tags}")" python3 - <<'PY'
import json
import os

payload = {
    "query": os.environ["QUERY"],
    "limit": int(os.environ["LIMIT"]),
    "page": int(os.environ["PAGE"]),
    "mode": os.environ["MODE"],
    "topics": json.loads(os.environ["TOPICS_JSON"]),
    "user_tags": json.loads(os.environ["USER_TAGS_JSON"]),
}
if os.environ["REVIEW_STATE"]:
    payload["review_state"] = os.environ["REVIEW_STATE"]
if os.environ["SOURCE_KIND"]:
    payload["source_kind"] = os.environ["SOURCE_KIND"]
print(json.dumps(payload))
PY
)"
    post_json "query" "${payload}"
    ;;

  list)
    limit="10"
    page="1"
    sort="newest"
    review_state=""
    source_kind=""
    topics=""
    user_tags=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --limit) limit="${2-}"; shift 2 ;;
        --page) page="${2-}"; shift 2 ;;
        --sort) sort="${2-}"; shift 2 ;;
        --review-state) review_state="${2-}"; shift 2 ;;
        --source-kind) source_kind="${2-}"; shift 2 ;;
        --topics) topics="${2-}"; shift 2 ;;
        --user-tags) user_tags="${2-}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) die "unknown arg for list: $1" ;;
      esac
    done
    payload="$(LIMIT="${limit}" PAGE="${page}" SORT="${sort}" REVIEW_STATE="${review_state}" SOURCE_KIND="${source_kind}" TOPICS_JSON="$(split_csv_json "${topics}")" USER_TAGS_JSON="$(split_csv_json "${user_tags}")" python3 - <<'PY'
import json
import os

payload = {
    "limit": int(os.environ["LIMIT"]),
    "page": int(os.environ["PAGE"]),
    "sort": os.environ["SORT"],
    "topics": json.loads(os.environ["TOPICS_JSON"]),
    "user_tags": json.loads(os.environ["USER_TAGS_JSON"]),
}
if os.environ["REVIEW_STATE"]:
    payload["review_state"] = os.environ["REVIEW_STATE"]
if os.environ["SOURCE_KIND"]:
    payload["source_kind"] = os.environ["SOURCE_KIND"]
print(json.dumps(payload))
PY
)"
    post_json "list" "${payload}"
    ;;

  review)
    item_id=""
    action=""
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --item-id) item_id="${2-}"; shift 2 ;;
        --action) action="${2-}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) die "unknown arg for review: $1" ;;
      esac
    done
    require_value "--item-id" "${item_id}"
    require_value "--action" "${action}"
    payload="$(ITEM_ID="${item_id}" ACTION="${action}" python3 - <<'PY'
import json
import os

print(json.dumps({
    "item_id": os.environ["ITEM_ID"],
    "action": os.environ["ACTION"],
}))
PY
)"
    post_json "review" "${payload}"
    ;;

  process)
    item_id=""
    reprocess="false"
    while [[ $# -gt 0 ]]; do
      case "$1" in
        --item-id) item_id="${2-}"; shift 2 ;;
        --reprocess) reprocess="${2-}"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) die "unknown arg for process: $1" ;;
      esac
    done
    require_value "--item-id" "${item_id}"
    payload="$(ITEM_ID="${item_id}" REPROCESS="${reprocess}" python3 - <<'PY'
import json
import os

print(json.dumps({
    "item_id": os.environ["ITEM_ID"],
    "reprocess": os.environ["REPROCESS"].lower() == "true",
}))
PY
)"
    post_json "process" "${payload}"
    ;;

  -h|--help|help)
    usage
    ;;

  *)
    die "unknown command: ${command}"
    ;;
esac
