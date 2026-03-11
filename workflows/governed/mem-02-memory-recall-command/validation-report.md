# Validation Report

- Status: draft artifact only, not yet created in n8n
- Trigger node: present
- Validation/normalization node: delegated to memory-api
- Retrieval behavior: delegated to `memory-api /recall`
- Error behavior: currently relies on n8n default failure handling
- Auth model in repo: `httpHeaderAuth` credential named `Memory API Header Auth`, referenced by name so n8n import can resolve a concrete credential ID
- Dev validation: imported successfully into dev n8n
- Missing before dev apply:
  - create/import the `Memory API Header Auth` credential in dev n8n
  - re-import the governed workflow so the name-based credential reference resolves
  - run happy-path and invalid-filter executions with production-grade auth wiring
