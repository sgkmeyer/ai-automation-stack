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
