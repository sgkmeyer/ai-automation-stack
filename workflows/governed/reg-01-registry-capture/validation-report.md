# Validation Report

- Status: repo artifact only; not yet imported into n8n
- Trigger node: present
- Auth model in repo: Webhook node `headerAuth` using the governed credential name `Registry Webhook Header Auth`
- Write behavior: delegated to `memory-api /registry/capture`
- Runtime model: fast capture only; background processing is delegated to memory-api
- Missing before apply:
  - create/import `Registry Webhook Header Auth`
  - ensure `Memory API Header Auth` resolves in the target n8n environment
  - import the governed workflow and activate it
  - run a shortened-URL and canonical-URL duplicate capture test
