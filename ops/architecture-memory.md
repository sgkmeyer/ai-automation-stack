# Memory Layer Architecture

## Purpose

The memory layer makes personal context durable and retrievable across sessions,
tools, and workflows. It serves the Personal OS and Second Brain capabilities
described in `ops/architecture.md`.

## Design Decisions

### Why not embeddings in v1?

Structured queries (entity match + time range + type filter + full-text search)
handle all Week 1 use cases. Vector search adds complexity that is not justified
until the corpus is large enough that structured queries miss relevant results.

### Why a separate service instead of direct DB access?

`memory-api` provides a clean API boundary that multiple consumers can call
without each needing database credentials or SQL knowledge. It also centralizes
LLM-powered extraction and synthesis logic.

### Why not a separate ingest-worker?

n8n is already the workflow engine. For workflow-driven ingestion, n8n calls
`memory-api` endpoints. A dedicated worker container is premature until volume
demands it.

## Data Model

### Entries

Everything that enters memory is an entry. Entries are append-only and carry a
type, body, source, and timestamp.

### Entities

Named things that entries reference. Entities are deduplicated by type plus
lowercase name, with optional aliases for fuzzy matching.

### Entry-Entity Links

Join rows connecting entries to the entities they mention. Each link has a role.

### Context Register

Key-value pairs organized by domain. Represents what is true right now and is
updated in place instead of appended.

### Ingestion Jobs

Tracks every ingestion attempt with status, counts, and error messages.

## Hybrid Stack Shape

Phase 1 now treats memory as a hybrid system with distinct canonical lanes.

### Shared Conversational Memory

Use for:

- durable conversational facts
- preferences
- commitments
- important decisions

This remains service-backed and optimized for quick agent recall.

### Context Register

Use for:

- current priorities
- temporary assumptions
- "true right now" state

This remains mutable and service-backed.

### Registry

Use for:

- saved links
- reading inbox
- review lifecycle state

This remains the canonical saved-content subsystem.

### Wiki Lane

Use for:

- compiled, human-readable syntheses
- person/company/project/topic pages
- source summary pages
- longitudinal knowledge artifacts

The wiki lane is file-backed for inspectability, but Phase 1 uses a reviewable
proposal flow rather than direct runtime canonicalization.

### Local Workspace Files

Use for:

- bootstrapping
- local working notes
- fallback continuity

These are not canonical long-term memory.

## Routing Rules

- conversational recall stays memory/context/registry/transcript first
- broad synthesis questions are wiki-first with selective fallback
- store provenance should remain visible in answers
- OpenClaw builtin semantic memory is treated as a helper/cache, not a
  canonical lane

## Agent-Neutral Contract

The service APIs are the durable capability boundary.

That means:

- TARS/OpenClaw shell wrappers are convenience adapters
- Claude Code, Hermes, and future agents should be able to call the same
  memory/context/registry/wiki contracts directly
- write-capable routes should carry actor metadata for audit and cross-agent
  debugging

## Week 2 Extensions

### File-Backed Ingestion

Week 2 adds dedicated ingestion endpoints for file-backed sources:

- `POST /ingest/document` for Obsidian-style note sync
- `POST /ingest/transcript` for Krisp-style transcript drops

These flows are idempotent on `source + source_ref` and carry a content
checksum in `structured` metadata so n8n can safely re-run sync jobs.

### Why dedicated ingest routes?

`/log` remains the lowest-friction conversational capture endpoint. File sync is
different: it needs stable source identities, checksum-based re-ingest, and
more predictable defaults for entry type classification. Splitting those
concerns keeps the Week 1 Telegram path simple while making Week 2 sync jobs
operationally clean.

## Security

- `memory-api` is internal-only with no public port mapping.
- Bearer token auth protects all functional endpoints.
- n8n and OpenClaw access it over the Docker network.
