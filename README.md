# Satoic Automation Suite

This repo contains the baseline configuration and runbooks for the Satoic Automation Platform (n8n + Openclaw + Portainer on Oracle Free Cloud).

## Layout
- `automation/` Docker compose + Caddy config
- `ops/runbooks.md` Operations runbooks
- `sql/001_create_leads.sql` Lead table schema
- `workflows/lead-enrichment.workflow.md` MVP workflow outline
- `scripts/sync-from-vm.sh` Sync live VM config to this repo
- `scripts/sync-to-vm.sh` Sync local config back to the VM
- `scripts/redact-secrets.sh` Create a share-safe redacted bundle
- `scripts/gitops-deploy.sh` Simple GitOps deploy script (run on VM)

## Quick Start
```bash
cd automation
cp .env.example .env
# Fill in secrets in .env

docker compose up -d
```

## VM Sync
This pulls `~/automation` from the Oracle VM into this repo, excluding paths listed in `.syncignore`.

```bash
./scripts/sync-from-vm.sh
```

If you prefer not to mirror deletions on your laptop, remove `--delete` from `scripts/sync-from-vm.sh`.

To push local changes to the VM:
```bash
./scripts/sync-to-vm.sh
```

## Redacted Bundle
Generate a share-safe copy of the automation folder (no secrets, volumes, or certs):
```bash
./scripts/redact-secrets.sh
```

## GitOps (Starter)
Minimal GitOps approach:
1. Commit changes locally.
2. Push to your Git remote.
3. Run `scripts/gitops-deploy.sh` on the VM.

```bash
# On the VM
./scripts/gitops-deploy.sh
```

## Caddy Basic Auth
Generate bcrypt hash:
```bash
caddy hash-password --plaintext 'your-password'
```
Set `BASIC_AUTH_HASH` in `.env` and reload Caddy:
```bash
docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile
```

## Create Leads Table
```bash
# Example using psql inside the Postgres container
# (update DB creds from .env as needed)
cat ../sql/001_create_leads.sql | docker exec -i $(docker compose ps -q postgres) psql -U $POSTGRES_USER -d $POSTGRES_DB
```

## Exposed Services
- `https://n8n.satoic.com`
- `https://openclaw.satoic.com`
- `https://portainer.satoic.com`

## Security Baseline
- Only ports `22/80/443` exposed at UFW + OCI
- Basic auth on all public subdomains
- n8n login required after basic auth
