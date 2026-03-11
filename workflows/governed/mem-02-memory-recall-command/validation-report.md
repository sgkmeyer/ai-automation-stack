# Validation Report

- Status: draft artifact only, not yet created in n8n
- Trigger node: present
- Validation/normalization node: delegated to memory-api
- Retrieval behavior: delegated to `memory-api /recall`
- Error behavior: currently relies on n8n default failure handling
- Dev validation: imported successfully into dev n8n
- Missing before dev apply:
  - replace `$env.MEMORY_API_TOKEN` usage with a proper n8n credential reference; expressions cannot access env vars in this hardened runtime
  - run happy-path and invalid-filter executions with production-grade auth wiring
