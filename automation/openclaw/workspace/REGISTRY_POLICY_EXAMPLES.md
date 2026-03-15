# REGISTRY_POLICY_EXAMPLES.md

Use these as behavior examples in direct chats with Stephan.

## Query Saved Content

User:
"What did I save about AI GTM?"

Action:

- run `./bin/query-registry "AI GTM" --limit 5`
- summarize the best matches naturally

## Reading Inbox

User:
"Show my reading inbox."

Action:

- run `./bin/list-registry --limit 3 --review-state inbox --sort oldest`
- give a curated page, not a long dump

## Recent Save

User:
"What did I just save?"

Action:

- run `./bin/list-registry --limit 1 --sort newest`
- summarize the latest item

## Archive An Item

User:
"Archive the first one."

Action:

- use the item id from the list you just showed
- run `./bin/review-registry ITEM_ID archive`
- confirm the item was archived

## Registry vs Memory

User:
"What did I save about Riipen partnerships?"

Action:

- use `./bin/query-registry "Riipen partnerships" --limit 5`

User:
"What do you remember about my Riipen partnership conversations overall?"

Action:

- start with `./bin/recall-memory "Riipen partnerships" --limit 5`
- use registry only if it helps round out the answer
