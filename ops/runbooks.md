# Satoic Automation Platform Runbooks

## Locations
- VM stack directory: `/home/ubuntu/automation`
- Local mirror directory: `/Users/sgkmeyer/ai-automation-stack/automation`

## Core Operations
### Start or update stack
```bash
cd /home/ubuntu/automation
docker compose up -d
```

### Stop stack
```bash
cd /home/ubuntu/automation
docker compose down
```

### Restart one service
```bash
docker restart automation-openclaw-1
```

### Reload Caddy config
```bash
cd /home/ubuntu/automation
docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile
```

## Health Checks
```bash
cd /home/ubuntu/automation
docker compose ps
docker logs --tail 80 automation-caddy-1
docker logs --tail 80 automation-n8n-1
docker logs --tail 80 automation-openclaw-1
docker logs --tail 80 automation-portainer-1
```

## External Verification
From laptop:
```bash
curl -I https://n8n.satoic.com
curl -I https://openclaw.satoic.com
curl -I https://portainer.satoic.com
```
Expected:
- `n8n.satoic.com`: app-native auth flow
- `openclaw.satoic.com`: `401` before basic auth
- `portainer.satoic.com`: `401` before basic auth

## Backup
### Config backup
```bash
cd /home/ubuntu
sudo tar czf automation-config-$(date +%F-%H%M).tar.gz automation
```

### Postgres volume backup
```bash
docker run --rm \
  -v automation_db_storage:/data \
  -v /home/ubuntu:/backup \
  busybox tar czf /backup/automation-db-$(date +%F-%H%M).tar.gz /data
```

### Verify backup artifacts
```bash
ls -lh /home/ubuntu/automation-config-*.tar.gz /home/ubuntu/automation-db-*.tar.gz
```

## Sync Workflow
From laptop:
```bash
cd /Users/sgkmeyer/ai-automation-stack
./scripts/sync-from-vm.sh
./scripts/sync-to-vm.sh
```

## Credential Rotation
### Openclaw gateway token
1. Generate new token.
2. Update:
- `/home/ubuntu/automation/.env`
- `/home/ubuntu/automation/openclaw/config.json`
3. Recreate Openclaw container.
4. Verify token consistency in env, config, and runtime.

### Caddy basic auth
1. Generate new bcrypt hash.
2. Replace hash in `/home/ubuntu/automation/Caddyfile`.
3. Reload Caddy.

## Git Baseline Workflow
From laptop:
```bash
cd /Users/sgkmeyer/ai-automation-stack
git add .
git commit -m "chore: baseline update"
```

## Incident Quick Actions
### Openclaw shows token missing in UI
- Confirm gateway token exists in config and env.
- Recreate `automation-openclaw-1`.

### Portainer setup timeout screen
```bash
docker restart automation-portainer-1
```
Then immediately complete setup.

### n8n proxy/rate-limit warnings
- Ensure n8n reverse-proxy env settings are present in `docker-compose.yml`.
- Recreate `n8n` and `n8n-worker`.
