# Validation Report

- Status: repo artifact only; not yet imported into n8n
- Trigger node: present
- Auth model in repo: Webhook node `headerAuth` using `Registry Webhook Header Auth`
- Query behavior: delegated to `memory-api /registry/query`
- Missing before apply:
  - import the workflow into n8n
  - confirm `Memory API Header Auth` resolves in the target environment
  - run query tests against at least one processed registry item and one empty-query inbox listing
