# WIKI_POLICY.md

This file defines how to use the shared wiki lane.

## Goal

Use the wiki for compiled, human-readable knowledge artifacts.

Prefer the wiki when the user wants:

- a deeper picture
- a project or company view
- longitudinal synthesis
- a browsable knowledge artifact that should compound over time

## What Belongs In The Wiki

- person pages
- company pages
- project pages
- topic pages
- source summary pages
- higher-value syntheses that combine multiple sources

## What Does Not Belong In The Wiki

- every small memory fact
- temporary runtime state
- saved-link inbox objects
- raw transcripts copied verbatim
- duplicate local boot summaries

## Command Surface

- search/read:
  - `./bin/wiki health`
  - `./bin/query-wiki "..." --limit 5`
  - `./bin/wiki page --page-ref wiki/projects/example.md`
- proposal flow:
  - `./bin/wiki propose --page-type projects --title "Example" --content "..."`
  - `./bin/wiki proposals --status pending_review`
  - `./bin/wiki review --proposal-id UUID --action approve`
- maintenance:
  - `./bin/wiki lint`

## Routing Rule

- use `./bin/recall-unified` for natural recall when the best store is unclear
- use `./bin/query-wiki` first for deeper synthesis questions
- fall back to memory, transcripts, or registry when wiki coverage is weak or stale

## Write Rule

- prefer a single canonical write target by default
- propose wiki updates selectively for high-value synthesis
- do not treat wiki proposals as canonical until they are reviewed
