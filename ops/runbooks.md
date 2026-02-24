# Satoic Automation Platform Runbooks

## Locations
- VM stack directory: `/home/ubuntu/automation`
- Local mirror directory: `/Users/sgkmeyer/ai-automation-stack/automation`

## Tailscale Network
- VM Tailscale IP: `100.82.169.113`
- VM Tailscale hostname: `satoic-production`
- SSH via Tailscale: `ssh ubuntu@100.82.169.113` or use the `satoic-production` alias (see below)

### SSH config (`~/.ssh/config`)
```
# Primary: route satoic-production through Tailscale (works from anywhere on the mesh)
Host satoic-production
  HostName 100.82.169.113
  User ubuntu

# Canonical Tailscale alias
Host satoic-production
  HostName 100.82.169.113
  User ubuntu
```

### Dev stack access (post-Tailscale)
- Dev n8n UI: `http://100.82.169.113:5679`
- Full Mac-side backup: `./scripts/backup.sh` (SSH + rsync + manifest)

## Core Operations
### Start or update stack
```bash
cd /home/ubuntu/automation
docker compose \
  -f docker-compose.yml \
  -f docker-compose.chromium-native.yml \
  -f docker-compose.chromium-ip.yml \
  up -d
```

### Stop stack
```bash
cd /home/ubuntu/automation
docker compose \
  -f docker-compose.yml \
  -f docker-compose.chromium-native.yml \
  -f docker-compose.chromium-ip.yml \
  down
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
docker compose \
  -f docker-compose.yml \
  -f docker-compose.chromium-native.yml \
  -f docker-compose.chromium-ip.yml \
  ps
docker logs --tail 80 automation-caddy-1
docker logs --tail 80 automation-n8n-1
docker logs --tail 80 automation-openclaw-1
docker logs --tail 80 automation-chromium-1
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
### Config backup (full, includes protected files)
```bash
cd /home/ubuntu
sudo tar czf automation-full-$(date +%F-%H%M).tar.gz automation
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
ls -lh /home/ubuntu/automation-full-*.tar.gz /home/ubuntu/automation-db-*.tar.gz
```

### Runtime log snapshots
```bash
cd /home/ubuntu/automation
mkdir -p /home/ubuntu/automation/ops
docker logs --tail 80 automation-openclaw-1 2>&1 | sudo tee /home/ubuntu/automation/ops/openclaw-log-snapshot.txt >/dev/null
docker logs --tail 80 automation-chromium-1 2>&1 | sudo tee /home/ubuntu/automation/ops/chromium-log-snapshot.txt >/dev/null
```

## Sync Workflow
From laptop:
```bash
cd /Users/sgkmeyer/ai-automation-stack
./scripts/sync-from-vm.sh
./scripts/sync-to-vm.sh
```

## GitOps Deployment (Preferred)
Goal: make the VM pull from GitHub and apply the stack from the repo checkout (single source of truth).

### One-time VM setup
1. Ensure repo exists on VM at `/home/ubuntu/ai-automation-stack` and has an SSH remote to GitHub.
2. Ensure the stack directory `/home/ubuntu/automation` points at the repo's `automation/` folder:
   - Recommended: symlink `/home/ubuntu/automation` -> `/home/ubuntu/ai-automation-stack/automation`
3. Ensure required untracked secrets/config exist on VM (not in Git):
   - `/home/ubuntu/automation/.env`
   - `/home/ubuntu/automation/openclaw/config.json`
   - other Openclaw runtime folders (`credentials/`, `telegram/`, etc.)

### Deploy
From laptop:
```bash
ssh satoic-production /home/ubuntu/ai-automation-stack/scripts/gitops-deploy.sh
```

### Guarded VM Operations (Recommended)
Use the local wrapper for explicit, approved VM actions:
```bash
cd /Users/sgkmeyer/ai-automation-stack
./scripts/vm-safe.sh health
./scripts/vm-safe.sh deploy
./scripts/vm-safe.sh backup
./scripts/vm-safe.sh dr-backup
./scripts/vm-safe.sh restart openclaw
./scripts/vm-safe.sh logs openclaw 30
./scripts/vm-safe.sh ps
./scripts/vm-safe.sh check-external
```
Notes:
- Every action prints the exact command and requires explicit approval.
- Actions are restricted to an allowlist to reduce accidental destructive changes.
- For non-interactive runs, pass `--yes` (only for trusted contexts).
- `dr-backup` creates VM archives, copies them to local `.dr-backups/`, and writes `ops/dr-manifests/dr-backup-*.md`.

## Session Handoff Workflow
At end of each work session:
1. Copy `ops/SESSION-TEMPLATE.md` to `ops/SESSION-YYYY-MM-DD.md`.
2. Fill in scope, changes, validations, risks, and next steps.
3. Update the "latest session handoff summary" pointer in `README.md`.

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

### Openclaw browser tool fails
1. Confirm Openclaw can reach n8n and Chromium:
```bash
docker exec -i automation-openclaw-1 sh -lc 'node -e "fetch(\"http://n8n:5678/healthz\").then(r=>r.text()).then(t=>console.log(t.slice(0,120))).catch(e=>{console.error(e);process.exit(1)})"'
docker exec -i automation-openclaw-1 sh -lc 'node -e "fetch(\"http://172.30.0.10:9222/json/version\").then(r=>r.text()).then(t=>console.log(t.slice(0,120))).catch(e=>{console.error(e);process.exit(1)})"'
```
2. Confirm CDP URL:
```bash
docker exec -i automation-openclaw-1 sh -lc 'node dist/index.js config get browser.cdpUrl'
```
Expected value:
`http://172.30.0.10:9222`
