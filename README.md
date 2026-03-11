# Satoic Personal OS

This repository is the operational source of truth for a personal operating system built around three layers:

- Personal OS: stable automations, communications, scheduling, browsing, and agent access
- Second brain: durable knowledge, notes, documents, transcripts, and retrieval
- Labs: experimental workflows and capabilities that may graduate into the core system later

The order matters. Personal OS is the product. The second brain supports it. Labs are allowed, but they do not define the system.

## What This Repo Owns

- Runtime infrastructure for the personal stack
- Agent runtime configuration for Openclaw
- n8n orchestration and workflow operations
- Operational runbooks, deploy scripts, and recovery procedures
- Knowledge-system design and schemas that support the second-brain layer

## What This Repo Is Not

- A generic automation playground with no boundary between experiments and production
- A business GTM system as the primary product surface
- A dumping ground for every kind of application state under the label "memory"

Work or domain-specific workflows can live here if they serve the personal operating system, but they should be treated as one domain inside the system, not the system's identity.

## System Priorities

1. Keep the personal stack reliable and recoverable.
2. Make personal knowledge durable, queryable, and manageable.
3. Isolate experiments so they do not degrade the core operating system.

## Architecture Summary

### Core runtime

- Reverse proxy/TLS: Caddy
- Orchestration: n8n + worker/webhook/task-runner services
- Queue/cache: Redis
- Database/system of record: PostgreSQL
- Agent gateway: Openclaw
- Browser runtime: Chromium CDP sidecar
- Container operations UI: Portainer

### Data classes

- Structured facts: Postgres tables for entities, records, and durable system facts
- Workflow state: Postgres tables and n8n execution state
- Ephemeral execution state: Redis
- Unstructured knowledge: document and note storage with retrieval-oriented indexing

See [ops/architecture.md](/Users/sgkmeyer/ai-automation-stack/ops/architecture.md) for the operating model and boundary rules.

## Repository Layout

- [automation](/Users/sgkmeyer/ai-automation-stack/automation): runtime stack files mirrored from the VM
- [ops](/Users/sgkmeyer/ai-automation-stack/ops): runbooks, architecture notes, session logs, and operational policy
- [scripts](/Users/sgkmeyer/ai-automation-stack/scripts): deploy, sync, backup, restore, and verification utilities
- [sql](/Users/sgkmeyer/ai-automation-stack/sql): schema scripts for durable system data
- [workflows](/Users/sgkmeyer/ai-automation-stack/workflows): workflow-specific design notes

## Current Direction

The current cleanup focus is to harden the repo contract before broadening the second-brain layer. That means:

- clarify ownership boundaries
- separate stable system concerns from labs
- define memory as a knowledge capability, not a junk drawer
- add memory infrastructure only after the CRUD model and data classes are explicit

## Operations

Pull current VM state:

```bash
cd /Users/sgkmeyer/ai-automation-stack
./scripts/sync-from-vm.sh
```

Deploy changes to the VM:

```bash
./scripts/sync-to-vm.sh
```

Apply the stack on the VM:

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
- `openclaw.satoic.com`: Openclaw gateway token authentication
- `portainer.satoic.com`: Caddy basic auth plus Portainer native admin auth

## Notes

- Keep secrets out of Git.
- Treat Docker Compose, Openclaw config, and runbooks as source of truth.
- Prefer explicit workflows and documented interfaces over hidden agent behavior.
- Promote labs into the core only after they prove useful and operationally clean.
