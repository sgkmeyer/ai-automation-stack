#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"
full_mode=false
with_rsync=false
if [[ "${1:-}" == "--full" ]]; then
  full_mode=true
fi
if [[ "${2:-}" == "--with-rsync" || "${1:-}" == "--with-rsync" ]]; then
  with_rsync=true
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

mark_warning() {
  session_status="WARNING"
}

say "Session start: $(date)"
say "Repo: ${repo_root}"
say "Log: ${log_file}"
hr

say "1) Git fetch + status (ahead/behind)"
if ! git fetch --prune; then
  say "WARNING: git fetch failed. You may be looking at stale remote state."
  mark_warning
fi
git status -sb
hr

if ${full_mode} && ${with_rsync}; then
  say "Full mode + --with-rsync: pulling latest VM runtime state (legacy)."
  if ! ./scripts/sync-from-vm.sh; then
    say "WARNING: sync-from-vm failed."
    mark_warning
  fi
  hr
elif confirm "Pull latest VM runtime state (legacy rsync sync-from-vm)?" ; then
  if ! ./scripts/sync-from-vm.sh; then
    say "WARNING: sync-from-vm failed."
    mark_warning
  fi
  hr
fi

say "2) Diff summary"
git diff --stat || true
hr

say "3) Deployment path"
say "   Default: GitOps (VM pulls from GitHub via scripts/gitops-deploy.sh)"
say "   Use rsync only for emergency patches."
hr

if ${full_mode}; then
  say "Full mode: running VM health checks."
  if ! ssh satoic-vm 'set -euo pipefail; cd /home/ubuntu/automation; docker compose -f docker-compose.yml -f docker-compose.chromium-native.yml -f docker-compose.chromium-ip.yml ps; echo; docker logs --since 30m --tail 80 automation-caddy-1 || true; docker logs --since 30m --tail 80 automation-n8n-1 || true; docker logs --since 30m --tail 80 automation-openclaw-1 || true; docker logs --since 30m --tail 80 automation-chromium-1 || true; docker logs --since 30m --tail 80 automation-portainer-1 || true'; then
    say "WARNING: VM health checks failed."
    mark_warning
  fi
  hr
  say "Full mode: running external checks from laptop."
  if ! curl -I https://n8n.satoic.com | head -n 5; then
    mark_warning
  fi
  if ! curl -I https://openclaw.satoic.com | head -n 5; then
    mark_warning
  fi
  if ! curl -I https://portainer.satoic.com | head -n 5; then
    mark_warning
  fi
  hr
elif confirm "Run VM health checks now (ssh satoic-vm)?" ; then
  say "Running compose ps + tail logs on VM..."
  if ! ssh satoic-vm 'set -euo pipefail; cd /home/ubuntu/automation; docker compose -f docker-compose.yml -f docker-compose.chromium-native.yml -f docker-compose.chromium-ip.yml ps; echo; docker logs --since 30m --tail 80 automation-caddy-1 || true; docker logs --since 30m --tail 80 automation-n8n-1 || true; docker logs --since 30m --tail 80 automation-openclaw-1 || true; docker logs --since 30m --tail 80 automation-chromium-1 || true; docker logs --since 30m --tail 80 automation-portainer-1 || true'; then
    say "WARNING: VM health checks failed."
    mark_warning
  fi
  hr
  say "External checks from laptop (optional):"
  say "  curl -I https://n8n.satoic.com"
  say "  curl -I https://openclaw.satoic.com"
  say "  curl -I https://portainer.satoic.com"
fi

say ""
say "START STATUS: ${session_status}"
say "Start-session complete."
