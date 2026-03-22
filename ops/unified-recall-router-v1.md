# Unified Recall Router v1

Locked on 2026-03-21 as the design baseline for Tranche B.

## Goal

Make TARS feel like one recall interface across multiple stores without
flattening those stores into one mushy system.

The router should:

- classify the user's recall intent
- choose the best primary lane
- evaluate confidence and result density
- fall back selectively when needed
- expose enough provenance to debug bad answers

## Non-Goals

- do not merge all stores into one index
- do not synthesize across stores by default
- do not hide uncertainty when results are weak
- do not let the router silently override store boundaries

## Store Lanes

### Registry

Use for:

- saved links
- articles/videos/posts
- reading inbox
- saved-content summaries and takeaways

Current surface:

- `./bin/query-registry`
- `./bin/list-registry`
- `./bin/review-registry`

### Transcripts

Use for:

- what someone said
- meeting summaries
- action items and follow-ups
- what happened in calls

Current surface:

- memory recall with transcript-shaped query policy
- transcript/action-item rows in `memory.entries`

### Memory

Use for:

- broad durable knowledge
- person/company/project history
- preferences
- decisions and standing facts

Current surface:

- `./bin/recall-memory`
- `./bin/context-memory` for current truth when applicable

### Current Context

Use for:

- current session state
- latest working assumptions
- "just now" or "today in this thread" style questions

Current surface:

- context register
- recent chat/session state handled by TARS/Openclaw

### Future Tasks / Decisions

Reserve a lane now so the router contract does not need redesign later.

Use for:

- open loops
- waiting-ons
- blocked items
- pending decisions

## Core Design Rule

Do not fan out across stores by default.

The router should:

1. classify intent
2. select a primary lane
3. evaluate confidence and density
4. only fall back when policy allows it

This keeps answers sharper and easier to trust.

## Two-Stage Routing Model

### Stage 1: Intent Classification

Classify the user's question into one of these intent types:

1. `saved_content_lookup`
2. `conversation_recall`
3. `durable_knowledge_recall`
4. `current_context_lookup`
5. `task_or_open_loop_recall`
6. `broad_synthesis`

Intent classification should be explicit in router logs.

### Stage 2: Lane Selection

Given the intent type, choose:

- `primary_lane`
- `secondary_lane`
- `fallback_policy`

Lane selection is policy-driven, not just keyword-triggered.

## Routing Matrix

### 1. Saved Content Lookup

Examples:

- "what did I save about AI GTM?"
- "show my reading inbox"
- "what did I just save?"
- "show the summary for that saved link"

Primary lane:

- `registry`

Secondary lane:

- `memory`

Fallback rules:

- only consult `memory` when registry confidence/density is weak or the user is
  clearly asking for broader remembered thinking rather than the saved item

Typical signals:

- save
- saved
- link
- article
- post
- video
- bookmark
- registry
- reading inbox

### 2. Conversation Recall

Examples:

- "what did Dana say about lighthouse accounts?"
- "summarize my call with Jennifer"
- "what were the action items from Thursday?"
- "what happened in today's calls?"

Primary lane:

- `transcripts`

Secondary lane:

- `memory`

Fallback rules:

- consult `memory` when transcript results are thin or when a distilled summary
  likely exists
- do not hit registry unless the user also references saved content

Typical signals:

- call
- meeting
- conversation
- transcript
- said
- discussed
- action items
- follow-up

### 3. Durable Knowledge Recall

Examples:

- "what do you remember about Riipen?"
- "what do you know about Dana?"
- "remind me what you know about LearnAid"

Primary lane:

- `memory`

Secondary lane:

- `transcripts`

Fallback rules:

- consult transcripts when the entity is heavily conversation-driven or memory
  results are thin
- do not consult registry unless the user asks about saved content specifically

Typical signals:

- remember
- know about
- background
- history
- preference
- profile

### 4. Current Context Lookup

Examples:

- "what are we focused on today?"
- "what did we just decide?"
- "what's the latest on this?"

Primary lane:

- `current_context`

Secondary lane:

- `memory` or `transcripts`, depending on entity/time cues

Fallback rules:

- prefer recency over breadth
- fall back only when the current-context lane is clearly insufficient

Typical signals:

- today
- latest
- current
- just now
- in this chat
- this thread

### 5. Task / Open-Loop Recall

Examples:

- "what are my open loops?"
- "what am I waiting on?"
- "what decisions are pending?"

Primary lane:

- `tasks`

Secondary lane:

- `memory`

Fallback rules:

- reserved for future implementation

### 6. Broad Synthesis

Examples:

- "brief me on Riipen"
- "what changed this week on LearnAid?"
- "give me the full picture on Dana"

Primary lane:

- `memory`

Secondary lane:

- chosen by entity/time/source cues

Fallback rules:

- broad synthesis is the main case where cross-store fanout is expected
- still keep it bounded and explain what stores were used

## Confidence and Density Model

Every lane response should expose both:

- `confidence`
- `result_density`

### Confidence

A normalized score from `0.0` to `1.0` answering:

- how likely is this lane to satisfy the user intent?

Interpretation:

- `0.80 - 1.00` strong
- `0.55 - 0.79` usable but may merit fallback
- `0.00 - 0.54` weak

### Result Density

One of:

- `empty`
- `thin`
- `narrow_high_confidence`
- `medium`
- `rich`

Why density matters:

- one strong direct hit may be better than many noisy weak hits
- thin results should often trigger fallback or explicit disclosure

## Fallback Policy

Fallback should be policy-driven, not automatic.

### Fallback should happen when

- primary lane confidence is below threshold
- result density is `empty` or `thin`
- the intent class allows a secondary lane
- the question is broad enough to justify another lane

