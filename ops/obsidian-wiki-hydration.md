# Obsidian Wiki Hydration Guide

## Purpose

This guide turns the Phase 1 wiki lane into a real working loop.

The goal is to:

1. scaffold the canonical local Obsidian wiki
2. pull approved VPS proposals into a local review queue
3. promote selected pages into the canonical vault
4. mirror the canonical vault back to the VPS for runtime reads

## Canonical Model

- local Mac Obsidian vault: canonical wiki
- VPS wiki outbox: approved-but-not-yet-canonical proposal queue
- VPS wiki mirror: runtime-readable copy after sync

## Step 1: Bootstrap the local wiki

Use:

```bash
./scripts/bootstrap-obsidian-wiki.sh
```

This creates a richer wiki scaffold under the local vault, including:

- `wiki/index.md`
- `wiki/log.md`
- `wiki/schema.md`
- seed synthesis/source pages for the hybrid memory rollout
- review queue folders under `_review/wiki-proposals`

Default local vault:

```text
/Users/sgkmeyer/vaults/second-brain
```

## Step 2: Inspect the canonical wiki in Obsidian

Open the local vault in Obsidian and review:

- `wiki/index.md`
- `wiki/schema.md`
- `wiki/syntheses/hybrid-memory-stack-phase-1.md`
- `wiki/sources/hybrid-memory-stack-pdr.md`

This is the baseline navigation and schema surface for early hydration.

## Step 3: Pull approved VPS proposals into the local review queue

Use:

```bash
./scripts/sync-wiki-outbox.sh
```

This copies the VPS review outbox into:

```text
<vault>/_review/wiki-proposals
```

Use `--dry-run` first if you want a preview.

## Step 4: Promote an approved proposal into the canonical vault

Use:

```bash
./scripts/promote-wiki-outbox.sh --proposal-id UUID
```

What this does:

- reads the approved proposal metadata from the local review queue
- copies the proposed page into the canonical vault path
- appends a line to `wiki/log.md`

The script is intentionally conservative:

- it refuses to overwrite an existing canonical page unless `--force` is used
- it only promotes from the local review queue, not directly from the VPS

## Step 5: Mirror the canonical vault back to the VPS

Use:

```bash
./scripts/sync-live-wiki-mirror.sh
```

This refreshes the VPS-side wiki mirror used by runtime wiki reads.

Important distinction:

- `./scripts/sync-live-wiki-mirror.sh` updates the live wiki lane mirror
- `./scripts/sync-obsidian-vault.sh` updates the broader Obsidian vault mirror
  used for note-ingest workflows

## Step 6: Re-test runtime reads

After a canonical page is present on the VPS mirror, test:

```bash
./bin/query-wiki "hybrid memory" --limit 5
./bin/recall-unified --query "Give me the deeper picture on the hybrid memory stack"
```

Expected direction:

- `query-wiki` should start returning the new page
- router calls should still disclose wiki-vs-live fallback behavior honestly

## First Hydration Backlog

### Control pages

- confirm `index.md`, `log.md`, and `schema.md`
- keep `log.md` append-only
- keep `schema.md` as the source for page conventions

### First content pages

- `wiki/sources/hybrid-memory-stack-pdr.md`
- `wiki/syntheses/hybrid-memory-stack-phase-1.md`
- one project page for the memory system rollout
- one topic page for hybrid memory architecture

### Next pages after that

- high-signal people pages from repeated interactions
- company pages for recurring counterparties
- source-summary pages for important saved articles
- project dossiers that accumulate decisions over time

## Testing Checklist

- local bootstrap created the expected folders and control pages
- approved proposal sync copied files into `_review/wiki-proposals`
- promotion copied a reviewed page into `wiki/...`
- `wiki/log.md` recorded the promotion
- VPS mirror sync completed cleanly
- `query-wiki` returns the hydrated page after sync

## Operator Notes

- treat the local vault as canonical even when the VPS mirror is ahead temporarily
- do not bypass the review queue for routine proposal promotion
- prefer a few high-quality pages over a large number of thin pages

## Related Scripts

- [bootstrap-obsidian-wiki.sh](/Users/sgkmeyer/ai-automation-stack/scripts/bootstrap-obsidian-wiki.sh)
- [sync-wiki-outbox.sh](/Users/sgkmeyer/ai-automation-stack/scripts/sync-wiki-outbox.sh)
- [promote-wiki-outbox.sh](/Users/sgkmeyer/ai-automation-stack/scripts/promote-wiki-outbox.sh)
- [sync-live-wiki-mirror.sh](/Users/sgkmeyer/ai-automation-stack/scripts/sync-live-wiki-mirror.sh)
- [sync-obsidian-vault.sh](/Users/sgkmeyer/ai-automation-stack/scripts/sync-obsidian-vault.sh)
