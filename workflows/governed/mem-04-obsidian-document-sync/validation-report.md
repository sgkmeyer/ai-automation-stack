# Validation Report

- Status: draft artifact only, not yet imported into n8n
- Trigger node: present
- Auth model in repo: `httpHeaderAuth` credential named `Memory API Header Auth`
- Ingest behavior: delegated to `memory-api /ingest/document`
- Idempotency: delegated to checksum + `source/source_ref` logic in `memory-api`
- Missing before dev apply:
  - import/create `Memory API Header Auth` in the target n8n environment
  - run create, update, and unchanged document-sync fixtures against dev
  - verify caller-side file watcher payload shape matches this contract
