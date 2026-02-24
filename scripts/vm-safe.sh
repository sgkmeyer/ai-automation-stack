#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VM_HOST="${VM_HOST:-satoic-production}"
VM_DIR="${VM_DIR:-/home/ubuntu/automation}"
VM_REPO_DIR="${VM_REPO_DIR:-/home/ubuntu/ai-automation-stack}"
LOCAL_DR_DIR="${LOCAL_DR_DIR:-${repo_root}/.dr-backups}"
ASSUME_YES=false

if [[ "${1:-}" == "--yes" ]]; then
  ASSUME_YES=true
  shift
fi

say() { printf "%s\n" "$*"; }

confirm() {
  local prompt="${1:?}"
  local reply=""
  if ${ASSUME_YES}; then
    return 0
  fi
  read -r -p "${prompt} [y/N] " reply || true
  [[ "${reply}" == "y" || "${reply}" == "Y" ]]
}

usage() {
  cat <<'EOF'
Usage:
  ./scripts/vm-safe.sh [--yes] <action> [args]

Actions:
  health
    VM docker compose ps + recent logs (last 30m) for core services.

  deploy
    Run GitOps deploy script on VM:
    /home/ubuntu/ai-automation-stack/scripts/gitops-deploy.sh

  backup
    Create config + DB backups on VM and list latest artifacts.

  dr-backup
    Create VM config + DB backups, copy them to local `.dr-backups/`,
    and write a dated restore manifest in `ops/dr-manifests/`.

  restart <service>
    Restart one allowed service container.
    Allowed: caddy n8n n8n-worker openclaw chromium portainer redis db toolbox

  logs <service> [minutes]
    Show recent logs for one allowed service. Default minutes: 30.

  ps
    Show docker compose ps for the 3-file stack.

  deploy-dev
    Start or update the dev stack (automation-dev project) on VM.

  ps-dev
    Show docker compose ps for the dev stack.

  check-external
    Run endpoint checks from local machine (n8n/openclaw/portainer).
EOF
}

compose_ps_cmd="cd ${VM_DIR}; docker compose -f docker-compose.yml -f docker-compose.chromium-native.yml -f docker-compose.chromium-ip.yml ps"

service_to_container() {
  case "${1:?}" in
    caddy) printf "automation-caddy-1" ;;
    n8n) printf "automation-n8n-1" ;;
    n8n-worker) printf "automation-n8n-worker-1" ;;
    openclaw) printf "automation-openclaw-1" ;;
    chromium) printf "automation-chromium-1" ;;
    portainer) printf "automation-portainer-1" ;;
    redis) printf "automation-redis-1" ;;
    db) printf "automation-db-1" ;;
    toolbox) printf "automation-toolbox-1" ;;
    *)
      say "ERROR: service '${1}' is not in the allowlist."
      exit 1
      ;;
  esac
}

run_vm_cmd() {
  local description="${1:?}"
  local cmd="${2:?}"
  say "Action: ${description}"
  say "Host:   ${VM_HOST}"
  say "Cmd:    ${cmd}"
  if ! confirm "Approve this VM action?"; then
    say "Skipped."
    exit 0
  fi
  # SC2029: cmd string is intentionally built and expanded client-side
  # shellcheck disable=SC2029
  ssh "${VM_HOST}" "${cmd}"
}

action="${1:-}"
if [[ -z "${action}" ]]; then
  usage
  exit 1
fi
shift || true

