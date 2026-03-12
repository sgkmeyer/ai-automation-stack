# Memory User Guide

This guide explains how to use the memory system as an end user through:

- OpenClaw for daily interaction
- Obsidian for structured notes and durable written memory
- Krisp for meeting transcripts and action-item capture

## What The System Is

Think of the memory system as having three input paths:

- **OpenClaw** for conversational memory
- **Obsidian** for authored notes
- **Krisp** for spoken conversations and meetings

All three end up in the same shared durable memory layer, so recall can span
across them.

## What To Put Where

Use **OpenClaw** for:

- "remember this" moments
- recalling what you already know about a person, company, or topic
- setting your current context or operating state
- asking for synthesis across prior memory

Use **Obsidian** for:

- daily notes
- curated notes
- project notes
- reference material you want to preserve in a structured written form

Use **Krisp** for:

- meeting transcripts
- conversation capture
- extracting action items from calls

## Current Reality

Today:

- OpenClaw is wired to the live shared memory layer
- Obsidian and Krisp can be ingested through the live memory interfaces
- the full automatic source-side wiring for Obsidian/Krisp may still be manual or semi-manual depending on your setup

So the user experience is:

- OpenClaw: conversational
- Obsidian: note-first, then ingest
- Krisp: transcript-first, then ingest

## Executive Coaching Pattern

If your goal is a true second-brain or executive-coaching system, use all three
memory shapes together:

- **Journal history** in Obsidian
- **Current truth** in the context register
- **Important transitions** as durable memory events

This matters because each answers a different question:

- journal: "what was happening over time?"
- context: "what is true right now?"
- durable event memory: "what important thing changed?"

### Recommended Structure

Use **Obsidian journal notes** for:

- daily or near-daily reflection
- work context
- energy and motivation patterns
- goals, blockers, and decisions
- relationship and life events

Use **context** for:

- current role
- current priorities
- current job search state
- temporary operating assumptions
- "for now" preferences

Use **durable memory writes** for:

- job changes
- major decisions
- commitments
- meaningful relationship updates
- important discoveries you want to recall later

### Example: Job Change

If your role changes, the best pattern is:

1. Update context with the new current truth.
2. Log a durable memory entry that the transition happened.
3. Capture the broader narrative in your journal.

That gives future LLM partners:

- the current state
- the historical event
- the surrounding narrative and reasoning

### Why This Is Better Than One Store

If you only keep the latest state:

- you lose the story of how things changed

If you only keep append-only history:

- recall may surface stale facts without a clear "current truth"

If you use all three together:

- you get chronology
- you get current accuracy
- you get better coaching and synthesis over time

### Recommended Cadence

- **During the day:** use OpenClaw for quick memory capture and recall
- **Daily or several times per week:** maintain an ongoing Obsidian journal
- **When something materially changes:** update context and log the transition

## OpenClaw Daily Use

OpenClaw is the main daily interface.

### Remember Something

Use natural language like:

- "Remember this: I met Dana from Stripe and she is open to advisor work."
- "Make note of this: I prefer flat whites over drip coffee."
- "Don't forget this: I need to send Alex the follow-up on Thursday."

Expected behavior:

- OpenClaw saves it into durable memory
- it confirms briefly that it was saved

### Recall Something

Ask naturally like:

- "What do you remember about Dana from Stripe?"
- "What do you remember about my VP Sales job search?"
- "Search memory for coffee preferences."

Expected behavior:

- OpenClaw runs a targeted recall
- it summarizes the result in normal language
- if nothing useful is found, it should say so directly

### Set Current Context

Use this when something is true **right now**, not forever.

Examples:

- "For now, my job search is focused on VP Sales roles at $50M-$120M ARR SaaS companies."
- "For now, assume I prefer walking meetings."

Expected behavior:

- OpenClaw stores that in the context register
- later it can use or retrieve that current-state context

### Get Current Context

Ask:

- "What is my current job-search context?"
- "What current preferences do you have stored?"

### Clear Context

Ask:

- "Clear that job-search context."
- "Delete my current coffee preference context."

### Ask For Synthesis

Examples:

- "What do you remember about my conversations with Dana?"
- "Summarize what you know about my current search."
- "What do you know about Figma from my notes and meetings?"

This is where the shared memory layer becomes valuable: OpenClaw can synthesize
across memories instead of just echoing one note back.

## Obsidian Use

Obsidian is for structured written memory.

### Best Uses

- Daily notes
- Meeting summaries
- Project logs
- Curated long-form notes
- Reference notes you may want to recall later

### Recommended Note Style

Keep the note usable as a normal note first. Memory ingest should be a side
effect, not the reason the note exists.

Helpful fields:

- clear title
- stable file path
- simple tags
- concise, readable content

Example note:

```md
# 2026-03-11

Met Lena at Figma and agreed to send a follow-up tomorrow with examples.

Tags: daily-note, networking
```

### How Obsidian Maps Into Memory

An ingested note is identified mainly by:

- source: `obsidian`
- source ref: the vault-relative file path

That means the same note can be re-ingested safely:

- first time -> `created`
- unchanged file -> `unchanged`
- edited file -> `updated`

