#!/usr/bin/env bash

set -euo pipefail

LOCAL_VAULT="${OBSIDIAN_LOCAL_VAULT:-/Users/sgkmeyer/vaults/second-brain}"
WIKI_ROOT="${LOCAL_VAULT}/wiki"

[[ -d "${LOCAL_VAULT}" ]] || {
  printf 'error: local vault not found: %s\n' "${LOCAL_VAULT}" >&2
  exit 1
}

mkdir -p \
  "${LOCAL_VAULT}/inbox" \
  "${LOCAL_VAULT}/raw/articles" \
  "${LOCAL_VAULT}/raw/transcripts" \
  "${LOCAL_VAULT}/raw/docs" \
  "${LOCAL_VAULT}/raw/assets" \
  "${WIKI_ROOT}/people" \
  "${WIKI_ROOT}/companies" \
  "${WIKI_ROOT}/projects" \
  "${WIKI_ROOT}/topics" \
  "${WIKI_ROOT}/syntheses" \
  "${WIKI_ROOT}/sources" \
  "${LOCAL_VAULT}/state" \
  "${LOCAL_VAULT}/memory" \
  "${LOCAL_VAULT}/registry" \
  "${LOCAL_VAULT}/_review/wiki-proposals/pages" \
  "${LOCAL_VAULT}/_review/wiki-proposals/metadata"

if [[ ! -f "${WIKI_ROOT}/index.md" ]]; then
  cat > "${WIKI_ROOT}/index.md" <<'EOF'
# Wiki Index

This is the top-level navigation page for the canonical Obsidian wiki.

## Control Pages

- [[schema]]
- [[log]]

## Seed Pages

- [[syntheses/hybrid-memory-stack-phase-1]]
- [[sources/hybrid-memory-stack-pdr]]

## Collections

- [[people]]
- [[companies]]
- [[projects]]
- [[topics]]
- [[syntheses]]
- [[sources]]

## Working Rules

- The Mac Obsidian vault is canonical for wiki content.
- The VPS outbox is a review queue, not the final source of truth.
- Promote approved pages selectively and keep the wiki high-signal.
EOF
fi

if [[ ! -f "${WIKI_ROOT}/log.md" ]]; then
  cat > "${WIKI_ROOT}/log.md" <<'EOF'
# Wiki Log

Append-only record of notable wiki maintenance events.

- 2026-04-10T00:00:00Z initialized canonical wiki scaffold for Hybrid Memory Stack Phase 1
EOF
fi

if [[ ! -f "${WIKI_ROOT}/schema.md" ]]; then
  cat > "${WIKI_ROOT}/schema.md" <<'EOF'
# Wiki Schema

Required frontmatter:

- `title`
- `type`
- `status`
- `tags`
- `source_refs`
- `updated_at`
- `confidence`

Page types:

- `people`
- `companies`
- `projects`
- `topics`
- `syntheses`
- `sources`

Recommended sections by page type:

- `people`: who they are, relationship/context, key facts, source refs
- `companies`: what it is, current relevance, open questions, source refs
- `projects`: goal, current state, decisions, next questions, source refs
- `topics`: concept summary, operating guidance, linked pages, source refs
- `syntheses`: compiled narrative across multiple sources
- `sources`: summary, why it matters, source refs, linked pages

Rules:

- prefer synthesized pages over raw-note dumps
- keep source refs explicit
- use wiki pages for compounding knowledge, not temporary state
- keep `log.md` append-only
EOF
fi

if [[ ! -f "${WIKI_ROOT}/sources/hybrid-memory-stack-pdr.md" ]]; then
  cat > "${WIKI_ROOT}/sources/hybrid-memory-stack-pdr.md" <<'EOF'
---
title: Hybrid Memory Stack PDR
type: sources
status: seeded
tags:
- memory
- wiki
- architecture
source_refs:
- HYBRID_MEMORY_STACK_PDR.md
updated_at: 2026-04-10T00:00:00Z
confidence: high
---

# Hybrid Memory Stack PDR

This source page tracks the planning document that defined the Hybrid Memory
Stack direction.

## Why It Matters

The PDR established the canonical lane split between:

- shared conversational memory
- runtime context/state
- registry
- an Obsidian-native wiki for synthesized knowledge

## Notes

- Phase 1 keeps memory/context/registry service-backed.
- The wiki is the canonical home only for compiled knowledge artifacts.
- Promotion into the wiki is selective and review-gated.
EOF
fi

if [[ ! -f "${WIKI_ROOT}/syntheses/hybrid-memory-stack-phase-1.md" ]]; then
  cat > "${WIKI_ROOT}/syntheses/hybrid-memory-stack-phase-1.md" <<'EOF'
---
title: Hybrid Memory Stack Phase 1
type: syntheses
status: seeded
tags:
- memory
- wiki
- phase-1
source_refs:
- ops/hybrid-memory-phase1-closeout.md
- ops/architecture-memory.md
- HYBRID_MEMORY_STACK_PDR.md
updated_at: 2026-04-10T00:00:00Z
confidence: medium
---

# Hybrid Memory Stack Phase 1

Phase 1 established a hybrid memory model that separates operational memory
from compiled knowledge.

## Canonical ownership

- shared conversational memory owns durable recall facts
- context memory owns true-right-now state
- registry owns saved-content objects and review state
- the Obsidian wiki owns synthesized knowledge artifacts

## Runtime shape

- the Mac Obsidian vault is canonical for wiki content
- the VPS hosts a runtime mirror plus proposal/review outbox
- broad synthesis queries route wiki-first with live-lane fallback

## Important limits

- approved proposals are not yet auto-promoted into the canonical vault
- sparse wiki results are expected until the canonical vault is hydrated
- the system still depends on clear provenance between wiki and live lanes

## Next moves

- hydrate starter pages in Obsidian
- pull approved proposals into the review queue
- promote selected pages into the canonical vault
- mirror the canonical vault back to the VPS for runtime reads
EOF
fi

printf 'Wiki scaffold ready at %s\n' "${WIKI_ROOT}"
