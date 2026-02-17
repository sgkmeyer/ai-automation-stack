# n8n Workflow Contract (Stephan ↔ TAR)

When TAR proposes/creates an n8n workflow, use this rule set.

## Required Rules of Engagement

1) **Return workflow JSON first** for review (no API creation yet).
2) **Use only installed/core nodes** (no community nodes unless explicitly approved).
3) Workflow must include:
   - **Trigger node**
   - **Validation/Normalization node**
   - **DB write node (Postgres)**
   - **Error branch** with Telegram/admin notification
4) **Name workflow**: `<WORKFLOW_NAME>` (follow naming convention; see below).
5) **Set workflow inactive by default**.
6) **After explicit approval**, create it via `POST /api/v1/workflows`.
7) After creation, return:
   - workflow id
   - workflow name
   - activation status
   - any required credentials not yet configured

## TAR Suggested Additions

8) **Versioning / idempotency**
   - Include a `workflowVersion` and/or stable `workflowHash` in the workflow (notes or name suffix).
   - Use a deterministic naming convention to avoid duplicates (e.g. `JS-01 - <name>`).

9) **Dry-run mode**
   - Support `DRY_RUN=true` to skip DB writes and only preview/log, for initial testing.

## DB Target Decision (pending)

Decide whether to write to:
- a dedicated Postgres schema/table owned by this automation stack (recommended), vs
- n8n’s internal tables (not recommended).
