#!/usr/bin/env bash
# Test memory-api health and basic operations.
# Works against the local stack by default and the dev lane with MEMORY_STACK=dev.
# Usage: ./scripts/test-memory-api.sh [MEMORY_API_TOKEN]

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
stack="${MEMORY_STACK:-local}"

if [[ "${stack}" == "dev" ]]; then
    compose_args=(
        -f "${repo_root}/automation/docker-compose.yml"
        -f "${repo_root}/automation/docker-compose.chromium-native.yml"
        -f "${repo_root}/automation/docker-compose.chromium-ip.yml"
        -f "${repo_root}/automation/docker-compose.dev.yml"
        --project-name automation-dev
    )
else
    compose_args=(-f "${repo_root}/automation/docker-compose.yml")
fi

if [[ -f "${repo_root}/automation/.env" ]]; then
    compose_args=(--env-file "${repo_root}/automation/.env" "${compose_args[@]}")
fi

TOKEN="${1:-${MEMORY_API_TOKEN:-changeme}}"

echo "=== Health Check ==="
docker compose "${compose_args[@]}" exec memory-api \
    python -c "
import json
import urllib.request
resp = urllib.request.urlopen('http://localhost:8100/health')
print(json.dumps(json.loads(resp.read()), indent=2))
"

echo ""
echo "=== Log Entry ==="
docker compose "${compose_args[@]}" exec memory-api \
    python -c "
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
docker compose "${compose_args[@]}" exec memory-api \
    python -c "
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
docker compose "${compose_args[@]}" exec memory-api \
    python -c "
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
docker compose "${compose_args[@]}" exec memory-api \
    python -c "
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
