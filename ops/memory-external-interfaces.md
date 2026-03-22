# Memory External Interfaces

For end-user usage guidance, see
[memory-user-guide.md](/Users/sgkmeyer/ai-automation-stack/ops/memory-user-guide.md#L1).

This stack exposes memory to end users through n8n webhooks. `memory-api` stays
internal-only on the Docker network.

## Public Interface

- Production base URL: `https://n8n.satoic.com/webhook/memory`
- Dev base URL: `http://100.82.169.113:5679/webhook/memory`

Routes:

- `POST /log`
- `POST /recall`
- `POST /context`
- `POST /ingest/document`
- `POST /ingest/transcript`

## Internal Memory-API Interfaces

These routes are internal-only and are intended for Openclaw/TARS and operator
tooling. They are not exposed directly through the public n8n webhook surface.

Base URL on the Docker network:

- `http://memory-api:8100`

Routes:

- `POST /router/recall`
  - unified recall router over registry, transcripts, durable memory, and
    current context
  - returns:
    - intent classification
    - primary and secondary lanes
    - routing reason
    - answer mode
    - normalized results
    - lane attempts with confidence and result density

- `POST /mutations/query`
  - query the mutation journal for reversible user-driven mutations

- `POST /mutations/rollback`
  - rollback a supported mutation by `mutation_id`
  - current rollback scope:
    - registry `review_state_change`

## Source Adapters

The normalized transcript ingest route is not the same thing as a vendor-facing
source adapter.

Krisp should target a dedicated adapter endpoint:

- Production: `https://n8n.satoic.com/webhook/memory/ingest/krisp`
- Dev validation: VM-local replay into `n8n-webhook` (see `ops/runbooks-memory.md`)

That adapter is responsible for:

- validating the Krisp shared-secret header
- normalizing Krisp webhook payloads
- forwarding transcript-bearing events to `POST /ingest/transcript`
- appending an operator-visible ingest audit record

Manual callers should continue using the normalized transcript route through
`scripts/memory-webhook.sh transcript ...`.

## End-User CLI

Use [memory-webhook.sh](/Users/sgkmeyer/ai-automation-stack/scripts/memory-webhook.sh) for manual use instead of hand-writing curl payloads.

Examples:

```bash
scripts/memory-webhook.sh log --text "Met Sam for coffee" --tags relationship
scripts/memory-webhook.sh recall --query "coffee with Sam" --limit 3
scripts/memory-webhook.sh context-set --domain prefs --key coffee --value "flat white"
scripts/memory-webhook.sh document --source-ref Daily/2026-03-11.md --file ~/vault/Daily/2026-03-11.md
scripts/memory-webhook.sh transcript --source-ref krisp:demo --file ./meeting.txt --action-items "Send proposal,Book follow-up"
```

To target dev instead of prod:

```bash
MEMORY_WEBHOOK_BASE_URL=http://100.82.169.113:5679/webhook/memory \
  scripts/memory-webhook.sh recall --query "Databricks"
```

## OpenClaw Boundary

OpenClaw should treat workspace files as local working memory, not the canonical
long-term database. Durable writes and recalls should route through the shared
memory webhooks so other front ends can use the same memory layer.

The OpenClaw workspace wrapper is:

```bash
./bin/memory
```

That wrapper delegates to the repo-managed CLI at
`/home/node/repo/scripts/memory-webhook.sh` and defaults to the production
memory webhook base URL.

Additional OpenClaw-friendly wrappers:

```bash
./bin/remember "Met Sam for coffee" --tags relationship
./bin/recall-memory "coffee with Sam"
./bin/recall-unified --query "what did I save about AI GTM"
./bin/context-memory set --domain prefs --key coffee --value "flat white"
```

Each wrapper invocation is logged locally to:

```text
memory/command-log.ndjson
```