### Current End-User Workflow

Current recommended path:

1. mirror the Mac vault to the VM
2. ingest selected notes from the VM mirror

Example sync:

```bash
scripts/sync-obsidian-vault.sh
```

Then ingest the note from the mirrored path:

Example:

```bash
ssh satoic-production '
  cd /home/ubuntu/ai-automation-stack &&
  scripts/memory-webhook.sh document \
    --source-ref Daily/2026-03-11.md \
    --file /home/ubuntu/obsidian-vault/Daily/2026-03-11.md \
    --tags daily-note,networking
'
```

Expected result:

- the note is stored in shared memory
- the same note can later be recalled through OpenClaw

### What Obsidian Is Good For

Use Obsidian when the information is:

- better written down than spoken
- part of a project or knowledge base
- something you want to refine over time
- something you may update and re-ingest later

## Krisp Use

Krisp is for capturing conversations and meetings.

### Best Uses

- sales calls
- networking calls
- 1:1s
- brainstorming sessions
- meetings where follow-ups matter

### What Happens On Transcript Ingest

A transcript ingest can create:

- a transcript summary entry
- optional action-item entries

That means later recall can find:

- the meeting itself
- the distilled summary
- action items derived from the meeting

### Current End-User Workflow

Preferred path now that Krisp webhook wiring is live:

- Krisp sends transcript-bearing webhook events directly to the memory stack
- the adapter normalizes them and ingests them automatically
- later recall should surface the conversation without extra user steps

Fallback path:

- if a Krisp delivery fails or you need to backfill an older meeting, ingest the transcript manually

Example:

```bash
scripts/memory-webhook.sh transcript \
  --source-ref krisp:2026-03-11-dana-call \
  --file ~/transcripts/dana-call.txt \
  --title "Dana Stripe Advisor Call" \
  --action-items "Send follow-up,Share intro options"
```

Expected result:

- the transcript summary is stored
- action items are stored as separate memory entries
- later OpenClaw recall can surface that conversation

### Krisp Webhook Validation

For replay-based validation from your laptop, use:

```bash
KRISP_WEBHOOK_SECRET=REPLACE_ME \
scripts/replay-krisp-webhook.sh \
  --payload workflows/governed/mem-06-krisp-webhook-adapter/fixtures/transcript-ready.json
```

Current note for dev validation:

- in the current queue-mode dev overlay, `http://100.82.169.113:5679` is the editor/UI service, not the production webhook listener
- dev Krisp replay currently needs to run VM-local against the `n8n-webhook` service, as documented in [ops/runbooks-memory.md](/Users/sgkmeyer/ai-automation-stack/ops/runbooks-memory.md)

For production Krisp configuration:

- URL: `https://n8n.satoic.com/webhook/memory/ingest/krisp`
- Header: `x-krisp-webhook-secret`
- Value: the secret stored in the `Krisp Webhook Header Auth` credential

### What Krisp Is Good For

Use Krisp when the information is:

- spoken rather than written
- time-sensitive
- tied to follow-up commitments
- useful to recall later but too inconvenient to summarize manually every time

## A Good Daily Workflow

A practical split:

### During The Day

Use OpenClaw to:

- remember quick facts
- recall people and commitments
- maintain current context

### After Meetings

Use Krisp transcripts to:

- capture the meeting
- preserve action items
- make meeting memory searchable later

### During Planning Or Reflection

Use Obsidian to:

- write clean notes
- maintain structured project memory
- create a durable written record worth re-ingesting

## Examples

### Example 1: Networking

1. You tell OpenClaw:
   "Remember this: Dana from Stripe is open to advisor work."
2. Later you ask:
   "What do you remember about Dana from Stripe?"
3. OpenClaw recalls the stored memory.

### Example 2: Daily Note

1. You write a daily note in Obsidian.
2. You ingest it into memory.
3. Later you ask OpenClaw:
   "What do you remember about my Figma follow-up?"
4. OpenClaw can retrieve the memory that came from the note.

### Example 3: Meeting Follow-Up

1. Krisp captures a meeting transcript.
2. You ingest the transcript with action items.
3. Later you ask OpenClaw:
   "What came out of my Dana call?"
4. OpenClaw can recall the summary and follow-up actions.

## What Not To Store

Do not use durable memory by default for:

- passwords
- API keys
- secret tokens
- financial account details

If something is highly sensitive, treat it separately unless you explicitly want
it persisted.

## What Success Looks Like

The memory system is working well if:

- OpenClaw can remember and recall important personal context
- Obsidian notes become searchable memory, not just static files
- Krisp transcripts turn into useful summaries and action items
- you can ask one question and get an answer that spans conversations, notes, and meetings

## Related Docs

- Obsidian setup guide: [obsidian-vault-setup.md](/Users/sgkmeyer/ai-automation-stack/ops/obsidian-vault-setup.md#L1)
- engineering interface doc: [memory-external-interfaces.md](/Users/sgkmeyer/ai-automation-stack/ops/memory-external-interfaces.md#L1)
- engineering runbook: [runbooks-memory.md](/Users/sgkmeyer/ai-automation-stack/ops/runbooks-memory.md#L1)
