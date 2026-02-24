# Today — Current Build State

> Manually maintained. Update at the end of each session alongside the dated session log.
> Last updated: 2026-02-24

---

## What Is Live and Healthy

**Production stack** (`automation` project on Oracle Free Tier VM):
- All 11 services up: caddy, db, redis, n8n, n8n-worker, n8n-webhook, n8n-task-runner, openclaw, chromium, portainer, toolbox
- **Stack versions (updated 2026-02-24):** n8n 2.9.2, Portainer CE lts, Caddy 2-alpine, Postgres 16-alpine, Redis 7-alpine, Python 3.12-slim
- Public endpoints:
  - `https://n8n.satoic.com` → 200 (app auth)
  - `https://openclaw.satoic.com` → 401 pre-auth (expected)
  - `https://portainer.satoic.com` → 401 pre-auth (expected)
- GitOps deploy active: push to `main` → SSH → `gitops-deploy.sh`
- Openclaw paired to Telegram (`@sg_tar_bot`), n8n API wired, Chromium CDP connected
- Openclaw hooks enabled: `http://openclaw:18789/hooks/` (internal only, dedicated token)
- n8n credentials configured: Gmail, Google Drive, Postgres, HubSpot, Google OAuth (drive.file)
- `public.leads` table live (unique on `domain`)
- JS-01 workflow **active** (id: `chwneHrHVCQON462`) — full pipeline wired by TAR
- `OPENCLAW_GATEWAY_TOKEN` available in all n8n services (n8n, n8n-worker, n8n-webhook)

**VM layout:**
- Repo: `/home/ubuntu/ai-automation-stack` (cloned from GitHub)
- Runtime symlink: `/home/ubuntu/automation → /home/ubuntu/ai-automation-stack/automation`
- Stack path on VM: `/home/ubuntu/automation`

---

## Active Priorities (next session)

- [ ] Research n8n v2 features — "Personal Agents" and "Workflow Agents" + how TARS could integrate
- [ ] Fix `vm-safe.sh dr-backup` to use `tar -h` for symlink following
- [ ] Fix `vm-safe.sh` usage text to include `n8n-task-runner` and `n8n-webhook`
- [ ] Build MCP bridge (Path A): Python MCP server on Mac → Openclaw API over Tailscale
- [ ] Set up shared handoff directory for Claude Code ↔ TAR async communication
- [ ] Test JS-01 end-to-end: `/lead <url>` → Openclaw → n8n → Postgres → HubSpot → Drive → Gmail
- [ ] Consider czlonkowski/n8n-mcp for better workflow authoring from Claude Code
- [x] Full stack upgrade completed (2026-02-24): n8n v1→v2, Portainer lts, all patches pulled
- [x] OPENAI_API_KEY wired to Openclaw — TARS memory_search working
- [x] SSH hostname fix (`satoic-vm` → `satoic-production`) across all scripts
- [x] JS-01: TAR built and activated workflow (17 nodes, all credentials bound)
- [x] OPENCLAW_GATEWAY_TOKEN propagated to all n8n services

---

## Backup & Recovery Model

### Current state (Tailscale live)

`./scripts/backup.sh` from the Mac works end-to-end:
SSH → VM backup → rsync artifacts to `.dr-backups/` locally → write manifest in `ops/dr-manifests/`.

**Always run from local Mac, never from the VM.** Scripts SSH outward to `satoic-production`.

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

## SSH Key Inventory

| Key | Purpose | Location |
|-----|---------|----------|
| `satoic_operator` | Personal Mac→VM (`ssh oracle`, `ssh satoic-production`) | `~/.ssh/satoic_operator` |
| `satoic_ci` | GitHub Actions CI/CD only | `~/.ssh/satoic_ci` + GitHub secret `VM_SSH_PRIVATE_KEY` |
| `id_ed25519_github` | GitHub git operations | `~/.ssh/id_ed25519_github` |

**Next key rotation due: ~2026-03-20**
To rotate `satoic_operator`: generate new key → add to VM `authorized_keys` → remove old entry → update `~/.ssh/config`.
To rotate `satoic_ci`: generate new key → update GitHub secret → add to VM `authorized_keys` → remove old entry.

---

## Open Items / Known Risks

- **SSH key rotation due ~2026-03-20** — rotate `satoic_operator` and `satoic_ci` (see SSH Key Inventory above)
- **Dev/prod GitOps lanes** — `dev` branch live, auto-deploy green, smoke test green
- **Tailscale authkey** — rotated to new reusable/ephemeral key (expires 2026-05-21); OAuth migration deferred until May
- **Dev stack not running** — torn down after n8n v2 upgrade testing (2026-02-24)
- **`scripts/backup.sh` / `vm-safe.sh dr-backup` only work from local Mac** — do not suggest running these on the VM
- **Gateway token** — verified matching between `.env` and `openclaw/config.json`; propagated to all n8n services (2026-02-23)
- **Secrets rotated** — `POSTGRES_PASSWORD` and `N8N_ENCRYPTION_KEY` rotated 2026-02-20; n8n MFA cleared and ready to re-enroll
- **Pre-GitOps VM backup** — `/home/ubuntu/automation.pre-gitops-2026-02-16-2147` still on VM; safe to remove
- **MCP bridge planned** — Path A (Python MCP server on Mac) recommended to reduce user relay between Claude Code and TAR
- **Agent roles defined** — TAR owns n8n workflow CRUD; Claude Code owns infra/docker-compose/Caddy/git
- **`vm-safe.sh dr-backup` tar doesn't follow symlinks** — needs `-h` flag since `automation` is a symlink on VM
- **`vm-safe.sh` usage text stale** — allowlist display missing `n8n-task-runner` and `n8n-webhook`
- **Local `.env` missing `N8N_RUNNERS_AUTH_TOKEN`** — only on VM; should sync for parity

---

## How to Update This File

At the end of each session:
1. Check off completed items
2. Add any new open items or risks discovered
3. Update "What Is Live and Healthy" if the stack state changed
4. Also fill in the dated `ops/SESSION-YYYY-MM-DD.md` for the detailed log
