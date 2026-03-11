# MEMORY_POLICY_EXAMPLES.md

Use these as behavior examples in direct chats with Stephan.

## Durable Memory Write

User:
"Remember this: I met Dana from Stripe and she is open to advisor work."

Action:

- run `./bin/remember "I met Dana from Stripe and she is open to advisor work."`
- reply with a short confirmation

## Durable Memory Write With Tags

User:
"Make note of this: I prefer flat whites over drip coffee."

Action:

- run `./bin/remember "I prefer flat whites over drip coffee." --tags preference`

## Recall

User:
"What do you remember about Dana from Stripe?"

Action:

- run `./bin/recall-memory "Dana Stripe" --limit 5`
- summarize the result naturally

## Context Set

User:
"For now, my job search is focused on VP Sales roles at $50M-$120M ARR SaaS companies."

Action:

- run:
  `./bin/context-memory set --domain job_search --key status --value "Focused on VP Sales roles at 50M-120M ARR SaaS companies."`

## Context Get

User:
"What is my current job-search context?"

Action:

- run `./bin/context-memory get`
- summarize the relevant domain/key values

## Context Delete

User:
"Clear that job-search context."

Action:

- run `./bin/context-memory delete --domain job_search --key status`

## Do Not Write

User:
"Haha I should probably move to Italy one day."

Action:

- do not write durable memory automatically
- treat as casual conversation unless the user asks to save it

## Sensitive Material

User:
"Remember my API key is abc123..."

Action:

- do not silently store it
- warn that secrets should not be stored in durable memory unless explicitly intended

## Weak Recall Result

User:
"What do you remember about that coffee thing?"

Action:

- if needed, try a concise query like `coffee preference`
- if results are weak, say that recall is uncertain instead of pretending confidence
