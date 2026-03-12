# Today — Current Build State

> Manually maintained. Update at the end of each session alongside the dated session log.
> Last updated: 2026-03-12

---

## What Is Live and Healthy

**Production stack** (`automation` project on Oracle Free Tier VM):
- All 11 services up: caddy, db, redis, n8n, n8n-worker, n8n-webhook, n8n-task-runner, openclaw, chromium, portainer, toolbox
- **Stack versions (updated 2026-03-11):** n8n 2.11.2, Openclaw 2026.3.8, Portainer CE lts, Caddy 2-alpine, Postgres 16-alpine, Redis 7-alpine, Python 3.12-slim
- Public endpoints:
  - `https://n8n.satoic.com` → 200 (app auth)
  - `https://openclaw.satoic.com` → 200 (gateway token auth only, no Caddy basic_auth)
  - `https://portainer.satoic.com` → 401 pre-auth (expected)
- GitOps deploy active: push to `main` → SSH → `gitops-deploy.sh`
- Openclaw paired to Telegram (`@sg_tar_bot`), n8n API wired, Chromium CDP connected
- Openclaw hooks enabled: `http://openclaw:18789/hooks/` (internal only, dedicated token)
- n8n credentials configured: Gmail, Google Drive, Postgres, HubSpot, Google OAuth (drive.file)
- `public.leads` table live (unique on `domain`)
- JS-01 workflow **active** (id: `chwneHrHVCQON462`) — full pipeline wired by TAR
- `OPENCLAW_GATEWAY_TOKEN` available in all n8n services (n8n, n8n-worker, n8n-webhook)
- Shared durable memory live in production:
  - `memory-api` healthy
  - public memory webhooks live at `https://n8n.satoic.com/webhook/memory`
  - Openclaw memory wrappers/policy deployed
  - document + transcript ingest routes live

**VM layout:**
- Repo: `/home/ubuntu/ai-automation-stack` (cloned from GitHub)
- Runtime symlink: `/home/ubuntu/automation → /home/ubuntu/ai-automation-stack/automation`
- Stack path on VM: `/home/ubuntu/automation`

---

## Active Priorities (next session)

