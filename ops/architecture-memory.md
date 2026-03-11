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

## Security

- `memory-api` is internal-only with no public port mapping.
- Bearer token auth protects all functional endpoints.
- n8n and OpenClaw access it over the Docker network.
