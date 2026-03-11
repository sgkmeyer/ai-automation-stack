#!/usr/bin/env bash
# Test memory-api health and basic operations.
# Works against the local stack by default.
# For the VM dev lane, set MEMORY_STACK=dev and MEMORY_REMOTE_HOST=<ssh-host>.
# Usage: ./scripts/test-memory-api.sh [MEMORY_API_TOKEN]

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
stack="${MEMORY_STACK:-local}"
remote_host="${MEMORY_REMOTE_HOST:-}"
remote_repo_root="${MEMORY_REMOTE_REPO_ROOT:-/home/ubuntu/ai-automation-stack}"

if [[ "${stack}" == "dev" ]]; then
    if [[ -n "${remote_host}" ]]; then
        compose_args=(
            --env-file automation/.env
            -f automation/docker-compose.yml
            -f automation/docker-compose.chromium-native.yml
            -f automation/docker-compose.chromium-ip.yml
            -f automation/docker-compose.dev.yml
            --project-name automation-dev
        )
    else
        compose_args=(
            -f "${repo_root}/automation/docker-compose.yml"
            -f "${repo_root}/automation/docker-compose.chromium-native.yml"
            -f "${repo_root}/automation/docker-compose.chromium-ip.yml"
            -f "${repo_root}/automation/docker-compose.dev.yml"
            --project-name automation-dev
        )
    fi
else
    compose_args=(-f "${repo_root}/automation/docker-compose.yml")
fi

if [[ -z "${remote_host}" && -f "${repo_root}/automation/.env" ]]; then
    compose_args=(--env-file "${repo_root}/automation/.env" "${compose_args[@]}")
fi

TOKEN="${1:-${MEMORY_API_TOKEN:-changeme}}"

run_memory_api_exec() {
    local python_snippet="${1:?}"
    if [[ -n "${remote_host}" ]]; then
        local quoted
        printf -v quoted "%q" "${python_snippet}"
        ssh "${remote_host}" "cd ${remote_repo_root} && docker compose ${compose_args[*]} exec -T memory-api python -c ${quoted}"
    else
        docker compose "${compose_args[@]}" exec memory-api python -c "${python_snippet}"
    fi
}

echo "=== Health Check ==="
run_memory_api_exec "
import json
import urllib.request
resp = urllib.request.urlopen('http://localhost:8100/health')
print(json.dumps(json.loads(resp.read()), indent=2))
"

echo ""
echo "=== Log Entry ==="
run_memory_api_exec "
import json
import urllib.request
data = json.dumps({
    'text': 'Had a call with Sarah at Databricks. They are hiring a VP Sales, 80M ARR, series D. She is sending the JD tomorrow.',
    'source': 'tars'
}).encode()
req = urllib.request.Request(
    'http://localhost:8100/log',
    data=data,
    headers={'Authorization': 'Bearer ${TOKEN}', 'Content-Type': 'application/json'}
)
resp = urllib.request.urlopen(req)
print(json.dumps(json.loads(resp.read()), indent=2))
"

echo ""
echo "=== Recall ==="
run_memory_api_exec "
import json
import urllib.request
data = json.dumps({
    'query': 'Databricks',
    'synthesize': False
}).encode()
req = urllib.request.Request(
    'http://localhost:8100/recall',
    data=data,
    headers={'Authorization': 'Bearer ${TOKEN}', 'Content-Type': 'application/json'}
)
resp = urllib.request.urlopen(req)
print(json.dumps(json.loads(resp.read()), indent=2))
"

echo ""
echo "=== Context Write ==="
run_memory_api_exec "
import json
import urllib.request
data = json.dumps({
    'key': 'status',
    'value': 'Actively interviewing. Targeting VP Sales roles at 50-120M ARR SaaS companies.'
}).encode()
req = urllib.request.Request(
    'http://localhost:8100/context/job_search',
    data=data,
    method='PUT',
    headers={'Authorization': 'Bearer ${TOKEN}', 'Content-Type': 'application/json'}
)
resp = urllib.request.urlopen(req)
print(json.dumps(json.loads(resp.read()), indent=2))
"

echo ""
echo "=== Context Read ==="
run_memory_api_exec "
import json
import urllib.request
req = urllib.request.Request(
    'http://localhost:8100/context',
    headers={'Authorization': 'Bearer ${TOKEN}'}
)
resp = urllib.request.urlopen(req)
print(json.dumps(json.loads(resp.read()), indent=2))
"

echo ""
echo "=== All tests passed ==="
