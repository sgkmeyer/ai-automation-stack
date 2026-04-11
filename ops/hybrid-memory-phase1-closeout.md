# Hybrid Memory Stack Phase 1 Closeout

## Status

Phase 1 is implemented and validated on both dev and production.

The stack now supports a hybrid memory model with:

- shared conversational memory for durable recall
- context memory for "true right now" state
- registry for saved-content objects and review state
- a new wiki lane for compiled knowledge artifacts

## What Shipped

### Backend

- `memory-api` now exposes internal wiki endpoints for:
  - health
  - search
  - page fetch
  - proposal create
  - proposal list
  - proposal review
  - lint
- the unified recall router now classifies broad synthesis queries as wiki-first
- live lanes remain the fallback path when the wiki is weak, stale, or empty

### Agent-neutral write contract

Write-capable routes now support a shared actor envelope:

- `actor_type`
- `actor_id`
- `session_id`
- `source_client`
- `reason`

That means TARS/OpenClaw, Claude Code, Hermes, and future clients can all use
the same backend contracts instead of relying on OpenClaw-specific local files
or wrappers.

### OpenClaw workspace

The live workspace now includes:

- `./bin/wiki`
- `./bin/query-wiki`
- `WIKI_POLICY.md`
- updated `AGENTS.md`
- updated `TOOLS.md`

### Runtime model

- the Mac Obsidian vault remains canonical for wiki content
- the VPS/VM hosts:
  - a wiki mirror for runtime reads
  - a proposal queue
  - an approved outbox for sync-back into the canonical vault
- approved wiki proposals are review-gated and do not silently become canonical

## What We Validated

The following live checks passed:

- `./bin/wiki --help`
- `./bin/wiki health`
- `./bin/query-wiki "hybrid memory" --limit 3`
- `./bin/wiki proposals --status pending_review`
- `./bin/wiki lint --limit 10`
- `./bin/wiki propose ...`
- `./bin/wiki review --proposal-id ... --action approve`
- `./bin/wiki proposals --status approved`
- `./bin/recall-unified --query "Give me the deeper picture on the hybrid memory stack and how it has evolved"`

Observed production behavior:

- wiki proposal creation now succeeds after the frontmatter serialization fix
- approved proposals land in the VPS outbox
- actor metadata is preserved in proposal and review records
- synthesis-style router calls resolve to `primary_lane=wiki`

## Known Phase 1 Limits

- the canonical Obsidian wiki still needs human/agent hydration
- the live wiki can be structurally healthy while still returning sparse search
  results if the canonical vault has not been populated yet
- approved proposals are not automatically promoted into the Mac vault
- Phase 1 does not attempt bidirectional synchronization between file-native wiki
  pages and service-backed memory/context/registry data

## What To Do Next

### 1. Hydrate the canonical Obsidian wiki

Use the local vault as the source of truth and create the first real pages:

- `wiki/index.md`
- `wiki/log.md`
- `wiki/schema.md`
- a source page for the hybrid memory PDR
- a synthesis page for the Phase 1 system shape
- starter project/topic/entity pages as they prove useful

### 2. Start a review-driven sync-back loop

Use the repo scripts to:

1. scaffold the local vault wiki structure
2. sync approved VPS outbox items into the local review queue
3. review and promote selected pages into the canonical vault
4. mirror the updated canonical wiki pages back to the live VPS wiki mirror

### 3. Test hydration as an operating workflow

The next useful tests are not backend-only. They are workflow tests:

- can an approved proposal be reviewed comfortably in Obsidian?
- can it be promoted into the canonical vault with clean provenance?
- after live wiki mirror sync, does `query-wiki` return the expected page?
- does the router stay honest about wiki-vs-live provenance?

### 4. Build the first compounding corpus

Recommended first hydration targets:

- hybrid memory architecture
- active projects
- key companies and people that recur across chats, notes, and transcripts
- high-value saved sources that deserve source-summary pages

## Recommended Phase 2 Focus

- make the canonical Obsidian wiki operationally real, not just structurally live
- add a tighter human review loop for proposal promotion
- improve wiki search quality once the first meaningful page set exists
- add wiki-aware hydration/lint routines that flag stale or missing high-value
  pages

## Related Docs

- [architecture-memory.md](/Users/sgkmeyer/ai-automation-stack/ops/architecture-memory.md)
- [obsidian-vault-setup.md](/Users/sgkmeyer/ai-automation-stack/ops/obsidian-vault-setup.md)
- [obsidian-wiki-hydration.md](/Users/sgkmeyer/ai-automation-stack/ops/obsidian-wiki-hydration.md)
- [memory-external-interfaces.md](/Users/sgkmeyer/ai-automation-stack/ops/memory-external-interfaces.md)
- [WIKI_POLICY.md](/Users/sgkmeyer/ai-automation-stack/automation/openclaw/workspace/WIKI_POLICY.md)
