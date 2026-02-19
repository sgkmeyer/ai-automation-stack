# Automation Capability Plan

## Purpose
Move from guided/manual operations to safe, phased automation for local + VM workflows.

## Operating Principles
- Production safety before speed.
- Least privilege by default.
- Explicit approval for destructive actions.
- Every automated action must be auditable and reversible.

## Current Baseline
- GitOps deploy path is active (`/home/ubuntu/ai-automation-stack/scripts/gitops-deploy.sh`).
- Guarded VM wrapper exists (`scripts/vm-safe.sh`) with action allowlist + approval prompt.
- Session hygiene scripts exist (`scripts/start-session.sh`, `scripts/end-session.sh`).

## Phase 0 - Stabilize Guardrails
### Goals
- Remove remaining operational noise and lock in safe defaults.

### Work
- Keep `vm-safe.sh` as the default VM control path.
- Keep `start-session.sh --full` GitOps-first (no implicit rsync).
- Add/maintain log filtering windows to avoid stale incident noise.

### Done Criteria
- Daily start checks complete without ambiguous warnings.
- All deploy and restart actions are run through `vm-safe.sh`.
- No direct ad hoc VM commands for routine operations.

## Phase 1 - Staging Environment
### Goals
- Test infra/workflow changes without production risk.

### Work
- Create staging stack with separate compose project/volumes.
- Use staging subdomains or non-public access.
- Separate staging credentials/tokens from production.
- Add a staging deploy script parallel to production GitOps deploy.

### Guardrails
- No shared secrets between staging and production.
- No shared Postgres volumes between staging and production.

### Done Criteria
- One full deploy cycle validated in staging.
- At least one workflow test runs end-to-end in staging.
- Rollback procedure documented and tested for staging.

## Phase 2 - Secrets Management
### Goals
- Eliminate plaintext secret handling in repo/docs/sessions.

### Work
- Select a secret system (1Password CLI, SOPS/age, or Vault).
- Separate read-only vs deploy credentials.
- Add pre-commit/CI checks for secret patterns.
- Document secret rotation runbook with owner + cadence.

### Done Criteria
- `.env` values sourced from vault-managed flow.
- Secret scanning active in local workflow and CI.
- Rotation drill executed at least once.

## Phase 3 - Health, Alerting, and SLOs
### Goals
- Detect incidents quickly with low alert noise.

### Work
- Add checks for:
  - restart loops
  - Caddy upstream 502 spikes
  - missed cron/heartbeat tasks
  - low disk thresholds
- Send alerts to Telegram with severity tags.
- Add dedupe/cooldown logic for repeated alerts.

### Done Criteria
- Test alerts validated for each failure class.
- Alert noise remains below agreed threshold.
- Incident acknowledgment and resolution flow documented.

## Phase 4 - Policy-Driven Execution
### Goals
- Allow selective autonomous actions under strict policy.

### Work
- Define allowlist for non-destructive autonomous commands.
- Keep destructive actions approval-gated:
  - deploys
  - restarts
  - backup prune/delete
  - ownership/permission changes
- Add command logging (who/what/when/result).

### Done Criteria
- Non-destructive ops can run unattended safely.
- Approval prompts remain required for high-impact actions.
- Audit log can reconstruct every VM action.

## Phase 5 - GitHub PR Automation and CI Gates
### Goals
- Automate safe change delivery with reviewer-quality context.

### Work
- Create PR template requiring:
  - risk statement
  - validation evidence
  - rollback plan
- Add CI checks:
  - compose/yaml validation
  - script shell lint/syntax
  - endpoint smoke checks (staging)
- Auto-generate change summary draft for ops PRs.

### Done Criteria
- Every production change lands via PR + passing checks.
- Rollback plan present on every infra-affecting PR.
- Mean time to review decreases without higher incident rate.

## Phase 6 - Controlled Autonomous Deployments
### Goals
- Move from “assist + approve” to controlled automatic execution.

### Work
- Start with low-risk automation:
  - scheduled health checks
  - log triage summaries
- Progress to conditional auto-deploy only when:
  - CI passes
  - maintenance window open
  - recent health baseline is green
- Add automatic rollback trigger thresholds.

### Done Criteria
- At least 2 weeks of stable low-risk automation.
- One supervised auto-deploy succeeds with rollback readiness.
- Post-deploy health checks and notifications are automatic.

## Decision Log (Required for Phase Changes)
Before moving to the next phase, record:
- Why ready now.
- What risks remain.
- Which controls are in place.
- Who approved phase transition.

## Immediate Next Actions
1. Adopt `scripts/vm-safe.sh` as mandatory for routine VM operations.
2. Pick a secrets platform (recommendation: 1Password CLI for speed to value).
3. Design staging topology (subdomain, credentials, and data isolation).
