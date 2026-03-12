# Operating Contract

This document defines how the project is operated from the repo side.
It exists to reduce operator-dependent behavior and keep the stack boring to run.

## Ownership

Working assumption: Codex owns repo-side DevOps execution unless the user explicitly redirects a task.

That means:

- Codex drives operational cleanup, repo hygiene, and deploy-path discipline
- TAR owns n8n workflow CRUD and Openclaw-side operational use
- The user remains the approval authority for deploys, SSH actions, commits, pushes, and irreversible changes

## Source Of Truth Hierarchy

Use the repository documents in this order:

1. `ops/today.md`
   Live state, current versions, active priorities, known risks, and environment facts that can change week to week.
2. `ops/runbooks.md`
   Canonical operating procedures, recovery steps, credential rotation, and backup/restore instructions.
3. `ops/SESSION-YYYY-MM-DD.md`
   Dated execution log for what changed, what was validated, and what remains.
4. `README.md`
   Stable architecture, boundaries, and repository contract.
5. `CLAUDE.md`
   Agent guardrails and collaboration rules, not environment state.

If these documents disagree, resolve the conflict by updating the lower-level document that drifted.
Do not preserve duplicate "current state" content in multiple places.

## Normal Change Path

Production changes should follow one default path:

1. Make the repo change locally.
2. If the change affects images, Compose, Caddy, auth, or runtime behavior, validate on dev first.
3. Push to the appropriate branch.
4. Deploy with the GitOps path.
5. Run the defined smoke or health checks.
6. Update `ops/today.md` if live state or risks changed.
7. Record the session details in the dated session log.

Break-glass paths exist, but they are exceptions:

- `scripts/sync-to-vm.sh` is emergency-only
- Direct VM edits are not part of routine operations

## Operational Invariants

These rules should stay true unless intentionally changed:

- One normal deploy path: GitOps
- One live-state document: `ops/today.md`
- Dev-first validation for runtime-affecting changes
- Secrets and runtime state stay out of git
- Recovery procedures must be testable, not only documented
- Auth, endpoint, and version facts should not drift across docs

## Current Cleanup Queue

Priority order for operational cleanup:

1. Remove documentation drift
   - Align auth, deploy-path, and source-of-truth statements across repo docs
2. Tighten verification
   - Define a standard preflight and post-deploy check set
   - Ensure memory and Openclaw surfaces have explicit smoke checks
3. Close security hygiene debt
   - Rotate the locally exposed `POSTGRES_PASSWORD`
   - Rotate SSH keys due around 2026-03-20
4. Reduce manual ingestion paths
   - Wire Krisp transcript ingress
   - Make Obsidian sync scheduled and observable
5. Improve agent coordination
   - Add a shared handoff path for Codex and TAR
   - Reduce chat-only state transfer

## Definition Of Done For Operational Work

An operational change is not done until:

- the repo change is applied
- the relevant environment is validated
- the runbook or live-state docs are updated if behavior changed
- rollback or recovery expectations are still clear

If one of those is missing, the work is still partial.
