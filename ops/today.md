# Today — Current Build State

> Manually maintained. Update at the end of each session alongside the dated session log.
> Last updated: 2026-02-19

---

## What Is Live and Healthy

**Production stack** (`automation` project on Oracle Free Tier VM):
- All 9 services up: caddy, db, redis, n8n, n8n-worker, openclaw, chromium, portainer, toolbox
- Public endpoints:
  - `https://n8n.satoic.com` → 200 (app auth)
  - `https://openclaw.satoic.com` → 401 pre-auth (expected)
  - `https://portainer.satoic.com` → 401 pre-auth (expected)
- GitOps deploy active: push to `main` → SSH → `gitops-deploy.sh`
- Openclaw paired to Telegram (`@sg_tar_bot`), n8n API wired, Chromium CDP connected

**VM layout:**
- Repo: `/home/ubuntu/ai-automation-stack` (cloned from GitHub)
- Runtime symlink: `/home/ubuntu/automation → /home/ubuntu/ai-automation-stack/automation`
- Stack path on VM: `/home/ubuntu/automation`

---

## Active Priorities (this session)

- [x] Phase 0: Git snapshot + DR backup
- [x] Phase 1: CLAUDE.md, ops/today.md, verify.sh, backup.sh
- [x] Phase 2: Dev/prod lanes (docker-compose.dev.yml, Caddyfile.dev, vm-safe.sh)
- [x] Phase 3: Tailscale — VM IP: 100.82.169.113, hostname: satoic-production
- [x] Phase 4: GitHub CI/CD (.github/workflows/) — needs GitHub secrets + branch protection

---

## Backup & Recovery Model

### Current state (Tailscale live)

`./scripts/backup.sh` from the Mac works end-to-end:
SSH → VM backup → rsync artifacts to `.dr-backups/` locally → write manifest in `ops/dr-manifests/`.

**Always run from local Mac, never from the VM.** Scripts SSH outward to `satoic-vm`.

**VM-local fallback** (if Mac-side scripts unavailable — e.g., SSH session directly on VM):
```bash
cd /home/ubuntu
sudo tar czf automation-full-$(date +%F-%H%M).tar.gz automation
docker run --rm \
  -v automation_db_storage:/data \
  -v /home/ubuntu:/backup \
  busybox tar czf /backup/automation-db-$(date +%F-%H%M).tar.gz /data
ls -lh /home/ubuntu/automation-full-*.tar.gz /home/ubuntu/automation-db-*.tar.gz | tail -n 4
```

---

## Open Items / Known Risks

- **GitHub CI/CD needs 3 secrets + branch protection** — see below
- **Dev stack not yet started on VM** — run `./scripts/vm-safe.sh deploy-dev` to bring it up
- **`scripts/backup.sh` / `vm-safe.sh dr-backup` only work from local Mac** — do not suggest running these on the VM (see Backup & Recovery Model above)
- **Gateway token mismatch** — `automation/.env` OPENCLAW_GATEWAY_TOKEN differs from `automation/openclaw/config.json` token; verify which is active and rotate if needed
- **Placeholder secrets in .env** — `POSTGRES_PASSWORD` and `N8N_ENCRYPTION_KEY` still use example-looking values; rotate before any production use
- **Pre-GitOps VM backup** — `/home/ubuntu/automation.pre-gitops-2026-02-16-2147` still on VM; safe to remove after one more healthy day
- **Workflow #1 not yet built** — Openclaw → n8n → Postgres leads pipeline (next build priority after env upgrades)

---

## How to Update This File

At the end of each session:
1. Check off completed items
2. Add any new open items or risks discovered
3. Update "What Is Live and Healthy" if the stack state changed
4. Also fill in the dated `ops/SESSION-YYYY-MM-DD.md` for the detailed log
