# Satoic Automation Suite

This repository is the operational source of truth for the Satoic automation stack running on Oracle Free Tier.

## Stack
- Reverse proxy/TLS: Caddy
- Orchestration: n8n + n8n worker
- Queue/cache: Redis
- Database: PostgreSQL
- Agent gateway: Openclaw
- Browser runtime: Chromium CDP sidecar
- Container operations UI: Portainer

## Domains
- `https://n8n.satoic.com`
- `https://openclaw.satoic.com`
- `https://portainer.satoic.com`

## Repository Layout
- `/Users/sgkmeyer/ai-automation-stack/automation` runtime stack files mirrored from VM
- `/Users/sgkmeyer/ai-automation-stack/ops/runbooks.md` operational procedures
- `/Users/sgkmeyer/ai-automation-stack/ops/SESSION-2026-02-19.md` latest session handoff summary
- `/Users/sgkmeyer/ai-automation-stack/ops/SESSION-TEMPLATE.md` handoff template for new sessions
- `/Users/sgkmeyer/ai-automation-stack/scripts` sync/deploy utility scripts
- `/Users/sgkmeyer/ai-automation-stack/sql` schema scripts
- `/Users/sgkmeyer/ai-automation-stack/workflows` workflow design notes

## Daily Workflow
1. Pull current VM state:
```bash
cd /Users/sgkmeyer/ai-automation-stack
./scripts/sync-from-vm.sh
```

2. Make controlled changes locally.

3. Push approved changes to VM:
```bash
./scripts/sync-to-vm.sh
```

4. Apply/reload on VM as needed:
```bash
cd /home/ubuntu/automation
docker compose \
  -f docker-compose.yml \
  -f docker-compose.chromium-native.yml \
  -f docker-compose.chromium-ip.yml \
  up -d
docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile
```

## Current Auth Model
- `n8n.satoic.com`: n8n native app authentication
- `openclaw.satoic.com`: Caddy basic auth + Openclaw gateway token
- `portainer.satoic.com`: Caddy basic auth + Portainer native admin auth

## Notes
- Keep secrets out of Git.
- Treat Docker Compose and Caddy files as source of truth.
- Use Portainer for observability/operations, not as the primary config authoring surface.