case "${action}" in
  health)
    run_vm_cmd \
      "VM health (compose ps + recent logs)" \
      "set -euo pipefail; ${compose_ps_cmd}; echo; docker logs --since 30m --tail 80 automation-caddy-1 || true; docker logs --since 30m --tail 80 automation-n8n-1 || true; docker logs --since 30m --tail 80 automation-openclaw-1 || true; docker logs --since 30m --tail 80 automation-chromium-1 || true; docker logs --since 30m --tail 80 automation-portainer-1 || true"
    ;;
  deploy)
    run_vm_cmd \
      "GitOps deploy on VM" \
      "set -euo pipefail; ${VM_REPO_DIR}/scripts/gitops-deploy.sh"
    ;;
  backup)
    run_vm_cmd \
      "Create config + DB backups on VM" \
      "set -euo pipefail; cd /home/ubuntu; sudo tar czf automation-full-\$(date +%F-%H%M).tar.gz automation; docker run --rm -v automation_db_storage:/data -v /home/ubuntu:/backup busybox tar czf /backup/automation-db-\$(date +%F-%H%M).tar.gz /data; ls -lh /home/ubuntu/automation-full-*.tar.gz /home/ubuntu/automation-db-*.tar.gz | tail -n 6"
    ;;
  dr-backup)
    ts="$(date +%F-%H%M%S)"
    remote_cfg="/home/ubuntu/automation-full-${ts}.tar.gz"
    remote_db="/home/ubuntu/automation-db-${ts}.tar.gz"
    local_cfg="${LOCAL_DR_DIR}/automation-full-${ts}.tar.gz"
    local_db="${LOCAL_DR_DIR}/automation-db-${ts}.tar.gz"
    manifest_dir="${repo_root}/ops/dr-manifests"
    manifest="${manifest_dir}/dr-backup-${ts}.md"

    say "Action: disaster-recovery backup (VM + local copy + manifest)"
    say "Host:   ${VM_HOST}"
    say "Create: ${remote_cfg}"
    say "Create: ${remote_db}"
    say "Local:  ${LOCAL_DR_DIR}"
    if ! confirm "Approve this DR backup action?"; then
      say "Skipped."
      exit 0
    fi

    mkdir -p "${LOCAL_DR_DIR}" "${manifest_dir}"

    # SC2029: remote_cfg/remote_db are intentionally expanded client-side (desired behavior)
    # shellcheck disable=SC2029
    ssh "${VM_HOST}" "set -euo pipefail; cd /home/ubuntu; sudo tar czf ${remote_cfg} automation; docker run --rm -v automation_db_storage:/data -v /home/ubuntu:/backup busybox tar czf ${remote_db} /data; ls -lh ${remote_cfg} ${remote_db}; sha256sum ${remote_cfg} ${remote_db}"

    rsync -avz "${VM_HOST}:${remote_cfg}" "${local_cfg}"
    rsync -avz "${VM_HOST}:${remote_db}" "${local_db}"

    cfg_sum="$(shasum -a 256 "${local_cfg}" | awk '{print $1}')"
    db_sum="$(shasum -a 256 "${local_db}" | awk '{print $1}')"

    cat > "${manifest}" <<EOF
# DR Backup Manifest - ${ts}

## Backup Artifacts
- VM config backup: \`${remote_cfg}\`
- VM DB backup: \`${remote_db}\`
- Local config backup: \`${local_cfg}\`
- Local DB backup: \`${local_db}\`

## Checksums (SHA256, local copies)
- \`${cfg_sum}\`  \`$(basename "${local_cfg}")\`
- \`${db_sum}\`  \`$(basename "${local_db}")\`

## Restore Notes
1. Recreate VM and clone repo to \`/home/ubuntu/ai-automation-stack\`.
2. Recreate symlink: \`/home/ubuntu/automation -> /home/ubuntu/ai-automation-stack/automation\`.
3. Restore \`.env\` and runtime config (\`openclaw/config.json\`).
4. Restore DB volume from \`$(basename "${local_db}")\`.
5. Run GitOps deploy: \`/home/ubuntu/ai-automation-stack/scripts/gitops-deploy.sh\`.
EOF

    say "DR backup complete."
    say "Manifest: ${manifest}"
    ;;
  restart)
    svc="${1:-}"
    if [[ -z "${svc}" ]]; then
      say "ERROR: restart requires a service name."
      usage
      exit 1
    fi
    container="$(service_to_container "${svc}")"
    run_vm_cmd \
      "Restart service ${svc}" \
      "set -euo pipefail; docker restart ${container}; ${compose_ps_cmd}"
    ;;
  logs)
    svc="${1:-}"
    mins="${2:-30}"
    if [[ -z "${svc}" ]]; then
      say "ERROR: logs requires a service name."
      usage
      exit 1
    fi
    if ! [[ "${mins}" =~ ^[0-9]+$ ]]; then
      say "ERROR: minutes must be an integer."
      exit 1
    fi
    container="$(service_to_container "${svc}")"
    run_vm_cmd \
      "Show recent logs for ${svc} (${mins}m)" \
      "set -euo pipefail; docker logs --since ${mins}m --tail 200 ${container}"
    ;;
  ps)
    run_vm_cmd \
      "VM docker compose ps" \
      "set -euo pipefail; ${compose_ps_cmd}"
    ;;
  check-external)
    say "Action: external endpoint checks from local machine"
    if ! confirm "Approve this local action?"; then
      say "Skipped."
      exit 0
    fi
    curl -I https://n8n.satoic.com
    curl -I https://openclaw.satoic.com
    curl -I https://portainer.satoic.com
    ;;
  deploy-dev)
    run_vm_cmd \
      "Start/update dev stack on VM (automation-dev project)" \
      "set -euo pipefail; cd ${VM_DIR}; docker compose -f docker-compose.yml -f docker-compose.chromium-native.yml -f docker-compose.chromium-ip.yml -f docker-compose.dev.yml --project-name automation-dev up -d"
    ;;
  ps-dev)
    run_vm_cmd \
      "VM docker compose ps (dev stack)" \
      "set -euo pipefail; cd ${VM_DIR}; docker compose -f docker-compose.yml -f docker-compose.chromium-native.yml -f docker-compose.chromium-ip.yml -f docker-compose.dev.yml --project-name automation-dev ps"
    ;;
  -h|--help|help)
    usage
    ;;
  *)
    say "ERROR: unknown action '${action}'."
    usage
    exit 1
    ;;
esac
