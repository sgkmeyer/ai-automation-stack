# MEMORY_POLICY.md

This file defines how to use shared durable memory during direct chats with
Stephan.

## Goal

Use the shared memory layer to:

- remember durable personal facts and commitments
- recall prior context before answering memory-shaped questions
- maintain "true right now" context separately from long-term memory

Do not turn every conversation into a write. Be selective.

## Priority Order

1. Protect privacy and avoid storing secrets by default.
2. Prefer the shared memory layer for durable facts.
3. Prefer local workspace files only for working notes, summaries, and fallback.
4. Keep replies natural; do not dump raw JSON unless asked.

## Command Surface

- durable memory write:
  - `./bin/remember "..." --tags a,b`
- targeted recall:
  - `./bin/recall-memory "..." --limit 5`
- current-state context:
  - `./bin/context-memory set --domain DOMAIN --key KEY --value VALUE`
  - `./bin/context-memory get`
  - `./bin/context-memory delete --domain DOMAIN --key KEY`

## When To Write Durable Memory

Write when one of these is true:

- the user explicitly says "remember this", "make note of this", "don't forget this"
- the user states a stable personal preference or standing fact
- the user records a commitment, decision, or follow-up worth retrieving later
- the user shares a relationship/contact fact likely to matter later
- the user confirms that something should be saved

Do not write durable memory when:

- the message is casual banter
- the fact is obviously temporary and better suited to context
- the content is sensitive or secret and the user did not explicitly ask to store it
- the statement is uncertain, joking, or speculative

## When To Recall

Recall before answering when:

- the user asks "what do you remember about ..."
- the user asks for prior context on a person, company, project, or topic
- the user asks for synthesis across earlier conversations
- the answer likely depends on prior durable memory

Do not recall for:

- simple greetings
- standalone factual questions with no sign memory is needed
- low-value chatter where memory lookup would just add latency

## When To Use Context Register

Use context for information that is true right now, such as:

- current priorities
- current preferences in force
- active job search state
- temporary operating assumptions
- the current status of an ongoing effort

Examples:

- "For now, assume I prefer walking meetings" -> context
- "My current job-search focus is VP Sales roles" -> context
- "I like flat whites" -> durable memory, not context, unless framed as temporary

## Response Behavior

After a successful write:

- briefly confirm what was saved
- mention whether it was stored as durable memory or current context when useful

After a recall:

- summarize the relevant result naturally
- include uncertainty if the match is weak
- avoid pasting the full raw response unless asked

If no result is found:

- say so directly
- optionally ask whether the user wants it remembered now

## Sensitivity Rules

Do not store by default:

- passwords
- API keys
- private tokens
- financial account numbers
- high-risk personal data unless explicitly instructed

If the user explicitly asks to store sensitive material, confirm the request in a
careful way instead of silently persisting it.

## Query Style

Keep recall queries short and concrete.

Good:

- `Dana Stripe advisor work`
- `job search VP Sales`
- `flat white coffee preference`

Bad:

- whole paragraphs
- vague pronouns with no entity anchor
- multiple unrelated topics in one query
