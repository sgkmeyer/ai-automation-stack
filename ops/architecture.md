# Architecture

## Purpose

This repository defines and operates a personal operating system with a second-brain capability and an attached lab environment.

The design principle is simple:

- the personal OS is the stable product
- the second brain is a core capability of that product
- labs are experimental and must stay isolated from the core until proven

## System Layers

### 1. Personal OS

The personal OS is the stable execution layer for day-to-day life and work.

It includes:

- agent access and interfaces
- messaging and communication automations
- scheduling, reminders, and coordination workflows
- browsing and web task execution
- repeatable operational workflows

This layer should optimize for reliability, recoverability, and clarity of ownership.

### 2. Second Brain

The second brain is the knowledge layer.

It exists to make personal context durable and retrievable across sessions, tools, and workflows. It is not a generic bucket for all state.

It includes:

- notes
- documents
- transcripts
- research captures
- summaries and derived knowledge artifacts

Its job is retrieval, provenance, and lifecycle management.

### 3. Labs

Labs are experimental capabilities.

They are allowed to be incomplete, narrow, or speculative, but they must be marked as such. Labs should not quietly become production dependencies without an explicit promotion step.

Examples:

- trying a new agent pattern
- testing workflow ideas
- piloting a retrieval pipeline
- proving a new integration before adopting it

## Boundary Rules

### What belongs in Postgres

Use Postgres for:

- structured facts and canonical entities
- workflow runs, outputs, and durable statuses
- second-brain document metadata
- retrieval indexes and chunk records for unstructured knowledge
- audit-friendly records that need clear lifecycle control

Postgres is the system of record.

### What belongs in Redis

Use Redis for:

- queues
- transient execution state
- short-lived cache

Redis is not long-term memory.

### What belongs in the second-brain knowledge layer

Use the knowledge layer for:

- documents
- transcripts
- notes
- web captures
- research artifacts

This layer should support create, read, update, delete, list, and provenance. It should not be the default home for relational business facts or workflow bookkeeping.

## Memory Model

In this system, "memory" means three different things and they should stay separate:

1. Workflow state
Short-lived or execution-oriented state owned by n8n and runtime services.

2. Durable structured facts
Canonical records that belong in normal relational tables.

3. Unstructured knowledge retrieval
Documents and notes stored with metadata and retrieval indexes.

Only the third category should use vector-style retrieval.

## Second-Brain Design Constraints

Before implementation, the knowledge layer should satisfy these constraints:

- every document has a stable parent record
- chunks are children of documents, not free-floating rows
- every chunk and document has provenance metadata
- update and delete operations are first-class, not afterthoughts
- ingestion is explicit and auditable
- labs cannot silently write undocumented knowledge data into production tables

This implies a parent-child model such as:

- `knowledge_documents`
- `knowledge_chunks`

not a chunks-only table keyed by filename.

## Promotion Rule For Labs

A lab graduates into the core only when all of the following are true:

- the use case is repeated and real
- the interfaces are documented
- the data lifecycle is understood
- backup and recovery implications are acceptable
- the feature does not blur ownership boundaries

If those conditions are not met, it stays a lab.

## Immediate Implications

This repo should now be organized and evaluated as:

- a stable personal operating system
- with an explicit second-brain capability under design
- and experimental labs kept legible and contained

That means future memory work should begin with one narrow vertical slice, not a broad promise to ingest everything everywhere.
