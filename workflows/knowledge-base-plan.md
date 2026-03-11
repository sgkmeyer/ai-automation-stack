# Knowledge Base Plan

Status: approved direction, not yet implemented

## Purpose

Build the second-brain knowledge layer for the Personal OS in a way that is operationally clean, explicitly scoped, and easy to expand later.

This plan replaces the earlier broad "ingest everything" approach with a narrower rollout:

- first source: Obsidian markdown notes
- second source: Krisp meeting transcripts
- primary interface: Openclaw via Telegram
- storage: Postgres with pgvector

## Why This Shape

This repo is now explicitly organized around:

- Personal OS
- Second brain
- Labs

The knowledge base should support that model, not blur it.

So:

- Obsidian is the authored, curated knowledge source
- Krisp is the captured conversational source
- Telegram/Openclaw is the control and query interface
- Postgres remains the system of record
- pgvector is an implementation detail of retrieval, not the definition of memory

## Scope

### In scope for the first implementation

- Ingest Obsidian markdown notes from a designated folder
- Store document metadata and chunks in Postgres
- Store embeddings in pgvector
- Support query, list, delete, and idempotent re-ingest
- Expose the knowledge base to TAR/Openclaw, Claude Code, and n8n workflows
- Add Krisp transcript ingestion after Obsidian is working

### Out of scope for the first implementation

- Google Drive watcher
- PDF and DOCX parsing
- Web URL ingestion
- Generic "upload anything" support
- Telegram document upload as a primary ingest path
- Broad multi-source ingestion before the first slice is proven

## Product Model

### Source roles

- Obsidian: high-trust curated notes
- Krisp: lower-trust raw transcripts
- Telegram/Openclaw: conversational interface for query and control

### Retrieval rule

Retrieval must preserve source identity.

At minimum, every result should indicate:

- source kind
- source name
- timestamp
- document title
- tags or categories where available

This is necessary so the system can distinguish:

- "this is from my curated note"
- "this is from a transcript"

## Data Model

Use a parent-child schema. Do not use a chunks-only table keyed by filename.

### `knowledge_documents`

Purpose: canonical document record.

Recommended fields:

- `id UUID PRIMARY KEY`
- `source_kind TEXT NOT NULL`
  - examples: `obsidian_note`, `krisp_transcript`
- `source_name TEXT NOT NULL`
  - examples: vault-relative file path, Krisp transcript id
- `title TEXT`
- `source_type TEXT NOT NULL`
  - examples: `md`, `txt`
- `checksum TEXT NOT NULL`
- `status TEXT NOT NULL DEFAULT 'active'`
  - examples: `active`, `deleted`
- `metadata JSONB NOT NULL DEFAULT '{}'`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
- `deleted_at TIMESTAMPTZ`

Constraints:

- unique on `(source_kind, source_name)`

### `knowledge_chunks`

Purpose: retrieval units for each document.

Recommended fields:

- `id UUID PRIMARY KEY`
- `document_id UUID NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE`
- `chunk_index INTEGER NOT NULL`
- `content TEXT NOT NULL`
- `embedding vector(1536)`
- `metadata JSONB NOT NULL DEFAULT '{}'`
- `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
- `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
- `tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED`

Constraints and indexes:

- unique on `(document_id, chunk_index)`
- HNSW index on `embedding`
- GIN index on `tsv`
- B-tree index on `document_id`

## CRUD Model

### Create

Ingest a new source document, chunk it, embed it, and store both the parent document row and child chunk rows.

### Read

Query by semantic similarity, optionally mixed with metadata filters and full-text search.

### Update

Use idempotent re-ingest.

For Obsidian, the identity key is:

- `source_kind = obsidian_note`
- `source_name = vault-relative path`

For Krisp, the identity key is:

- `source_kind = krisp_transcript`
- `source_name = transcript id or normalized transcript filename`

If the checksum changed:

- update the document row
- delete and replace child chunks in one transaction

### Delete

Delete by document identity, not by filename alone.

Support either:

- soft delete on document row plus chunk removal
- hard delete of the document row with cascading chunk delete

For the first implementation, hard delete is acceptable if the operation is explicit and auditable.

### List

List documents from `knowledge_documents`, not chunk aggregates.

At minimum return:

- document id
- source kind
- source name
- title
- status
- updated_at

## API Contract

All consumers should use the same contract where possible.

### `POST /webhook/knowledge-ingest`

Purpose: create or update a document.

Example payload:

```json
{
  "source_kind": "obsidian_note",
  "source_name": "Areas/Trading/Options Strategy.md",
  "source_type": "md",
  "title": "Options Strategy",
  "content": "# Options Strategy\n\n...",
  "metadata": {
    "tags": ["trading", "options"],
    "category": "knowledge"
  }
}
```

Expected behavior:

- compute checksum
- upsert parent document
- replace chunks if changed
- return document id, status, chunk count

### `POST /webhook/knowledge-query`

