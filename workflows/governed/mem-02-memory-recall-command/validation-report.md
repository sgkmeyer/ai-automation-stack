# Validation Report

- Status: draft artifact only, not yet created in n8n
- Trigger node: present
- Validation/normalization node: present
- Retrieval behavior: delegated to `memory-api /recall`
- Error behavior: non-2xx responses are translated into a Telegram-safe `reply_text`
- Missing before dev apply:
  - confirm n8n can supply `MEMORY_API_TOKEN`
  - import/create in dev
  - run happy-path and invalid-filter executions
