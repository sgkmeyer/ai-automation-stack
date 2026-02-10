# Satoic Automation Platform — Runbooks

## Start / Restart Stack
```bash
cd ~/automation
docker compose up -d
```

## Stop Stack
```bash
docker compose down
```

## Reload Caddy Config
```bash
docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile
```

## Health Checks
```bash
docker compose ps
docker compose logs n8n -f
docker compose logs n8n-worker -f
docker compose logs caddy -f
```

## Backup
Backup the full config directory and Docker volumes.

```bash
# Config
cd ~/automation
tar czf automation-config.tar.gz .

# Postgres data volume (example)
docker run --rm \
  -v automation_postgres_data:/data \
  -v $(pwd):/backup \
  busybox tar czf /backup/postgres-data.tar.gz /data
```

## Restore
```bash
cd ~/automation
# Restore config
# (extract automation-config.tar.gz into ~/automation)

docker compose up -d
```

## Firewall Ports
Ensure only the following are open at both UFW and OCI Security Lists:
- `22` (SSH)
- `80` (HTTP)
- `443` (HTTPS)

## Credential Rotation
- Update `BASIC_AUTH_HASH` in `.env` and reload Caddy.
- Update n8n user credentials inside the UI.
- Rotate external API keys used by workflows.
