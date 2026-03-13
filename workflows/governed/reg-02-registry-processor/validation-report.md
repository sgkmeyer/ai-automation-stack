# Validation Report

- Status: repo artifact only; not yet imported into n8n
- Trigger node: present
- Auth model in repo: Webhook node `headerAuth` using `Registry Webhook Header Auth`
- Processing behavior: delegated to `memory-api /registry/process`
- Missing before apply:
  - import the workflow into n8n
  - confirm `Memory API Header Auth` resolves in the target environment
  - run one explicit reprocess after a successful capture to verify merge and archive behavior