### Fallback should not happen when

- the primary lane has a strong narrow-high-confidence result
- the secondary lane is likely to add noise rather than clarity
- the question is clearly store-specific

### Recommended v1 thresholds

- strong direct answer:
  - confidence `>= 0.80`
  - density `narrow_high_confidence`, `medium`, or `rich`
- fallback candidate:
  - confidence `< 0.80`
  - or density `thin`
- thin-result disclosure:
  - confidence `< 0.55` across attempted lanes

## Answer Modes

### 1. Direct Answer

Use when:

- one lane returns a strong answer

Behavior:

- answer directly
- do not mention extra stores unless useful

### 2. Routed With Fallback

Use when:

- primary lane is weak/thin
- secondary lane helps materially

Behavior:

- synthesize carefully
- be transparent when the answer used more than one lane

### 3. Thin Result Disclosure

Use when:

- no lane produced a strong answer

Behavior:

- say what was checked
- say the result is weak/thin
- avoid false confidence

## Normalized Lane Result Contract

Each lane should normalize into a shape like:

```json
{
  "intent_type": "conversation_recall",
  "lane": "transcripts",
  "query": "Dana lighthouse accounts",
  "routing_reason": "question asks what a person said in a meeting",
  "confidence": 0.82,
  "result_density": "medium",
  "fallback_recommended": false,
  "results": [
    {
      "id": "uuid",
      "title": "Stephan <> Dana",
      "summary": "Dana emphasized lighthouse accounts...",
      "source_type": "transcript_summary",
      "source_ref": "krisp:...",
      "canonical_url": null,
      "occurred_at": "2026-03-12T17:01:25Z",
      "entity_refs": ["Dana", "Riipen"],
      "citation": "Krisp transcript summary",
      "score": 0.91
    }
  ],
  "notes": {
    "secondary_lane": "memory",
    "fallback_used": false
  }
}
```

### Required top-level fields

- `intent_type`
- `lane`
- `query`
- `routing_reason`
- `confidence`
- `result_density`
- `fallback_recommended`
- `results`

### Required result fields

- `id`
- `title`
- `summary`
- `source_type`
- `occurred_at`
- `score`

### Optional result fields

- `source_ref`
- `canonical_url`
- `entity_refs`
- `citation`
- `review_state`
- `why_it_matters`
- `key_takeaways`

## Observability Schema

For every routed recall, log:

- original user query
- classified intent type
- primary lane
- secondary lane
- routing reason
- normalized query sent to the lane
- lane confidence
- result density
- whether fallback was recommended
- whether fallback was used
- final answer mode

Minimum operator-visible example:

```json
{
  "query": "what did I save about AI GTM?",
  "intent_type": "saved_content_lookup",
  "primary_lane": "registry",
  "secondary_lane": "memory",
  "routing_reason": "saved-content wording plus topic lookup",
  "primary_confidence": 0.88,
  "primary_density": "medium",
  "fallback_used": false,
  "answer_mode": "direct_answer"
}
```

## Implementation Touchpoints

### Openclaw Workspace

Needs:

- routing policy docs
- examples of which wrapper to use when
- answer-mode guidance

Likely files:

- [`AGENTS.md`](/Users/sgkmeyer/ai-automation-stack/automation/openclaw/workspace/AGENTS.md)
- [`MEMORY_POLICY.md`](/Users/sgkmeyer/ai-automation-stack/automation/openclaw/workspace/MEMORY_POLICY.md)
- [`REGISTRY_POLICY.md`](/Users/sgkmeyer/ai-automation-stack/automation/openclaw/workspace/REGISTRY_POLICY.md)

### Wrapper Layer

May need:

- a higher-level routed recall wrapper
- or consistent output normalization from existing wrappers

Likely files:

- `automation/openclaw/workspace/bin/*`
- `scripts/memory-webhook.sh`
- registry wrapper scripts

### Memory API / Registry API

May need:

- normalized response adapters
- richer confidence/density metadata
- explicit transcript-vs-memory lane handling

Likely files:

- [`automation/memory-api/app/routes/recall.py`](/Users/sgkmeyer/ai-automation-stack/automation/memory-api/app/routes/recall.py)
- [`automation/memory-api/app/routes/registry.py`](/Users/sgkmeyer/ai-automation-stack/automation/memory-api/app/routes/registry.py)

### Documentation / Runbooks

Needs:

- router policy docs
- operator debugging guidance
- UAT prompts and expected routed behavior

## Example Queries

### Query

`what did I save about AI GTM?`

Expected:

- intent `saved_content_lookup`
- primary `registry`
- direct answer if registry result is medium or rich

### Query

`what did Dana say about lighthouse accounts?`

Expected:

- intent `conversation_recall`
- primary `transcripts`
- fallback to memory only if transcript result is thin

### Query

`what do you remember about Riipen?`

Expected:

- intent `durable_knowledge_recall`
- primary `memory`
- fallback to transcripts if memory is thin

### Query

`what happened today?`

Expected:

- intent depends on prompt context:
  - current-context-first if asking about this session
  - transcript-first if framed as calls/meetings
  - broad synthesis if clearly across multiple sources

### Query

`what are my open loops?`

Expected:

- reserved task lane later
- until task layer exists, be explicit about limitations

## Definition of Done

Unified recall router v1 is ready for implementation when:

- intent classes are explicit
- routing matrix is explicit
- confidence and density vocabulary is explicit
- fallback rules are explicit
- normalized lane contract is explicit
- observability requirements are explicit

## Immediate Next Step

Implement the smallest viable router slice:

1. registry vs transcript vs memory intent classification
2. normalized lane result wrapper
3. routing trace log
4. direct answer vs fallback vs thin-result disclosure behavior
