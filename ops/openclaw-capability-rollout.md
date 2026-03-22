# Openclaw Capability Rollout

This checklist exists to prevent a repeat of the same failure mode:

- backend feature exists
- workflows are active
- but TARS/Openclaw cannot actually use it

The registry rollout exposed that gap clearly. From now on, a subsystem is not
"live for TARS" until all of the layers below are complete.

## Definition Of Ready

Before adding a new TARS-facing subsystem, confirm:

1. The backend route or service contract exists.
2. The route has operator-facing documentation.
3. The route has at least one concrete validation path.
4. The request/response shape is stable enough to wrap.

## Required Rollout Layers

Every new capability must ship through all of these layers.

### 1. Substrate

- Postgres schema or durable storage is in place.
- Idempotency and error behavior are understood.
- Secrets/env vars are defined explicitly.

### 2. Service Layer

- `memory-api` route or equivalent service endpoint exists.
- n8n workflow route exists where applicable.
- Workflow credentials are governed, not ad hoc.
- Success, partial-success, and failure states are inspectable.

### 3. Openclaw Tool Surface

- A workspace wrapper exists in `automation/openclaw/workspace/bin`.
- Friendly shortcut wrappers exist when needed.
- Wrapper output is concise enough for TARS to reason over.
- Required env vars are available inside the Openclaw container.

### 4. Policy Surface

- `AGENTS.md` tells TARS when to use the capability.
- `TOOLS.md` points to the right base URLs, wrappers, and boundaries.
- Any capability-specific policy/examples are present when behavior is non-trivial.

### 5. Verification

- The wrapper runs inside production Openclaw.
- The output shape is usable by TARS, not just technically correct.
- The capability is verified against at least one real item or realistic fixture.
- Live-state docs are updated after rollout.

## Minimal Audit For A New Capability

When a capability is believed to be live, verify all of these:

### Backend

- route responds
- auth works
- required storage/schema exists

### Openclaw

- wrapper exists
- wrapper runs in-container
- policy docs mention the wrapper and the trigger phrases

### Human-facing

- end-user docs exist if the feature is user-operated
- UAT doc exists if the feature is operationally important

## Required Proof

For each rollout, capture the exact proof in the session log:

- wrapper command used
- environment or endpoint used
- result summary
- any remaining known risks

## Current Capability Audit Snapshot

As of `2026-03-21`, the current TARS-facing shared-system wrappers are:

### Memory

- `./bin/memory`
- `./bin/remember`
- `./bin/recall-memory`
- `./bin/context-memory`

### Registry

- `./bin/registry`
- `./bin/query-registry`
- `./bin/list-registry`
- `./bin/review-registry`

This should be re-audited whenever a new subsystem is added or an existing one
changes shape.
