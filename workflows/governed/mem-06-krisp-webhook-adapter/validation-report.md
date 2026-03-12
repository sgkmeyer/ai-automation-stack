# Validation Report

- Status: repo artifact updated after production payload inspection; re-import/replay required
- Trigger node: present
- Auth model in repo: Webhook node `headerAuth` using the governed credential name `Krisp Webhook Header Auth`
- Normalization: handled inside the workflow adapter before calling `memory-api /ingest/transcript`
- Transcript persistence and idempotency: delegated to `memory-api` using stable `source_ref`
- Audit trail target: `/home/node/.n8n/krisp-ingest.ndjson` as NDJSON append-only log
- Runtime compatibility: workflow is code-node-free; it avoids blocked `$env` expression access and does not depend on `n8n-task-runner`
- Runtime gate: target n8n env must expose `NODES_EXCLUDE=[]` so the `Execute Command` node is available for audit-log append steps
- Production payload note: on March 12, 2026, Krisp `transcript_created` delivered transcript text under `data.content.description` and meeting identity under `data.meeting.*`
- Missing before dev apply:
  - re-import `MEM-06 - Krisp Webhook Adapter` into dev and production
  - replay the transcript-ready, transcript-only, and ignored-event fixtures against dev
  - verify the audit log appends exactly one line per replayed webhook event
  - verify duplicate delivery of the same Krisp meeting id no-ops or updates without creating duplicate memories
