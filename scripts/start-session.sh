#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${repo_root}"

say() { printf "%s\n" "$*"; }
hr() { printf "\n"; }

confirm() {
  local prompt="${1:?}"
  local reply=""
  read -r -p "${prompt} [y/N] " reply || true
  [[ "${reply}" == "y" || "${reply}" == "Y" ]]
}

say "Session start: $(date)"
say "Repo: ${repo_root}"
hr

say "1) Git fetch + status (ahead/behind)"
git fetch --prune || true
git status -sb
hr

if confirm "Pull latest VM runtime state (legacy rsync sync-from-vm)?" ; then
  ./scripts/sync-from-vm.sh
  hr
fi

say "2) Diff summary"
git diff --stat || true
hr

say "3) Deployment path"
say "   Default: GitOps (VM pulls from GitHub via scripts/gitops-deploy.sh)"
say "   Use rsync only for emergency patches."
hr

if confirm "Run VM health checks now (ssh satoic-vm)?" ; then
  say "Running compose ps + tail logs on VM..."
  ssh satoic-vm 'set -euo pipefail; cd /home/ubuntu/automation; docker compose -f docker-compose.yml -f docker-compose.chromium-native.yml -f docker-compose.chromium-ip.yml ps; echo; docker logs --tail 80 automation-caddy-1 || true; docker logs --tail 80 automation-n8n-1 || true; docker logs --tail 80 automation-openclaw-1 || true; docker logs --tail 80 automation-chromium-1 || true; docker logs --tail 80 automation-portainer-1 || true'
  hr
  say "External checks from laptop (optional):"
  say "  curl -I https://n8n.satoic.com"
  say "  curl -I https://openclaw.satoic.com"
  say "  curl -I https://portainer.satoic.com"
fi

say ""
say "Start-session complete."
