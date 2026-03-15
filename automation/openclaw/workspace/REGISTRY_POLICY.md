# REGISTRY_POLICY.md

This file defines how to use the shared content registry during direct chats
with Stephan.

## Goal

Use the registry layer to:

- find links, articles, videos, and saved web pages Stephan explicitly captured
- answer saved-content questions from the registry before falling back to memory
- curate the reading inbox without dumping long raw lists

Registry is the source of truth for saved-link items. Memory is still the
broader second-brain layer for durable facts and cross-system recall.

## Command Surface

- general registry CLI:
  - `./bin/registry`
- friendly wrappers:
  - `./bin/query-registry "..." --limit 5`
  - `./bin/list-registry --limit 3 --review-state inbox --sort oldest`
  - `./bin/review-registry ITEM_ID archive`

## When To Use Registry First

Use registry first when the user asks questions like:

- "what did I save about ..."
- "show my reading inbox"
- "show my saved items on ..."
- "what did I just save?"
- "show the summary/takeaways for this saved link"
- "archive the first one"

Do not start with memory recall for those requests unless the user clearly wants
broader cross-system synthesis instead of saved-link retrieval.

## Query Style

Keep registry queries short and concrete.

Good:

- `AI GTM`
- `Riipen partnerships`
- `sales leadership podcast`

Bad:

- whole paragraphs
- multi-part unrelated requests in one query
- vague pronouns with no topic anchor

## Inbox Behavior

When listing inbox items:

- prefer `./bin/list-registry --limit 3 --review-state inbox --sort oldest`
- summarize the count and show a small curated page
- offer to continue, summarize all, or archive/review specific items

Do not dump 20 items into chat unless the user explicitly asks for the raw list.

## Review Actions

Supported review actions:

- `mark_reviewed`
- `archive`
- `mark_inbox`

When the user refers to items positionally, map carefully:

- "archive the first one" -> archive the first item from the most recent list you just showed
- if there is any ambiguity, ask a short clarification instead of mutating the wrong item

## Response Behavior

After a registry query:

- answer naturally
- include the original link when useful
- prefer stored `summary`, `why_it_matters`, and `key_takeaways`
- avoid pretending the registry contains information it does not

After a list:

- say how many items matched
- show only the top page unless asked for more

If no items are found:

- say so directly
- optionally suggest a tighter search term

## Boundary With Memory

- registry = saved links and their summaries
- memory = durable facts, conversations, notes, and cross-system recall

If the user asks something like:

- "what did I save about AI GTM?" -> registry first
- "what do you remember about my AI GTM thinking overall?" -> memory first, optionally mention registry items if relevant
