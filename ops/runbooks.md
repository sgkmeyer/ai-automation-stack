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
- Dev lane runs with Caddy scaled to `0` to avoid host port conflicts (`80/443`) with production Caddy.

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
- `openclaw.satoic.com`: `200` (gateway token auth flow)
- `portainer.satoic.com`: `401` before basic auth

## Backup & Recovery

### What gets backed up

| Archive | Contents | Why it matters |
|---------|----------|----------------|
| `automation-full-*.tar.gz` | `.env`, Caddyfile, compose files, Dockerfile, Openclaw config/credentials/telegram/devices | Secrets + app config (can't be recovered from git) |
| `automation-db-*.tar.gz` | Postgres data volume (n8n workflows, encrypted credentials, leads table, execution history) | All application state |

**Critical dependency:** n8n credentials (Gmail, Google Drive, HubSpot OAuth tokens) are encrypted
in Postgres using `N8N_ENCRYPTION_KEY`. The DB backup is only useful if you also have the matching
encryption key from `.env`. Both archives are needed for a full restore.

### Automated backups (VM systemd timer)

Runs daily at **03:00 UTC** via `satoic-backup.timer`.
- Archives saved to `/home/ubuntu/backups/` on VM
- Retention: 7 days (auto-pruned)
- Log: `/home/ubuntu/backups/cron-backup.log`
- Script: `scripts/vm-cron-backup.sh`

```bash
# Check timer status
sudo systemctl status satoic-backup.timer

# View last run
sudo systemctl status satoic-backup.service

# View backup log
cat /home/ubuntu/backups/cron-backup.log

# Manual trigger
sudo systemctl start satoic-backup.service

# List backups
ls -lh /home/ubuntu/backups/
```

### On-demand backup (from Mac)

Full DR backup with local copy + manifest:
```bash
./scripts/backup.sh
# — or —
./scripts/vm-safe.sh dr-backup
```

This SSHs to the VM, creates both archives, rsyncs them to `.dr-backups/` on your Mac,
and writes a manifest to `ops/dr-manifests/`. **Always run from your Mac, never from the VM.**

### Manual backup (on VM directly)

If Mac is unavailable (e.g., SSH session directly on VM):
```bash
cd /home/ubuntu
sudo tar -hczf automation-full-$(date +%F-%H%M).tar.gz automation
docker run --rm \
  -v automation_db_storage:/data \
  -v /home/ubuntu:/backup \
  busybox tar czf /backup/automation-db-$(date +%F-%H%M).tar.gz /data
ls -lh /home/ubuntu/automation-full-*.tar.gz /home/ubuntu/automation-db-*.tar.gz | tail -n 4
```

### Restore to existing VM

```bash
sudo /home/ubuntu/ai-automation-stack/scripts/restore.sh \
  /home/ubuntu/backups/automation-full-YYYY-MM-DD.tar.gz \
  /home/ubuntu/backups/automation-db-YYYY-MM-DD.tar.gz
```

This stops the stack, restores secrets/config + Postgres volume, then gives next steps.

### Full disaster recovery (new VPS from scratch)

If the VM is gone and you need to stand up a replacement:

1. **Provision a new VM** (Ubuntu 22.04+, arm64 or amd64)
2. **Copy bootstrap script** to the new VM and run it:
   ```bash
   scp scripts/bootstrap-vm.sh ubuntu@<new-vm-ip>:/tmp/
   ssh ubuntu@<new-vm-ip> 'sudo bash /tmp/bootstrap-vm.sh'
   ```
3. **Copy DR backup archives** to the new VM:
   ```bash
   scp .dr-backups/automation-full-*.tar.gz .dr-backups/automation-db-*.tar.gz ubuntu@<new-vm-ip>:/home/ubuntu/backups/
   ```
4. **Run restore**:
   ```bash
   ssh ubuntu@<new-vm-ip>
   sudo /home/ubuntu/ai-automation-stack/scripts/restore.sh \
     /home/ubuntu/backups/automation-full-YYYY-MM-DD.tar.gz \
     /home/ubuntu/backups/automation-db-YYYY-MM-DD.tar.gz
   ```
5. **Authenticate Tailscale**: `sudo tailscale up`
6. **Deploy the stack**: `sudo -u ubuntu /home/ubuntu/ai-automation-stack/scripts/gitops-deploy.sh`
7. **Update DNS** if the VM's public IP changed (point `*.satoic.com` to new IP)
8. **Update GitHub secrets** if the VM's Tailscale IP or host keys changed:
   - `VM_TAILSCALE_HOST`
   - `VM_SSH_KNOWN_HOSTS`
   - `VM_SSH_PRIVATE_KEY` (if new CI key generated)
9. **Verify endpoints**:
   ```bash
   curl -I https://n8n.satoic.com
   curl -I https://openclaw.satoic.com
   curl -I https://portainer.satoic.com
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
Notes:
- `sync-to-vm.sh` now runs a `--dry-run` preview and asks for confirmation before applying `--delete`.
- Use `./scripts/sync-to-vm.sh --yes` only in trusted automation contexts.

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
4. Ensure GitHub Actions secret `VM_SSH_KNOWN_HOSTS` is set with the VM host key line(s).

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
./scripts/verify.sh
./scripts/verify-memory-webhook.sh
```
Notes:
- Every action prints the exact command and requires explicit approval.
- Actions are restricted to an allowlist to reduce accidental destructive changes.
- For non-interactive runs, pass `--yes` (only for trusted contexts).
- `check-external` and `verify.sh` enforce the public smoke contract: `n8n=200`, `openclaw=200`, `portainer=401`, with retries.
- `verify-memory-webhook.sh` exercises the live `memory/context` webhook using a dedicated smoke-only key and cleans it up afterward.
- `dr-backup` creates VM archives, copies them to local `.dr-backups/`, and writes `ops/dr-manifests/dr-backup-*.md`.
- `deploy-dev` is safe against Caddy port collisions (runs dev compose with `--scale caddy=0`).

### GitHub Actions Notes
- `Deploy to Dev` / `Deploy to Production` currently use Tailscale authkey mode and may show a deprecation warning.
- Planned cleanup: migrate `tailscale/github-action` to OAuth client credentials.

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
### Openclaw disconnected after upgrade / container recreation
This is a known recurring issue. When the Openclaw container is recreated (e.g., during
`docker compose up -d`), volume file ownership can break if the image's `node` UID changes,
and browser-side tokens (device + gateway) are invalidated.

**Symptoms (in order of appearance):**
1. `device_token_mismatch` — browser's cached device token doesn't match container state
2. `gateway token missing` — clearing browser storage to fix #1 also wipes the gateway token
3. `pairing required` — new browser origin needs device pairing approval

**Fix procedure:**

1. **Fix file ownership** (root cause — UID mismatch on volume):
```bash
ssh satoic-production "docker exec -u root automation-openclaw-1 chown -R node:node /home/node/.openclaw"
```

2. **Restart Openclaw:**
```bash
ssh satoic-production "cd /home/ubuntu/automation && docker compose -f docker-compose.yml -f docker-compose.chromium-native.yml -f docker-compose.chromium-ip.yml restart openclaw"
```

3. **Re-inject gateway token into browser** via SSH tunnel:
```bash
# From Mac — create tunnel
ssh -N -L 18789:$(ssh satoic-production "docker inspect automation-openclaw-1 --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' | head -1"):18789 satoic-production &

# Open in browser (token value from VM .env):
# http://localhost:18789/#token=<OPENCLAW_GATEWAY_TOKEN>
```

4. **Approve device pairing** (run after "pairing required" appears):
```bash
ssh satoic-production 'docker exec automation-openclaw-1 node -e "
const fs = require(\"fs\");
const paired = JSON.parse(fs.readFileSync(\"/home/node/.openclaw/devices/paired.json\", \"utf8\"));
const pending = JSON.parse(fs.readFileSync(\"/home/node/.openclaw/devices/pending.json\", \"utf8\"));
for (const [id, req] of Object.entries(pending)) {
  const now = Date.now();
  paired[req.deviceId] = {
    deviceId: req.deviceId, publicKey: req.publicKey, platform: req.platform,
    clientId: req.clientId, clientMode: req.clientMode, role: req.role,
    roles: req.roles, scopes: req.scopes,
    tokens: { operator: { token: require(\"crypto\").randomBytes(16).toString(\"hex\"),
      role: \"operator\", scopes: req.scopes, createdAtMs: now, lastUsedAtMs: now } },
    createdAtMs: now, approvedAtMs: now, remoteIp: req.remoteIp
  };
  delete pending[id];
  console.log(\"Approved:\", req.deviceId);
}
fs.writeFileSync(\"/home/node/.openclaw/devices/paired.json\", JSON.stringify(paired, null, 2));
fs.writeFileSync(\"/home/node/.openclaw/devices/pending.json\", JSON.stringify(pending, null, 2));
"'
```

5. **Reload Openclaw** (hot reload, no full restart):
```bash
ssh satoic-production "docker exec automation-openclaw-1 kill -USR1 1"
```

6. **Verify** by opening `https://openclaw.satoic.com` — should show Health Online.

7. **If accessing via Caddy**, you may need to repeat steps 3–5 for the `openclaw.satoic.com` origin (different browser local storage than `localhost`).

**Prevention:** The `gitops-deploy.sh` script automatically fixes `.openclaw` ownership after every deploy.

### Openclaw shows token missing in UI (legacy — simple case)
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
