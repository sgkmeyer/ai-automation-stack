# RAG Architecture — Design Notes

Status: **not started** — capturing decisions for when a use case demands it.

## When to build

Don't build until a specific workflow hits the wall of what Openclaw's
built-in `memory_search` can do. Triggers:

- "I wish TARS could search my resume collection"
- "TARS needs to reference my trading strategy docs"
- "I need job listings cross-referenced with my skills"

## Recommended architecture (pgvector + n8n)

No new services — uses existing Postgres and n8n.

```
Documents ──► n8n ingestion workflow ──► OpenAI embeddings API
                                              │
                                              ▼
                                     pgvector table (Postgres)
                                              │
                                              ▼
                              TARS queries via tool/API call
```

### Steps when ready

1. Enable pgvector on existing Postgres:
   `CREATE EXTENSION vector;`
2. Create embeddings table (content, embedding vector, metadata/source).
3. Build n8n workflow: watch folder/source → chunk → embed via OpenAI → upsert.
4. Expose a query endpoint (n8n webhook or direct SQL tool for TARS).

### Why this over a dedicated vector DB

- pgvector is a 10-minute add, no new container.
- Already backing up Postgres — embeddings get backed up too.
- Good enough for small-to-medium corpus (thousands of docs).
- Upgrade path: swap to Qdrant/Weaviate later if scale demands it.

## Potential use cases (future)

| Use case | Data sources | Priority |
|----------|-------------|----------|
| Job search workflows | Resumes, job listings, company research | TBD |
| Life automations | Personal docs, reference material | TBD |
| GTM automations | Outreach templates, lead data, market research | TBD |
| Trading bots | Strategy docs, market data, signals | TBD |

## Key decisions deferred

- Chunking strategy (fixed-size vs semantic) — depends on doc types
- Embedding model (OpenAI `text-embedding-3-small` is the default, cheap)
- Access control — single-user for now, revisit if multi-tenant
- Hybrid search (vector + keyword) — pgvector supports this but adds complexity
