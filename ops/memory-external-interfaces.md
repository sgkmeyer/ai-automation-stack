# Memory External Interfaces

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
