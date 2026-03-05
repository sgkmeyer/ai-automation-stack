# TAR Workflow Governance (Openclaw + n8n)

## Purpose
Define how TAR (your primary Openclaw agent) designs, builds, tests, and promotes n8n workflows without production drift.

## Scope
- TAR-driven workflow lifecycle for n8n.
- Agent spawning for workflow architecture, build, and validation tasks.
- Promotion controls for `dev` -> `main`/production.

## Roles
- TAR (`control persona`):
  - Owns orchestration, policy checks, approvals routing, and final activation decisions.
- Specialist agents (spawned by TAR):
  - `workflow-architect`: structure, node graph, error handling design.
  - `workflow-builder`: n8n JSON generation/update.
  - `workflow-tester`: fixtures, replay tests, negative-path tests.
  - `ops-guardian`: risk review, rollback checks, deploy evidence.

## Environment Policy
- Dev-first mandatory:
  - TAR may create/update workflows in dev automatically.
  - TAR must not activate or mutate production workflows without explicit user approval.
- Production promotion:
  - Requires evidence bundle and explicit approval.

## Workflow Lifecycle
1. Spec
   - TAR creates `workflow-spec.json` (intent, trigger, inputs, outputs, dependencies, failure modes).
2. Build
   - TAR or builder agent generates n8n workflow JSON.
3. Validate
   - Structural checks, credentials mapping checks, node-compatibility checks.
4. Test (dev)
   - Execute with test fixtures.
   - Validate happy path + at least one failure path.
5. Review
   - TAR prepares concise change summary and risk notes.
6. Promote
   - On explicit approval, apply to production and verify smoke checks.

## Required Artifacts Per Workflow Change
- `workflow-spec.json`
- `workflow.json` (or API diff summary if workflow already exists)
- `test-fixtures.json`
- `validation-report.md`
- `rollback-plan.md`

Suggested storage path:
- `workflows/governed/<workflow-slug>/`

## Hard Gates
- TAR must block promotion when any gate fails:
  - Missing required credentials.
  - Missing rollback plan.
  - Test failures in dev.
  - Unhandled error path (no notification/branching).
  - Duplicate workflow name without explicit versioning intent.

## Naming and Versioning
- Workflow naming format:
  - `<DOMAIN>-<NN> - <purpose>`
  - Example: `JS-01 - Lead Enrichment Pipeline`
- Include version marker in notes or metadata:
  - `workflowVersion` (semver or date-based).

## Safety Constraints
- No destructive operations without approval:
  - deleting workflows
  - disabling production workflows
  - schema-changing DB writes
  - secret/credential mutation
- TAR must ask before any production activation toggle.

## Observability and Evidence
- TAR must return:
  - workflow id
  - activation state
  - execution id(s) from validation run
  - pass/fail summary
  - unresolved risks (if any)

## Rollback Standard
- Every change must include:
  - previous workflow id/version reference
  - exact rollback command/API call sequence
  - expected recovery verification checks

## Approval Protocol
- Explicit approval required for:
  - production activation/deactivation
  - production workflow overwrite
  - destructive cleanup actions
- Approval should be captured in session notes:
  - `ops/SESSION-YYYY-MM-DD.md`

## Default Decision Rules for TAR
- Prefer update-in-place only when workflow id is known and diff is low-risk.
- Prefer create-new-version when logic changes materially.
- Prefer inactive-by-default until validation report passes.

