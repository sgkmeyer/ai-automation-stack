# CLAUDE.md — Agent Instructions for ai-automation-stack

This file is read by Claude Code (and Codex) at the start of every session.
It defines how agents should operate safely in this repository.

---

## Repo Layout

```
automation/     Infrastructure config: Docker Compose, Caddyfile, Openclaw runtime
ops/            Session logs, runbooks, plans, today.md
scripts/        Operational scripts (start/end session, sync, deploy, backup, verify)
sql/            Database schema scripts
workflows/      Workflow design docs
.github/        CI/CD workflows
```

Secrets (`automation/.env`, `automation/openclaw/config.json`) are gitignored and never committed.

---

## Deployment Rules

- **Default path:** commit → push → `./scripts/vm-safe.sh deploy` (GitOps)
- **Emergency only:** `./scripts/sync-to-vm.sh` (rsync direct copy)
- **Never edit the VM directly** for routine changes — use `vm-safe.sh`
- Changes to `automation/` take effect on the VM only after a GitOps deploy

---

## What Agents Can Do Freely

- Read any file in the repo
- Edit tracked files in: `automation/`, `scripts/`, `ops/`, `sql/`, `workflows/`, `.github/`
- Create new files in those directories
- Run read-only bash commands (`git status`, `git log`, `bash -n`, `cat`, etc.)

## What Requires Explicit Approval

- Any `vm-safe.sh` action (deploy, restart, backup, dr-backup, logs)
- `git commit` or `git push`
- Any SSH command to the VM
- Anything irreversible

---

## Backup Guardrails

**`scripts/backup.sh` and `vm-safe.sh dr-backup` run from the local Mac only.**
They SSH outward to `satoic-vm`. Running them on the VM itself will fail.

**Never suggest running these backup commands on the VM.**

### Normal backup (Tailscale live — current state)
`./scripts/backup.sh` from the Mac — SSH + rsync to `.dr-backups/` + manifest in `ops/dr-manifests/`.

### VM-local fallback (if Mac-side unavailable — e.g., direct SSH session on VM)
Instruct the user to run this in their SSH session on the VM:
```bash
cd /home/ubuntu
sudo tar czf automation-full-$(date +%F-%H%M).tar.gz automation
docker run --rm \
  -v automation_db_storage:/data \
  -v /home/ubuntu:/backup \
  busybox tar czf /backup/automation-db-$(date +%F-%H%M).tar.gz /data
```
Output stays on the VM at `/home/ubuntu/`. No local copy in this path.

---

## Secret Hygiene

- `automation/.env` is gitignored — never commit it, never paste its contents in chat
- `automation/openclaw/config.json` is gitignored — same rule
- If a secret is accidentally pasted in session output, rotate it immediately
- Secret scan before every commit: `git grep -nE '(OPENCLAW_GATEWAY_TOKEN|N8N_API_KEY|BROWSERLESS_TOKEN|BRAVE_API_KEY)'`

---

## Multi-Agent Conventions (Claude Code + Codex)

- **Claude Code:** multi-file work, infra changes, planning, session open/close, anything touching scripts/ or .github/
- **Codex:** inline edits, quick lookups, background cloud tasks
- **Git is the handoff point** — always commit and push before switching tools
- One task in flight at a time — no parallel edits to the same file from different agents
- If in doubt about scope, check `ops/today.md` for current priorities

---

## Quick Commands

| Task | Command |
|------|---------|
| Health check | `./scripts/verify.sh` |
| Backup | `./scripts/backup.sh` |
| Session open | `./scripts/start-session.sh` |
| Session close | `./scripts/end-session.sh` |
| VM status | `./scripts/vm-safe.sh ps` |
| VM logs | `./scripts/vm-safe.sh logs <service>` |
| VM deploy | `./scripts/vm-safe.sh deploy` |
| Dev deploy | `./scripts/vm-safe.sh deploy-dev` |

---

## Stack Services

| Service | URL | Auth |
|---------|-----|------|
| n8n | https://n8n.satoic.com | n8n native |
| Openclaw | https://openclaw.satoic.com | Caddy basic auth + gateway token |
| Portainer | https://portainer.satoic.com | Caddy basic auth + Portainer native |

Dev stack (when running): `http://100.82.169.113:5679` (Tailscale direct access — no tunnel needed).

---

## Current State Reference

See `ops/today.md` for current build state and active priorities.
See `ops/sessions/` (or `ops/`) for dated session logs.
See `ops/runbooks.md` for full operational procedures.