Purpose: retrieve relevant chunks and source metadata.

Example payload:

```json
{
  "query": "What is my options strategy?",
  "top_k": 5,
  "filter": {
    "source_kind": "obsidian_note"
  }
}
```

Expected response shape:

- ranked results
- chunk content
- source metadata
- similarity score

### `GET /webhook/knowledge-list`

Purpose: list stored documents and metadata.

### `DELETE /webhook/knowledge-delete`

Purpose: remove a document by identity.

Example payload:

```json
{
  "source_kind": "obsidian_note",
  "source_name": "Areas/Trading/Options Strategy.md"
}
```

## Phase Plan

## Phase 0: Design And Contract

Goal: lock the data model and first use case before infra changes.

Deliverables:

- this plan doc
- agreed schema model
- agreed webhook contract
- agreed first source and first retrieval workflow

Exit criteria:

- no unresolved ambiguity about document identity
- no unresolved ambiguity about CRUD behavior
- parser/runtime ownership decided

## Phase 1: Infrastructure

Goal: prepare the stack for knowledge storage.

Changes:

- switch Postgres image in [automation/docker-compose.yml](/Users/sgkmeyer/ai-automation-stack/automation/docker-compose.yml) from `postgres:16-alpine` to `pgvector/pgvector:pg16`
- add [sql/002_create_knowledge_base.sql](/Users/sgkmeyer/ai-automation-stack/sql/002_create_knowledge_base.sql) with `knowledge_documents` and `knowledge_chunks`
- add [automation/openclaw/workspace/knowledge/README.md](/Users/sgkmeyer/ai-automation-stack/automation/openclaw/workspace/knowledge/README.md) as a curated markdown bridge, not the primary KB
- update [automation/openclaw/workspace/TOOLS.md](/Users/sgkmeyer/ai-automation-stack/automation/openclaw/workspace/TOOLS.md) with the knowledge endpoints once they exist

Explicit non-goal:

- do not add parser libraries until the parsing runtime is decided

Exit criteria:

- dev deploy succeeds
- `CREATE EXTENSION vector;` succeeds
- schema applies cleanly
- smoke test insert/query succeeds

## Phase 2: First Vertical Slice

Goal: make the system useful with the smallest real second-brain workflow.

Source:

- Obsidian markdown notes only

Capabilities:

- ingest Obsidian note
- re-ingest modified note
- query note corpus
- list ingested notes
- delete ingested note

Interface:

- Openclaw/Telegram can trigger query and control operations
- Claude Code can use the same webhook contract
- n8n can query directly or via webhook

Recommended first use case:

- "What do my notes say about X?"

Exit criteria:

- note edits propagate correctly
- duplicate ingest does not create duplicate documents
- delete removes the note cleanly
- query returns useful note context with source attribution

## Phase 3: Telegram/Openclaw Control Surface

Goal: make Telegram the primary user interaction layer without making it the storage layer.

Supported operations:

- query knowledge
- list recent documents
- trigger Obsidian sync or ingest
- delete a known document
- summarize findings with source attribution

Important rule:

- Telegram is the interface, not the source of truth

## Phase 4: Krisp Ingestion

Goal: add conversational memory after curated note retrieval is stable.

Source:

- Krisp meeting transcripts

Behavior:

- ingest transcript text plus meeting metadata
- store as `source_kind = krisp_transcript`
- preserve lower-trust source identity in retrieval

Recommended first use case:

- "What did we discuss about project X in recent meetings?"

Exit criteria:

- transcripts ingest cleanly
- transcript retrieval is distinguishable from curated notes
- mixed queries can filter or rank by source kind

## Phase 5: Expansion

Only after the above is working:

- PDF and DOCX parsing
- Google Drive ingestion
- Telegram document upload
- web URL capture
- hybrid ranking improvements

## Runtime Ownership Decision

This must be explicit before parser libraries are installed.

Options:

1. Parse inside n8n workflows
2. Parse in a dedicated helper runtime
3. Parse via Openclaw-triggered helper code

Current recommendation:

- first slice uses Obsidian markdown only, so no special parser runtime is needed
- defer parser-library installation until Phase 5 or until Krisp/other sources require it

## Verification

### Dev

- Postgres starts on `pgvector/pgvector:pg16`
- n8n remains healthy
- Openclaw remains healthy
- schema applies cleanly
- test document ingest works
- similarity query returns expected chunk
- list and delete operations work

### Production

- take DR backup first
- deploy via GitOps after dev validation
- verify all core services healthy
- verify knowledge endpoints return expected responses

## Resource Expectations

Current target size:

- 50 to 500 documents

Expected footprint:

- comfortably within existing VM headroom
- no new service required
- embeddings cost remains negligible at this scale

## Immediate Next Step

Implement Phase 1 only after one more short planning decision:

- define the exact Obsidian source path and sync method

Once that is decided, execution can begin with:

1. pgvector image swap
2. schema creation
3. dev deploy and smoke test
