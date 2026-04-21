#!/usr/bin/env bash
# Replay a Krisp webhook payload to dev or prod for adapter validation.

set -euo pipefail

KRISP_WEBHOOK_URL="${KRISP_WEBHOOK_URL:-https://n8n.satoic.com/webhook/memory/ingest/krisp}"
KRISP_WEBHOOK_SECRET="${KRISP_WEBHOOK_SECRET:-}"
KRISP_WEBHOOK_SECRET_HEADER="${KRISP_WEBHOOK_SECRET_HEADER:-x-krisp-webhook-secret}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FIXTURE_FILE="${REPO_ROOT}/workflows/governed/mem-06-krisp-webhook-adapter/test-fixtures.json"

usage() {
  cat <<'EOF'
Usage:
  scripts/replay-krisp-webhook.sh (--payload FILE | --fixture NAME) [--url URL] [--secret SECRET] [--header NAME]

Environment:
  KRISP_WEBHOOK_URL            Defaults to https://n8n.satoic.com/webhook/memory/ingest/krisp
  KRISP_WEBHOOK_SECRET         Required unless passed via --secret
  KRISP_WEBHOOK_SECRET_HEADER  Defaults to x-krisp-webhook-secret

Examples:
  scripts/replay-krisp-webhook.sh --fixture transcriptReady
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
fixture=""
temp_payload=""

cleanup() {
  if [[ -n "${temp_payload}" && -f "${temp_payload}" ]]; then
    rm -f "${temp_payload}"
  fi
}

trap cleanup EXIT

while [[ $# -gt 0 ]]; do
  case "$1" in
    --payload) payload="${2-}"; shift 2 ;;
    --fixture) fixture="${2-}"; shift 2 ;;
    --url) KRISP_WEBHOOK_URL="${2-}"; shift 2 ;;
    --secret) KRISP_WEBHOOK_SECRET="${2-}"; shift 2 ;;
    --header) KRISP_WEBHOOK_SECRET_HEADER="${2-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done

if [[ -n "${payload}" && -n "${fixture}" ]]; then
  die "use either --payload or --fixture, not both"
fi
if [[ -z "${payload}" && -z "${fixture}" ]]; then
  die "missing --payload or --fixture"
fi

if [[ -n "${fixture}" ]]; then
  [[ -f "${FIXTURE_FILE}" ]] || die "fixture file not found: ${FIXTURE_FILE}"
  temp_payload="$(mktemp "${TMPDIR:-/tmp}/krisp-fixture.XXXXXX.json")"
  FIXTURE_PATH="${FIXTURE_FILE}" FIXTURE_NAME="${fixture}" OUTPUT_PATH="${temp_payload}" python3 - <<'PY'
import json
import os
import sys

fixture_path = os.environ["FIXTURE_PATH"]
fixture_name = os.environ["FIXTURE_NAME"]
output_path = os.environ["OUTPUT_PATH"]

with open(fixture_path, encoding="utf-8") as handle:
    fixtures = json.load(handle)

fixture = fixtures.get(fixture_name)
if not fixture:
    available = ", ".join(sorted(fixtures))
    raise SystemExit(f"unknown fixture: {fixture_name}. Available: {available}")

payload = fixture.get("request")
if not isinstance(payload, dict):
    raise SystemExit(f"fixture {fixture_name} does not contain a request object")

with open(output_path, "w", encoding="utf-8") as handle:
    json.dump(payload, handle)
PY
  payload="${temp_payload}"
fi

[[ -f "${payload}" ]] || die "payload file not found: ${payload}"
[[ -n "${KRISP_WEBHOOK_SECRET}" ]] || die "missing KRISP_WEBHOOK_SECRET"

curl -fsS \
  -H 'Content-Type: application/json' \
  -H "${KRISP_WEBHOOK_SECRET_HEADER}: ${KRISP_WEBHOOK_SECRET}" \
  -X POST \
  "${KRISP_WEBHOOK_URL}" \
  --data-binary "@${payload}"
printf '\n'
