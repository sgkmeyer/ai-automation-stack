#!/usr/bin/env bash
# setup-tailscale-daemon.sh — install tailscaled as a system LaunchDaemon (Mac only)
# Run once with: sudo ./scripts/setup-tailscale-daemon.sh
# After install, tailscaled starts automatically at boot and after crashes.
set -euo pipefail

PLIST_SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/com.tailscale.tailscaled.plist"
PLIST_DST="/Library/LaunchDaemons/com.tailscale.tailscaled.plist"
STATE_DIR="/var/lib/tailscale"

if [[ "$(uname)" != "Darwin" ]]; then
  echo "ERROR: This script is for macOS only."
  exit 1
fi

if [[ "$(id -u)" -ne 0 ]]; then
  echo "ERROR: Must run as root. Use: sudo $0"
  exit 1
fi

echo "==> Creating Tailscale state directory: ${STATE_DIR}"
mkdir -p "${STATE_DIR}"
chmod 700 "${STATE_DIR}"

echo "==> Installing LaunchDaemon plist to ${PLIST_DST}"
cp "${PLIST_SRC}" "${PLIST_DST}"
chown root:wheel "${PLIST_DST}"
chmod 644 "${PLIST_DST}"

# Unload existing if present (ignore error if not loaded)
launchctl unload "${PLIST_DST}" 2>/dev/null || true

echo "==> Loading LaunchDaemon..."
launchctl load -w "${PLIST_DST}"

echo "==> Waiting for tailscaled to start..."
sleep 3

echo "==> Tailscale status:"
tailscale status 2>&1 || true

echo ""
echo "Done. If Tailscale shows 'Logged out', run: tailscale up"
echo "If already authenticated previously, it should reconnect automatically."
