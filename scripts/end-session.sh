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

today="$(date +%F)"
session_template="${repo_root}/ops/SESSION-TEMPLATE.md"
session_file="${repo_root}/ops/SESSION-${today}.md"

say "Session end: $(date)"
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

say "2) Create/update session handoff"
if [[ ! -f "${session_template}" ]]; then
  say "ERROR: Missing template: ${session_template}"
  say "Create it first (see ops/) and re-run."
  exit 1
fi

if [[ ! -f "${session_file}" ]]; then
  cp "${session_template}" "${session_file}"
  perl -pi -e "s/^# Session Log — YYYY-MM-DD\\s*\$/# Session Log — ${today}/" "${session_file}" || true
  say "Created: ${session_file}"
else
  say "Exists:  ${session_file}"
fi

say ""
say "Fill in the handoff file now:"
say "  ${session_file}"
read -r -p "Press Enter when ready to continue... " _ || true
hr

say "3) Update README 'latest session' pointer"
if [[ -f "${repo_root}/README.md" ]]; then
  perl -pi -e "s|^\\- `/Users/sgkmeyer/ai-automation-stack/ops/SESSION-[0-9]{4}-[0-9]{2}-[0-9]{2}\\.md` latest session handoff summary\\s*\$|- `/Users/sgkmeyer/ai-automation-stack/ops/SESSION-${today}.md` latest session handoff summary|g" "${repo_root}/README.md" || true
  say "Updated README pointer to SESSION-${today}.md (if present)."
else
  say "WARN: README.md not found; skipping."
fi
hr

say "4) Quick secret scan (optional but recommended)"
if confirm "Scan tracked files for common secret patterns?" ; then
  # Keep this lightweight and conservative. This is not a full secret scanner.
  git grep -nE '(OPENCLAW_GATEWAY_TOKEN|N8N_API_KEY|BROWSERLESS_TOKEN|BRAVE_API_KEY|-----BEGIN( RSA| OPENSSH)? PRIVATE KEY|sk-[A-Za-z0-9]{20,})' || true
  hr
fi

say "5) Review git status"
git status -sb
hr

if confirm "Commit and push all current changes?" ; then
  if ! git remote get-url origin >/dev/null 2>&1; then
    say "ERROR: No 'origin' remote configured. Configure it first, then rerun."
    exit 1
  fi

  git add -A
  if git diff --cached --quiet; then
    say "No staged changes to commit."
  else
    default_msg="chore: session handoff ${today}"
    read -r -p "Commit message [${default_msg}]: " msg || true
    msg="${msg:-$default_msg}"
    git commit -m "${msg}"
  fi

  git push
  hr
fi

say "6) Deploy"
say "   Default: GitOps (VM pulls from GitHub and applies)"
say "   Emergency: rsync (direct copy from laptop)"
hr

deploy_mode="none"
if confirm "Deploy now via GitOps?" ; then
  deploy_mode="gitops"
elif confirm "Emergency deploy via rsync?" ; then
  deploy_mode="rsync"
fi

if [[ "${deploy_mode}" == "gitops" ]]; then
  if confirm "Take backups on VM before applying (recommended for config/db-impacting changes)?" ; then
    say "Running backups on VM..."
    ssh satoic-vm 'set -euo pipefail; cd /home/ubuntu; sudo tar czf automation-full-$(date +%F-%H%M).tar.gz automation; docker run --rm -v automation_db_storage:/data -v /home/ubuntu:/backup busybox tar czf /backup/automation-db-$(date +%F-%H%M).tar.gz /data; ls -lh /home/ubuntu/automation-full-*.tar.gz /home/ubuntu/automation-db-*.tar.gz | tail -n 4'
    hr
  fi

  say "Running GitOps deploy on VM..."
  ssh satoic-vm '/home/ubuntu/ai-automation-stack/scripts/gitops-deploy.sh'
  hr

  if confirm "Run external verification from this laptop (curl -I)?" ; then
    curl -I https://n8n.satoic.com | head -n 5 || true
    curl -I https://openclaw.satoic.com | head -n 5 || true
    curl -I https://portainer.satoic.com | head -n 5 || true
    hr
  fi
elif [[ "${deploy_mode}" == "rsync" ]]; then
  if confirm "Take backups on VM before applying (recommended for config/db-impacting changes)?" ; then
    say "Running backups on VM..."
    ssh satoic-vm 'set -euo pipefail; cd /home/ubuntu; sudo tar czf automation-full-$(date +%F-%H%M).tar.gz automation; docker run --rm -v automation_db_storage:/data -v /home/ubuntu:/backup busybox tar czf /backup/automation-db-$(date +%F-%H%M).tar.gz /data; ls -lh /home/ubuntu/automation-full-*.tar.gz /home/ubuntu/automation-db-*.tar.gz | tail -n 4'
    hr
  fi

  ./scripts/sync-to-vm.sh
  hr

  if confirm "Apply stack changes on VM now (docker compose up -d + caddy reload)?" ; then
    ssh satoic-vm 'set -euo pipefail; cd /home/ubuntu/automation; docker compose -f docker-compose.yml -f docker-compose.chromium-native.yml -f docker-compose.chromium-ip.yml up -d; docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile; docker compose -f docker-compose.yml -f docker-compose.chromium-native.yml -f docker-compose.chromium-ip.yml ps'
    hr
  else
    say "Apply on VM when ready:"
    say "  ssh satoic-vm"
    say "  cd /home/ubuntu/automation"
    say "  docker compose -f docker-compose.yml -f docker-compose.chromium-native.yml -f docker-compose.chromium-ip.yml up -d"
    say "  docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile"
    hr
  fi

  if confirm "Run external verification from this laptop (curl -I)?" ; then
    curl -I https://n8n.satoic.com | head -n 5 || true
    curl -I https://openclaw.satoic.com | head -n 5 || true
    curl -I https://portainer.satoic.com | head -n 5 || true
    hr
  fi
fi

say ""
say "End-session complete."
