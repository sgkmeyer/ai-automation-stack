# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.

## Memory Interfaces

- Shared durable memory lives behind the memory webhooks, not only in workspace files.
- Workspace wrapper: `./bin/memory`
- Friendly wrappers:
  - `./bin/remember`
  - `./bin/recall-memory`
  - `./bin/context-memory`
  - `./bin/recall-unified`
- Production base URL: `https://n8n.satoic.com/webhook/memory`
- Dev base URL: `http://100.82.169.113:5679/webhook/memory`
- Internal routed-recall base URL: `http://memory-api:8100`
- Main endpoints:
  - `POST /log`
  - `POST /recall`
  - `POST /context`
  - `POST /ingest/document`
  - `POST /ingest/transcript`
  - `POST /router/recall`
  - `POST /mutations/query`
  - `POST /mutations/rollback`
- Use shared memory for durable facts, recall, and context. Use workspace files for working notes and local summaries.
- Local audit log: `memory/command-log.ndjson`
- Routed recall audit log: `router/command-log.ndjson`

## Registry Interfaces

- Shared content registry lives behind the registry webhooks, not the memory webhooks.
- Workspace wrapper: `./bin/registry`
- Friendly wrappers:
  - `./bin/query-registry`
  - `./bin/list-registry`
  - `./bin/review-registry`
- Production base URL: `https://n8n.satoic.com/webhook/registry`
- Main endpoints:
  - `POST /capture`
  - `POST /query`
  - `POST /list`
  - `POST /review`
  - `POST /process`
- Use registry first for saved links, summaries, and reading inbox behavior.
- Local audit log: `registry/command-log.ndjson`

## Capability Rollout

- A subsystem is not usable by TARS until the wrapper, docs, env, and live in-container verification are all done.
- Rollout checklist:
  [openclaw-capability-rollout.md](/Users/sgkmeyer/ai-automation-stack/ops/openclaw-capability-rollout.md)
