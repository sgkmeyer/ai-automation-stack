# Memory Dev-Lane Rollout

## Purpose

Run the Week 1 memory layer through the repo's required dev-first path before any production promotion.

## Prerequisites

- `automation/.env` on the VM includes:
  - `MEMORY_API_TOKEN`
  - `MEMORY_LLM_PROVIDER`
  - `MEMORY_LLM_API_KEY` (optional)
  - `MEMORY_LLM_MODEL`
- Code is committed on a branch that will be promoted to `dev`
- Local repo already passed static validation and local smoke checks

## Rollout Sequence

1. Commit the memory-layer changes.
2. Push the branch to `dev`.
3. Wait for the dev deploy workflow to complete, or run:

```bash
./scripts/vm-safe.sh deploy-dev
```

4. On the VM, verify the dev stack includes `memory-api`:

```bash
cd /home/ubuntu/ai-automation-stack/automation
docker compose \
  -f docker-compose.yml \
  -f docker-compose.chromium-native.yml \
  -f docker-compose.chromium-ip.yml \
  -f docker-compose.dev.yml \
  --project-name automation-dev \
  ps
```

5. Apply the memory schema to the dev database:

```bash
cd /home/ubuntu/ai-automation-stack
cat sql/010_memory_extensions.sql \
    sql/011_memory_schema.sql \
    sql/012_memory_views.sql \
  | docker compose --env-file automation/.env \
      -f automation/docker-compose.yml \
      -f automation/docker-compose.chromium-native.yml \
      -f automation/docker-compose.chromium-ip.yml \
      -f automation/docker-compose.dev.yml \
      --project-name automation-dev \
      exec -T db sh -lc 'psql -U "$POSTGRES_USER" -d "${POSTGRES_DB_DEV:-n8n_dev}"'
```

6. Verify health inside the dev service:

```bash
docker compose --env-file automation/.env \
  -f automation/docker-compose.yml \
  -f automation/docker-compose.chromium-native.yml \
  -f automation/docker-compose.chromium-ip.yml \
  -f automation/docker-compose.dev.yml \
  --project-name automation-dev \
  exec -T memory-api \
  python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8100/health').read().decode())"
```

7. Run the smoke test against the VM-backed dev lane:

```bash
MEMORY_STACK=dev \
MEMORY_REMOTE_HOST=satoic-production \
./scripts/test-memory-api.sh "$MEMORY_API_TOKEN"
```

8. Create the n8n header-auth credential for the workflow layer. Use the governed name exactly so workflow imports can resolve it by name:

```json
[
  {
    "id": "memory-api-header-auth",
    "name": "Memory API Header Auth",
    "type": "httpHeaderAuth",
    "data": {
      "name": "Authorization",
      "value": "Bearer REPLACE_WITH_MEMORY_API_TOKEN"
    }
  }
]
```

```bash
cd /home/ubuntu/automation
cat >/tmp/memory-api-header-auth.json <<'JSON'
[
  {
    "id": "memory-api-header-auth",
    "name": "Memory API Header Auth",
    "type": "httpHeaderAuth",
    "data": {
      "name": "Authorization",
      "value": "Bearer REPLACE_WITH_MEMORY_API_TOKEN"
    }
  }
]
JSON

docker compose \
  -f docker-compose.yml \
  -f docker-compose.chromium-native.yml \
  -f docker-compose.chromium-ip.yml \
  -f docker-compose.dev.yml \
  --project-name automation-dev \
  exec -T n8n \
  n8n import:credentials --input=/tmp/memory-api-header-auth.json
```

9. Re-import the governed memory workflows after the credential exists. The governed workflow JSON references `Memory API Header Auth` by name; n8n resolves that to a concrete credential ID during import:

```bash
cd /home/ubuntu/ai-automation-stack
for wf in \
  workflows/governed/mem-01-memory-log-command/workflow.json \
  workflows/governed/mem-02-memory-recall-command/workflow.json \
  workflows/governed/mem-03-memory-context-command/workflow.json
do
  docker compose --env-file automation/.env \
    -f automation/docker-compose.yml \
    -f automation/docker-compose.chromium-native.yml \
    -f automation/docker-compose.chromium-ip.yml \
    -f automation/docker-compose.dev.yml \
    --project-name automation-dev \
    exec -T n8n sh -lc "cat >/tmp/workflow.json && n8n import:workflow --input=/tmp/workflow.json" < "$wf"
done

docker compose --env-file automation/.env \
  -f automation/docker-compose.yml \
  -f automation/docker-compose.chromium-native.yml \
  -f automation/docker-compose.chromium-ip.yml \
  -f automation/docker-compose.dev.yml \
  --project-name automation-dev \
  restart n8n n8n-webhook n8n-worker
```

10. Run workflow-layer checks against dev:

```bash
curl -sS -X POST https://dev.openclaw.satoic.com/webhook/memory/log \
  -H 'Content-Type: application/json' \
  -d '{"text":"Met Sam for coffee","source":"tars","tags":["relationship"]}'

curl -sS -X POST https://dev.openclaw.satoic.com/webhook/memory/recall \
  -H 'Content-Type: application/json' \
  -d '{"query":"coffee with Sam","limit":3,"synthesize":false}'

curl -sS -X POST https://dev.openclaw.satoic.com/webhook/memory/context \
  -H 'Content-Type: application/json' \
  -d '{"action":"set","domain":"prefs","key":"drink","value":"flat white"}'
```

## Acceptance Criteria

- `memory-api` is `Up` and healthy on the dev stack
- `/health` returns `schema=ready`
- `test-memory-api.sh` passes on `MEMORY_STACK=dev`
- `Memory API Header Auth` exists in dev n8n as an `httpHeaderAuth` credential
- all three memory workflows import with a resolved credential reference
- Auth failures return `401`/`403`
- Invalid `source` and `entry_type` return `422`
- `DELETE /context/...` returns `404` when the key is already gone

## Promotion Gate

Do not promote to production until:

- dev deploy is green
- dev smoke tests are green
- memory workflows pass command-level tests on dev with credential-backed auth
- required env vars are present on the VM
- the password-rotation follow-up from the local validation session is addressed
