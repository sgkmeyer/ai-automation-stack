# Tranche B State Reversibility Design

Locked on 2026-03-21 as the mutation-safety baseline for Tranche B.

## Goal

Give TARS and future operator tools a safe write path across registry, memory,
and later tasks/decisions without creating irreversible damage.

This design is intentionally narrower than a full event-sourced architecture.
The objective is:

- safe everyday mutations
- explicit rollback paths
- auditable operator recovery
- low-complexity implementation

## Design Principles

1. Prefer reversible metadata changes over destructive rewrites.
2. Keep source-driven ingest append- or upsert-oriented, not manually edited.
3. Journal user-facing mutations before or alongside applying them.
4. Treat merge and promotion as operator-sensitive actions with stronger audit.
5. Do not give TARS mutation power that lacks a clear rollback story.

## Mutation Classes

### Class A: Reversible Metadata Mutations

These are safe to expose to TARS once journaling exists.

Examples:

- registry `review_state` changes
- future task status changes
- future task due-date changes
- future priority/flag changes
- future "mark important" actions

Expected rollback:

- direct inverse mutation
- journal-backed operator restore

### Class B: Reversible Cross-Store Mutations

These create or link records in another store and must be traceable.

Examples:

- promote registry item to memory
- turn transcript action item into task
- attach item to entity/project

Expected rollback:

- reverse the created link or created downstream record
- preserve provenance so rollback does not guess

### Class C: Structural Mutations

These change storage topology and should be operator-gated or strongly
constrained.

Examples:

- registry item merge
- memory dedupe merge
- future task merge

Expected rollback:

- journal-backed restore using pre-merge snapshots or mutation payloads
- operator-led recovery path only

### Class D: Source-Driven Ingest Mutations

These are primarily governed by source-of-truth replay, not by user undo.

Examples:

- transcript ingest refresh
- Krisp key points/action items refresh
- document re-ingest after improved parser

Expected rollback:

- replay prior source version if available
- or restore from mutation journal / backup if recovery is needed

These should not be framed to TARS as user-editable state.

## Recommended Mechanism

Use a mixed model:

1. **Mutation journal** for user-facing writes
2. **Soft-state transitions** where natural
3. **Operator-only structural rollback** for merges and promotions
4. **Source replay** for ingest-driven corrections where practical

Do not implement global row versioning across all tables.
That would add more complexity than value at this stage.

## Proposed Journal Contract

Each mutable subsystem should emit a journal record with:

```json
{
  "mutation_id": "uuid",
  "occurred_at": "2026-03-21T18:00:00Z",
  "actor_type": "tars",
  "actor_id": "openclaw",
  "subsystem": "registry",
  "mutation_type": "review_state_change",
  "target_id": "uuid",
  "reason": "archive the first one",
  "before": {
    "review_state": "inbox"
  },
  "after": {
    "review_state": "archived"
  },
  "rollback_mode": "inverse_mutation",
  "rollback_status": "available"
}
```

Minimum required fields:

- `mutation_id`
- `occurred_at`
- `actor_type`
- `subsystem`
- `mutation_type`
- `target_id`
- `before`
- `after`
- `rollback_mode`
- `rollback_status`

Nice-to-have fields:

- `reason`
- `session_id`
- `operator_notes`
- `source_ref`

## Subsystem Rules

### Registry

Safe TARS mutations:

- `mark_reviewed`
- `mark_inbox`
- `archive`

Required rollback model:

- direct inverse action
- journal entry for each change

Operator-sensitive mutations:

- merge duplicate items
- restore merged/deleted duplicate shape
- future hard-delete or purge

Registry recommendation:

- keep `review_state` as soft-state, not destructive delete
- when merges happen, journal:
  - survivor item id
  - absorbed item id
  - moved capture ids
  - metadata reconciliation details

### Memory

Safe TARS mutations:

- none by default in Tranche B beyond future promotion actions

Operator-sensitive mutations:

- dedupe merge
- entity merge
- deletion/purge

Memory recommendation:

- treat normal memory rows as durable historical records
- prefer additive corrective entries over silent destructive edits
- only expose targeted reversible actions later, after journaling exists

### Future Tasks / Decisions

Safe TARS mutations once the subsystem exists:

- create task
- update status
- update due date
- set waiting-on
- archive/reopen task

Required rollback model:

- inverse mutation backed by journal

Task recommendation:

- design the schema from day one with:
  - `status`
  - `archived_at`
  - `source_entry_id`
  - optional `person_id` / `company_id` / `project_id`

## TARS Write Authority Policy

### Allowed Once Journal Exists

- registry review-state changes
- future task status changes
- future low-risk curation actions with clear inverse

### Allowed Only With Operator Guardrails

- promotion from registry/transcript into another store
- merge or dedupe actions
- entity linking that creates durable structural relationships

### Not Allowed By Default

- hard delete
- purge
- silent destructive dedupe
- schema-shaping writes

## Rollback Modes

### Inverse Mutation

Best for:

- review-state changes
- task status changes
- archive/reopen

Mechanism:

- apply the opposite mutation using journal `before` state

### Compensating Mutation

Best for:

- promotions
- cross-store linking

Mechanism:

- remove created link or downstream record
- preserve audit trail rather than pretending nothing happened

### Operator Restore

Best for:

- merges
- dedupe
- ambiguous structural corrections

Mechanism:

- reconstruct from journal payload and preserved ids/metadata

### Source Replay

Best for:

- ingest-driven rows

Mechanism:

- re-run ingest from prior source payload or known-good snapshot

## Minimum Tranche B Implementation Recommendation

Do not try to build the full journal across every subsystem immediately.

Implement in this order:

1. registry mutation journal for `review_state` changes
2. mutation schema / helper library shape that other subsystems can reuse
3. operator-only merge journaling for registry duplicate convergence
4. promotion journaling when promotion actions are introduced

This gives us a narrow but real reversibility foundation.

## Observability Requirements

Every reversible mutation should answer:

- what changed
- who changed it
- why it changed
- what the prior state was
- how to undo it
- whether undo is still available

Minimum operator surfaces:

- query recent mutations by subsystem
- query mutations for a target id
- inspect `before` and `after`
- perform rollback for inverse-mutation cases

## Example Operator Workflows

### Registry Item Archived Incorrectly

1. Find the latest mutation journal row for the item.
2. Confirm mutation type is `review_state_change`.
3. Inspect `before.review_state`.
4. Apply inverse mutation to restore `inbox` or `reviewed`.
5. Journal the rollback action too.

### Registry Duplicate Merge Was Wrong

1. Inspect the structural merge journal entry.
2. Identify survivor item, absorbed item, and moved captures.
3. Recreate the absorbed item if needed.
4. Move captures back.
5. Record operator restore notes.

### Bad Promotion From Registry Into Memory

1. Find the promotion journal entry.
2. Locate created memory row ids or linking records.
3. Apply compensating mutation:
   - archive/unlink the promoted record
   - preserve audit note that promotion was reverted

## Definition of Done

State reversibility is ready for implementation when:

- mutation classes are explicit
- TARS write authority boundaries are explicit
- rollback modes are explicit
- registry review-state changes have a concrete journal design
- merge/promotion rollback expectations are documented before those actions expand

## Immediate Next Step

Use this design to implement the first narrow mutation journal for registry
review-state changes before broadening TARS write authority.
