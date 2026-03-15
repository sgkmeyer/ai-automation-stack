# Roadmap Priorities

Locked on 2026-03-14.

This is the current prioritization baseline for the Personal OS roadmap. Use it
to decide what enters implementation next. This list is intentionally ordered to
optimize for:

1. trust and durability first
2. daily usefulness second
3. coherence third
4. operating-system feel last

## Must-Have Now

1. Security and secret-handling polish
2. Registry capture hardening
3. Memory hygiene and deduplication
4. Openclaw capability hardening
5. State reversibility
6. Observability and reasoning traceability
7. Cost and loop governance
8. Unified recall router v1

## Next

9. Registry retrieval quality
10. Lightweight tasks / open-loops layer
11. Daily executive queries
12. Promotion / curation actions
13. Entity / project centric linking
14. Cross-store synthesis rules

## Later

15. Scheduled review loops
16. TARS operating blueprint
17. Orchestrator portability
18. Cheap review surface
19. Task/entity/source linkage refinement

## Defer / Avoid

20. Graph-specific architecture
21. Heavy custom dashboard app
22. Dedicated comms / briefing lane
23. Too many specialist agents

## Execution Order

### Trust Layer

- items `1-7`

### Daily Utility

- items `8-12`

### Coherence

- items `13-14`

### Operating-System Feel

- items `15-19`

## Architectural Notes

- Do not build a sophisticated router on top of noisy capture or weakly
  normalized stores.
- Do not give TARS stronger write authority without reversibility,
  observability, and loop/cost guardrails.
- Tasks should be designed with entity/project anchoring in mind, even if the
  first version is lightweight.
- Keep graph ambitions relational for now. Do not build graph-specific
  substrate prematurely.
- Favor cheap surfaces over custom UI until retrieval, tasks, and review loops
  are trustworthy.

## Next Session Starting Point

If there is no higher-priority operational incident, the recommended next
implementation tranche is:

1. Registry capture hardening
2. Memory hygiene and deduplication
3. Openclaw capability hardening follow-up
4. State reversibility design
5. Unified recall router v1
