#!/usr/bin/env bash
# verify-memory-webhook.sh — end-to-end smoke test for the public memory webhook.
# Writes a dedicated smoke-test context entry, verifies readback, and deletes it.

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
memory_cli="${repo_root}/scripts/memory-webhook.sh"

base_url="${MEMORY_WEBHOOK_BASE_URL:-https://n8n.satoic.com/webhook/memory}"
domain="${MEMORY_SMOKE_DOMAIN:-ops_smoke}"
key="${MEMORY_SMOKE_KEY:-memory_webhook}"
value="smoke-$(date -u +%Y%m%dT%H%M%SZ)"
set_ok=false
delete_ok=false

say() { printf "%s\n" "$*"; }

parse_and_assert() {
  local mode="${1:?}"
  local payload="${2:?}"
  RESPONSE_MODE="${mode}" RESPONSE_PAYLOAD="${payload}" EXPECTED_DOMAIN="${domain}" EXPECTED_KEY="${key}" EXPECTED_VALUE="${value}" python3 - <<'PY'
import json
import os
import sys

mode = os.environ["RESPONSE_MODE"]
payload = json.loads(os.environ["RESPONSE_PAYLOAD"])
domain = os.environ["EXPECTED_DOMAIN"]
key = os.environ["EXPECTED_KEY"]
value = os.environ["EXPECTED_VALUE"]

if mode == "set":
    if payload.get("status") != "updated":
        raise SystemExit(f"unexpected set status: {payload!r}")
    if payload.get("domain") != domain or payload.get("key") != key:
        raise SystemExit(f"unexpected set payload: {payload!r}")
elif mode == "get":
    context = payload.get("context", {})
    items = context.get(domain, [])
    for item in items:
        if item.get("key") == key and item.get("value") == value:
            break
    else:
        raise SystemExit(f"context entry not found in payload: {payload!r}")
elif mode == "delete":
    if payload.get("status") != "deleted":
        raise SystemExit(f"unexpected delete status: {payload!r}")
    if payload.get("domain") != domain or payload.get("key") != key:
        raise SystemExit(f"unexpected delete payload: {payload!r}")
else:
    raise SystemExit(f"unsupported mode: {mode}")
PY
}

cleanup() {
  if ${set_ok} && ! ${delete_ok}; then
    MEMORY_WEBHOOK_BASE_URL="${base_url}" "${memory_cli}" context-delete --domain "${domain}" --key "${key}" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

say "Memory webhook smoke check"
say "Base URL: ${base_url}"
say "Context:  ${domain}/${key}"

set_response="$(MEMORY_WEBHOOK_BASE_URL="${base_url}" "${memory_cli}" context-set --domain "${domain}" --key "${key}" --value "${value}")"
parse_and_assert set "${set_response}"
set_ok=true
say "OK   memory context set"

get_response="$(MEMORY_WEBHOOK_BASE_URL="${base_url}" "${memory_cli}" context-get)"
parse_and_assert get "${get_response}"
say "OK   memory context get"

delete_response="$(MEMORY_WEBHOOK_BASE_URL="${base_url}" "${memory_cli}" context-delete --domain "${domain}" --key "${key}")"
parse_and_assert delete "${delete_response}"
delete_ok=true
say "OK   memory context delete"

say "Memory webhook smoke passed."
