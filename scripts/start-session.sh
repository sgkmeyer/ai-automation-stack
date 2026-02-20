#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

full_mode=false
if [[ "${1:-}" == "--full" ]]; then
  full_mode=true
fi

log_file="${repo_root}/ops/start-session-$(date +%F).log"
mkdir -p "${repo_root}/ops"
exec > >(tee -a "${log_file}") 2>&1

say() { printf "%s\n" "$*"; }
hr() { printf "\n"; }

confirm() {
  local prompt="${1:?}"
  local reply=""
  read -r -p "${prompt} [y/N] " reply || true
  [[ "${reply}" == "y" || "${reply}" == "Y" ]]
}

session_status="CLEAN"
mark_warning() { session_status="WARNING"; }

say "Session start: $(date)"
say "Repo: ${repo_root}"
say "Log: ${log_file}"
hr

say "0) Tailscale status"
if tailscale status &>/dev/null; then
  say "   Tailscale: connected"
  tailscale status --peers=false 2>/dev/null || true
else
  say "   Tailscale: NOT running"
  say "   VM access via public IP (ssh oracle) will still work."
  say "   To fix: sudo launchctl load /Library/LaunchDaemons/com.tailscale.tailscaled.plist"
  say "   (Run setup once: sudo ./scripts/setup-tailscale-daemon.sh)"
  mark_warning
fi
hr

say "1) Git fetch + status"
if ! git fetch --prune; then
  say "WARNING: git fetch failed."
  mark_warning
fi
git status -sb
hr

say "2) Diff summary"
git diff --stat || true
hr

say "3) Deployment path"
say "   GitOps: push to main → GitHub Actions CI → SSH → gitops-deploy.sh on VM"
say "   Emergency only: ./scripts/sync-to-vm.sh (rsync direct)"
hr

if ${full_mode}; then
  say "Full mode: running VM health checks."
  if ! ssh satoic-vm 'set -euo pipefail; cd /home/ubuntu/automation; docker compose -f docker-compose.yml -f docker-compose.chromium-native.yml -f docker-compose.chromium-ip.yml ps'; then
    say "WARNING: VM health checks failed."
    mark_warning
  fi
  hr
elif confirm "Run VM health checks now (ssh satoic-vm)?"; then
  say "Running compose ps on VM..."
  if ! ssh satoic-vm 'set -euo pipefail; cd /home/ubuntu/automation; docker compose -f docker-compose.yml -f docker-compose.chromium-native.yml -f docker-compose.chromium-ip.yml ps'; then
    say "WARNING: VM health checks failed."
    mark_warning
  fi
  hr
fi

say "START STATUS: ${session_status}"
say "Start-session complete."
