# Validation Report

- Status: repo artifact only; not yet imported into n8n
- Trigger nodes: present for both `registry/list` and `registry/review`
- Auth model in repo: both Webhook nodes use `Registry Webhook Header Auth`
- Read/write behavior: delegated to `memory-api /registry/list` and `/registry/review`
- Missing before apply:
  - import the workflow into n8n
  - confirm `Memory API Header Auth` resolves in the target environment
  - validate paginated inbox listing and at least one `archive` plus `mark_reviewed` action
