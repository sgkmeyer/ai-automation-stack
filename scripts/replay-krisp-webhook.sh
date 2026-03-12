#!/usr/bin/env bash
# Replay a Krisp webhook payload to dev or prod for adapter validation.

set -euo pipefail

KRISP_WEBHOOK_URL="${KRISP_WEBHOOK_URL:-https://n8n.satoic.com/webhook/memory/ingest/krisp}"
KRISP_WEBHOOK_SECRET="${KRISP_WEBHOOK_SECRET:-}"
KRISP_WEBHOOK_SECRET_HEADER="${KRISP_WEBHOOK_SECRET_HEADER:-x-krisp-webhook-secret}"

usage() {
  cat <<'EOF'
Usage:
  scripts/replay-krisp-webhook.sh --payload FILE [--url URL] [--secret SECRET] [--header NAME]

Environment:
  KRISP_WEBHOOK_URL            Defaults to https://n8n.satoic.com/webhook/memory/ingest/krisp
  KRISP_WEBHOOK_SECRET         Required unless passed via --secret
  KRISP_WEBHOOK_SECRET_HEADER  Defaults to x-krisp-webhook-secret

Examples:
  scripts/replay-krisp-webhook.sh --payload workflows/governed/mem-06-krisp-webhook-adapter/test-fixtures.json
  KRISP_WEBHOOK_URL=http://100.82.169.113:5679/webhook/memory/ingest/krisp \
    KRISP_WEBHOOK_SECRET=changeme \
    scripts/replay-krisp-webhook.sh --payload /tmp/krisp-event.json
EOF
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

payload=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --payload) payload="${2-}"; shift 2 ;;
    --url) KRISP_WEBHOOK_URL="${2-}"; shift 2 ;;
    --secret) KRISP_WEBHOOK_SECRET="${2-}"; shift 2 ;;
    --header) KRISP_WEBHOOK_SECRET_HEADER="${2-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

[[ -n "${payload}" ]] || die "missing --payload"
[[ -f "${payload}" ]] || die "payload file not found: ${payload}"
[[ -n "${KRISP_WEBHOOK_SECRET}" ]] || die "missing KRISP_WEBHOOK_SECRET"

curl -fsS \
  -H 'Content-Type: application/json' \
  -H "${KRISP_WEBHOOK_SECRET_HEADER}: ${KRISP_WEBHOOK_SECRET}" \
  -X POST \
  "${KRISP_WEBHOOK_URL}" \
  --data-binary "@${payload}"
printf '\n'
