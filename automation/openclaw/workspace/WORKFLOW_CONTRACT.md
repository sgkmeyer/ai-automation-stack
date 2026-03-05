# n8n Workflow Contract (Stephan ↔ TAR)

When TAR proposes/creates an n8n workflow, use this rule set.
This contract is the quick-operating layer; full policy lives in:
`/Users/sgkmeyer/ai-automation-stack/ops/TAR-WORKFLOW-GOVERNANCE.md`

## Required Rules of Engagement

1) **Return workflow spec + workflow JSON first** for review (dev apply allowed only after contract checks).
2) **Use only installed/core nodes** (no community nodes unless explicitly approved).
3) Workflow must include:
   - **Trigger node**
   - **Validation/Normalization node**
   - **DB write node (Postgres)**
   - **Error branch** with Telegram/admin notification
4) **Name workflow**: `<WORKFLOW_NAME>` (follow naming convention; see below).
5) **Set workflow inactive by default** unless explicitly asked to activate in dev.
6) **Dev-first rule**: TAR may create/update in dev after checks pass.
7) **Production rule**: explicit approval required before create/update/activate in production.
8) After creation/update, return:
   - workflow id
   - workflow name
   - activation status
   - any required credentials not yet configured
   - validation summary (pass/fail + execution IDs)
   - rollback summary

## TAR Suggested Additions

9) **Versioning / idempotency**
   - Include a `workflowVersion` and/or stable `workflowHash` in the workflow (notes or name suffix).
   - Use a deterministic naming convention to avoid duplicates (e.g. `JS-01 - <name>`).

10) **Dry-run mode**
   - Support `DRY_RUN=true` to skip DB writes and only preview/log, for initial testing.

## DB Target Decision (pending)

Decide whether to write to:
- a dedicated Postgres schema/table owned by this automation stack (recommended), vs
- n8n’s internal tables (not recommended).