- [x] Wire Krisp transcript output into `/webhook/memory/ingest/krisp` and validate first real production ingest (2026-03-12)
- [ ] Generate end-user UAT scripts for memory through Openclaw, Obsidian, and Krisp
- [ ] Create first real Obsidian seed notes and ingest them into memory
- [ ] Decide on the long-term “second brain” pattern for current truth vs journal history vs durable events
- [x] Update `gitops-deploy.sh` to restart Caddy when Caddyfile changes — already implemented via `caddy reload` (line 34)
- [ ] Research n8n v2 features — "Personal Agents" and "Workflow Agents" + how TARS could integrate
- [x] Fix `vm-safe.sh dr-backup` to use `tar -h` for symlink following (2026-03-05)
- [x] Fix `vm-safe.sh` usage text to include `n8n-task-runner` and `n8n-webhook` (2026-03-05)
- [ ] Build MCP bridge (Path A): Python MCP server on Mac → Openclaw API over Tailscale
- [ ] Set up shared handoff directory for Claude Code ↔ TAR async communication
- [ ] Test JS-01 end-to-end: `/lead <url>` → Openclaw → n8n → Postgres → HubSpot → Drive → Gmail
- [ ] Consider czlonkowski/n8n-mcp for better workflow authoring from Claude Code
- [x] Rotate `POSTGRES_PASSWORD` to a new URL-safe value and re-sync prod/dev DB-dependent services (2026-03-12)
- [x] Rotate `satoic_operator` SSH key on the Mac and VM (2026-03-12)
- [x] Rotate `satoic_ci` SSH key and GitHub secret `VM_SSH_PRIVATE_KEY` (2026-03-12)
- [x] Openclaw security hardening: gateway.auth.rateLimit + hooks.defaultSessionKey applied (2026-03-03)
- [x] Security audit baseline: 0 critical on both dev and prod (2026-03-03)
- [x] Dev Openclaw: added controlUi.allowedOrigins + fixed config perms (2026-03-03)
- [x] Caddy basic_auth removed for openclaw.satoic.com — gateway token auth only (2026-03-02)
- [x] Dev Openclaw Telegram disabled — prevents bot token conflict with production (2026-03-02)
- [x] Openclaw v2026.3.1 upgrade — dev-first validated, production deployed (2026-03-03)
- [x] Prod smoke test fixed: retry logic + startup delay + expected 200 for openclaw (2026-03-03)
- [x] Deploy scripts fixed to include `--build` flag for Dockerfile change detection
- [x] Dev lane cdp_net subnet collision fixed (dev: 172.31.0.0/24, prod: 172.30.0.0/24)
- [x] Full stack upgrade completed (2026-02-24): n8n v1→v2, Portainer lts, all patches pulled
- [x] Openclaw upgraded v2026.2.14 → v2026.2.23 → v2026.2.24 → v2026.2.26 → v2026.3.1; version pinned in Dockerfile
- [x] Openclaw post-upgrade recovery: fixed UID ownership, trustedProxies, device pairing, gateway token re-injection
- [x] Added post-deploy ownership check to `gitops-deploy.sh` (prevents UID drift)
- [x] Added Openclaw recovery runbook to `ops/runbooks.md`
- [x] OPENAI_API_KEY wired to Openclaw — TARS memory_search working
- [x] SSH hostname fix (`satoic-vm` → `satoic-production`) across all scripts
- [x] JS-01: TAR built and activated workflow (17 nodes, all credentials bound)
- [x] OPENCLAW_GATEWAY_TOKEN propagated to all n8n services
- [x] CI SSH hardening: strict host key checking enabled; uses `VM_SSH_KNOWN_HOSTS` secret (2026-03-05)
- [x] n8n hardening: disabled `CODE_ENABLE_PROCESS_ENV_ACCESS` on n8n, worker, webhook (2026-03-05)
- [x] n8n image pinning: `n8nio/n8n:2.9.2` (2026-03-05)
- [x] Emergency rsync hardening: `sync-to-vm.sh` now does dry-run + confirmation before `--delete` (2026-03-05)
- [x] Dev CI deploy stabilized: sanitized `VM_TAILSCALE_HOST` + default fallback IP + `accept-new` host key policy (2026-03-05)
- [x] Dev GitOps lane fixed: force `--scale caddy=0` to avoid port 80/443 conflict with production Caddy (2026-03-05)
- [x] Hardening rollout validated end-to-end: dev deploy+smoke and prod deploy+smoke green (2026-03-05)
- [x] Openclaw upgraded v2026.3.1 → v2026.3.2; version pin updated in Dockerfile (2026-03-05)
- [x] Openclaw upgraded v2026.3.2 → v2026.3.8; dev-validated, production deployed (2026-03-11)
- [x] n8n upgraded 2.9.2 → 2.11.2; dev-validated, production deployed (2026-03-11)
- [x] Openclaw UID ownership fix: explicit UID 1000 chown in gitops-deploy, vm-cron-backup, restore (2026-03-11)
- [x] gitops-deploy-dev.sh: added stash/ownership handling parity with production deploy script (2026-03-11)
- [x] First DR backup taken and verified (config 7MB + DB 14MB) (2026-03-10)
- [x] `.env.example` created documenting all 13 required env vars (2026-03-10)
- [x] Production Openclaw config synced to local (was 3 keys, now 51) (2026-03-10)
- [x] Automated daily backups: systemd timer at 03:00 UTC, 7-day retention on VM (2026-03-10)
- [x] `gitops-deploy.sh` fixed: handles Openclaw file ownership + stashes runtime changes before pull (2026-03-10)
- [x] `tar -h czf` → `tar -hczf` bug fixed across vm-safe.sh, end-session.sh (2026-03-10)
- [x] `vm-safe.sh dr-backup` docker path fix: busybox container now writes to /backup/ mount (2026-03-10)
- [x] `bootstrap-vm.sh` created: automates fresh VPS setup from zero (2026-03-10)
- [x] `restore.sh` created: restores config + Postgres from DR backup archives (2026-03-10)
- [x] Backup & recovery fully documented in `ops/runbooks.md` (2026-03-10)
- [x] Week 1 memory layer complete: schema, API, workflows, Openclaw integration, prod/dev validation (2026-03-11)
- [x] Week 2 ingest layer complete: document + transcript ingest routes and workflows, prod/dev validation (2026-03-11)
- [x] Obsidian first-pass ingress path working via Mac → VM `rsync` mirror (2026-03-11)

---

## Backup & Recovery Model

Full documentation in `ops/runbooks.md` (Backup & Recovery section).

### Summary

| Method | Schedule | Location | Trigger |
|--------|----------|----------|---------|
| Automated (systemd) | Daily 03:00 UTC | VM `/home/ubuntu/backups/` (7-day retention) | `satoic-backup.timer` |
| On-demand (Mac) | Manual | Mac `.dr-backups/` + manifest | `./scripts/backup.sh` |
| Manual (VM) | Manual | VM `/home/ubuntu/` | tar commands |

