# Multi-Agent Workflow

## Purpose
Standardize how the team uses both Codex and Claude on the same project without drift or production risk.

## Core Rules
- Git is the source of truth for shared changes.
- Use GitOps for VM updates; avoid manual VM edits except emergencies.
- Keep tool-local workspaces untracked (for example `.claude/`).
- Keep secrets out of git and session notes.

## Daily Flow
1. Start in local repo:
   - `git fetch --prune`
   - `git status -sb`
2. Before switching tools:
   - commit or stash current work
   - push branch if work should be shared
3. In the next tool:
   - pull/rebase before editing
   - review `git diff` before commit
4. End of task:
   - commit small, focused changes
   - push and update session handoff notes

## Branching Policy
- `main` stays stable.
- Use one branch per task.
- Merge only after review + basic validation.

## VM Operations Policy
- Default path:
  - local commit/push
  - VM deploy via GitOps script
- Use `scripts/vm-safe.sh` for routine VM actions (`health`, `deploy`, `logs`, `backup`).
- Restarts/deploys/backups should be explicit and logged.

## Emergency Hotfix Policy
- If a direct VM hotfix is required:
  1. apply minimal fix on VM
  2. immediately mirror fix in local repo
  3. commit + push with clear "hotfix" message
  4. record reason and rollback notes in session log

## Handoff Standard
- Update `ops/SESSION-YYYY-MM-DD.md` at end of work.
- Include:
  - what changed
  - validation evidence
  - risks and rollback plan
  - exact next step
