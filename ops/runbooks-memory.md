# Memory Layer Runbooks

## Apply Schema to Existing Database

Postgres only runs init scripts on a fresh data volume. For an existing deployment:

```bash
cd /path/to/ai-automation-stack

cat sql/010_memory_extensions.sql \
    sql/011_memory_schema.sql \
    sql/012_memory_views.sql \
  | docker compose --env-file automation/.env -f automation/docker-compose.yml exec -T db \
    psql -U $POSTGRES_USER -d $POSTGRES_DB
```

## Build and Start memory-api

```bash
cd /path/to/ai-automation-stack
docker compose --env-file automation/.env -f automation/docker-compose.yml build memory-api
docker compose --env-file automation/.env -f automation/docker-compose.yml up -d memory-api
```

## Verify Health

```bash
docker compose --env-file automation/.env -f automation/docker-compose.yml exec memory-api \
    python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8100/health').read().decode())"
```

## Run Smoke Tests

```bash
./scripts/test-memory-api.sh $MEMORY_API_TOKEN
```

## Apply Week 2 Ingest Upgrade

For an existing deployment, apply the Week 2 migration as well:

```bash
cat sql/013_memory_ingest.sql \
  | docker compose -f automation/docker-compose.yml exec -T db \
    psql -U $POSTGRES_USER -d $POSTGRES_DB
```

## Manual Obsidian Ingest Check

```bash
docker compose -f automation/docker-compose.yml exec memory-api \
  python - <<'PY'
import json
import urllib.request

req = urllib.request.Request(
    "http://localhost:8100/ingest/document",
    data=json.dumps({
        "source": "obsidian",
        "source_ref": "Daily/2026-03-11.md",
        "source_type": "md",
        "title": "2026-03-11",
        "content": "Met Sam for coffee and captured next steps.",
        "tags": ["daily-note"]
    }).encode(),
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {__import__('os').environ['MEMORY_API_TOKEN']}",
    },
    method="POST",
)
print(urllib.request.urlopen(req).read().decode())
PY
```

## Manual Transcript Ingest Check

```bash
docker compose -f automation/docker-compose.yml exec memory-api \
  python - <<'PY'
import json
import urllib.request

req = urllib.request.Request(
    "http://localhost:8100/ingest/transcript",
    data=json.dumps({
        "source_ref": "krisp:demo-meeting",
        "title": "Demo Meeting",
        "transcript_text": "We agreed to send the proposal tomorrow.",
        "action_items": ["Send the proposal tomorrow"]
    }).encode(),
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {__import__('os').environ['MEMORY_API_TOKEN']}",
    },
    method="POST",
)
print(urllib.request.urlopen(req).read().decode())
PY
```

## Reset Memory

```bash
docker compose --env-file automation/.env -f automation/docker-compose.yml exec db \
    psql -U $POSTGRES_USER -d $POSTGRES_DB \
    -c "DROP SCHEMA IF EXISTS memory CASCADE;"
```

Then re-apply the schema scripts.

## Backup Memory Data

Memory data lives in the same Postgres volume as n8n data, so the existing
backup procedures already cover it.
