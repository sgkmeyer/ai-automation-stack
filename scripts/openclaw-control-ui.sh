#!/usr/bin/env bash
set -euo pipefail

VM_HOST="${VM_HOST:-satoic-production}"
OPENCLAW_CONTAINER="${OPENCLAW_CONTAINER:-automation-openclaw-1}"
DASHBOARD_BASE_URL="${DASHBOARD_BASE_URL:-https://openclaw.satoic.com}"

say() {
  printf "%s\n" "$*"
}

usage() {
  cat <<'EOF'
Usage:
  ./scripts/openclaw-control-ui.sh status
  ./scripts/openclaw-control-ui.sh copy-url
  ./scripts/openclaw-control-ui.sh qr
  ./scripts/openclaw-control-ui.sh mobile-qr

Commands:
  status
    Read-only health/auth snapshot for the production OpenClaw Control UI.

  copy-url
    Copy a tokenized Control UI bootstrap URL for the configured dashboard origin
    to the local clipboard without printing the token to the terminal.

  qr
    Print a QR for the tokenized browser dashboard URL. Use this for a new
    phone/tablet/laptop browser that says to run "openclaw dashboard".

  mobile-qr
    Print OpenClaw's mobile setup QR for the configured dashboard origin.
    Scan it from the new device, then approve the pending device if prompted.

Environment overrides:
  VM_HOST
  OPENCLAW_CONTAINER
  DASHBOARD_BASE_URL
EOF
}

remote_openclaw() {
  local cmd="${1:?}"
  local quoted_cmd=""
  printf -v quoted_cmd "%q" "${cmd}"
  # shellcheck disable=SC2029
  ssh "${VM_HOST}" "docker exec ${OPENCLAW_CONTAINER} sh -lc ${quoted_cmd}"
}

copy_url() {
  if ! command -v pbcopy >/dev/null 2>&1; then
    say "ERROR: pbcopy is required for copy-url on this machine."
    say "Run this on macOS, or add a clipboard handler before using copy-url."
    exit 1
  fi

  local token=""
  local url=""

  token="$(remote_openclaw "openclaw config get gateway.auth.token")"
  if [[ -z "${token}" ]]; then
    say "ERROR: OpenClaw gateway token lookup returned empty output."
    exit 1
  fi

  url="${DASHBOARD_BASE_URL%/}/#token=${token}"
  printf "%s" "${url}" | pbcopy
  say "Copied OpenClaw Control UI bootstrap URL to the clipboard."
  say "Open a fresh browser tab and paste it into the address bar."
  say "If the UI then shows 'pairing required', approve the pending device request."
}

qr() {
  local public_url="${DASHBOARD_BASE_URL%/}"

  remote_openclaw "token=\$(openclaw config get gateway.auth.token); node -e \"const qr=require('qrcode-terminal'); const url=process.argv[1]; console.log('Dashboard QR for ${public_url}'); console.log('Scan this on the new browser device.'); qr.generate(url, { small: false }); console.log('URL: ${public_url}/#token=<redacted>');\" \"${public_url}/#token=\$token\""
}

mobile_qr() {
  local public_url="${DASHBOARD_BASE_URL%/}"

  remote_openclaw "token=\$(openclaw config get gateway.auth.token); openclaw qr --url '${public_url}' --token \"\$token\""
}

status() {
  say "Checking OpenClaw Control UI health on ${VM_HOST}..."
  remote_openclaw "openclaw config get gateway.auth.mode"
  remote_openclaw 'node -e "fetch(\"http://127.0.0.1:18789/healthz\").then(r=>{ if (!r.ok) throw new Error(\"healthz=\" + r.status); console.log(\"healthz=ok\") }).catch(e=>{ console.error(e.message); process.exit(1) })"'
  # shellcheck disable=SC2029
  ssh "${VM_HOST}" "docker logs --since 20m --tail 80 ${OPENCLAW_CONTAINER} 2>&1 | grep -E 'token missing|AUTH_TOKEN_MISSING|pairing required|device_token_mismatch|closed before connect' || true"
}

main() {
  local cmd="${1:-}"

  case "${cmd}" in
    status)
      status
      ;;
    copy-url)
      copy_url
      ;;
    qr)
      qr
      ;;
    mobile-qr)
      mobile_qr
      ;;
    ""|-h|--help|help)
      usage
      ;;
    *)
      say "ERROR: unknown command '${cmd}'."
      usage
      exit 1
      ;;
  esac
}

main "${1:-}"