### Disaster recovery

1. `bootstrap-vm.sh` — sets up a fresh VPS (Docker, Tailscale, repo, symlink, secrets, backup timer)
2. `restore.sh` — restores secrets + Postgres from DR backup archives
3. `gitops-deploy.sh` — deploys the stack

See `ops/runbooks.md` for step-by-step procedure.

---

## SSH Key Inventory

| Key | Purpose | Location |
|-----|---------|----------|
| `satoic_operator` | Personal Mac→VM (`ssh oracle`, `ssh satoic-production`) | `~/.ssh/satoic_operator` |
| `satoic_ci` | GitHub Actions CI/CD only | `~/.ssh/satoic_ci` + GitHub secret `VM_SSH_PRIVATE_KEY` |
| `id_ed25519_github` | GitHub git operations | `~/.ssh/id_ed25519_github` |

**Last SSH key rotation:** `satoic_operator` and `satoic_ci` rotated successfully on 2026-03-12.

---

## Open Items / Known Risks

- **Dev/prod GitOps lanes** — `dev` branch live, auto-deploy green, smoke test green
- **Obsidian ingress path** — currently manual `./scripts/sync-obsidian-vault.sh` from Mac to VM; no schedule yet
- **Krisp upstream wiring** — live in production at `POST /webhook/memory/ingest/krisp`; first real meeting ingest validated on 2026-03-12 (`Stephan / Dana`, source_ref `krisp:019ce2c77998759e9e3d93b1baf7c19b`)
- **Tailscale GitHub Action authkey deprecation warning** — OAuth clients require a paid plan (not available on Free); authkey still works, revisit if plan upgraded or Tailscale forces migration
- **Dev stack running** — n8n 2.11.2 + Openclaw v2026.3.8 validated on dev (2026-03-11)
- **`scripts/backup.sh` / `vm-safe.sh dr-backup` only work from local Mac** — do not suggest running these on the VM
- **Gateway token** — verified matching between `.env` and `openclaw/config.json`; propagated to all n8n services (2026-02-23)
- **`POSTGRES_PASSWORD` format** — keep it URL-safe (`A-Za-z0-9._~-`) unless the compose-built DSNs are updated to URL-encode credentials; `memory-api` consumes a full DB URL assembled from env vars
- **Openclaw config schema (v2026.2.26+)** — `trustedProxies` and `controlUi` inside `gateway` section; `gateway.auth.rateLimit` uses `maxAttempts/windowMs/lockoutMs/exemptLoopback` (not `enabled/window/maxFailures`)
- **Openclaw security audit baseline** — 0 critical on both dev/prod (2026-03-03); see `ops/security-audit-2026-03-03.md`
- **Openclaw version pinned** — Dockerfile uses `ARG OPENCLAW_VERSION=2026.3.8`
- **Caddy bind-mount reload** — Caddyfile changes require explicit `docker compose restart caddy`; `docker compose up -d` does not detect bind-mount file changes
- **Openclaw device pairing** — new browser platforms (e.g., iPhone) require approval from an already-paired session; pending devices visible in `openclaw/devices/pending.json`
- **Openclaw basic_auth removed** — `openclaw.satoic.com` no longer uses Caddy basic_auth; gateway token (256-bit) is sole auth. Portainer still has basic_auth.
- **`openclaw onboard` overwrites config.json** — always backup before running; .bak may also be overwritten
- **Secrets rotated** — `POSTGRES_PASSWORD` and `N8N_ENCRYPTION_KEY` rotated 2026-02-20; n8n MFA cleared and ready to re-enroll
- **Pre-GitOps VM backup** — `/home/ubuntu/automation.pre-gitops-2026-02-16-2147` still on VM; safe to remove
- **MCP bridge planned** — Path A (Python MCP server on Mac) recommended to reduce user relay between Claude Code and TAR
- **Agent roles defined** — TAR owns n8n workflow CRUD; Claude Code owns infra/docker-compose/Caddy/git
- **GitHub Actions SSH trust** — `VM_SSH_KNOWN_HOSTS` secret must stay current when VM host keys rotate
- **Local `.env` missing `N8N_RUNNERS_AUTH_TOKEN`** — only on VM; should sync for parity

---

## How to Update This File

At the end of each session:
1. Check off completed items
2. Add any new open items or risks discovered
3. Update "What Is Live and Healthy" if the stack state changed
4. Also fill in the dated `ops/SESSION-YYYY-MM-DD.md` for the detailed log
