# Content Registry User Guide

This guide explains how to use the content registry as an end user.

The content registry is your private saved-link system for:

- articles
- YouTube videos
- X posts
- TikTok links
- normal web pages you want to come back to later

The registry is **not** the same thing as memory:

- the **registry** is the source of truth for saved links and their summaries
- **memory** is still the broader second-brain layer for cross-system recall

## What The Registry Is

Think of the registry as a structured reading and interest inbox.

When you save a link, the system tries to:

1. normalize the URL
2. deduplicate it against anything you already saved
3. fetch and summarize it
4. store:
   - original link
   - canonical link
   - title
   - summary
   - why it matters
   - key takeaways
   - source type
   - save history
   - inbox / reviewed / archived state

## Current Reality

As of March 14, 2026:

- the registry backend is live in production
- TARS can query it through the registry workflows and the Openclaw registry wrapper
- the current capture endpoint is:
  - `https://n8n.satoic.com/webhook/registry/capture`
- capture is protected by the `x-registry-webhook-secret` header
- true Tailnet-only shortcut ingress is still a follow-up, not live yet

This means the system is usable now, but the iPhone Shortcut still relies on a
secret-protected public endpoint instead of a dedicated Tailnet-private one.

## Best Uses

Use the registry for:

- "I want to come back to this later"
- "this looks relevant to my interests"
- "this might matter for work, GTM, AI, hiring, or strategy"
- "I don’t want to lose this link"

Do **not** use the registry for:

- random files
- handwritten notes without a URL
- things that should immediately become durable memory facts

## What Happens When You Save A Link

When you save a link successfully:

1. the system creates or updates a canonical registry item
2. it stores the save event separately as capture history
3. it places the item in `inbox`
4. it processes the link in the background
5. TARS can later query, list, or review it

If you save the same content more than once:

- you should get **one canonical item**
- plus multiple capture events attached to it

## What Gets Stored

For each canonical registry item, v1 stores:

- `original_url`
- `canonical_url`
- `source_kind`
- `title`
- `summary`
- `why_it_matters`
- `key_takeaways`
- `topics`
- `review_state`
- `processing_status`
- capture history
- raw archive path for the fetched source material

This is what makes the registry useful later for recall and, eventually,
interest-graph building.

## Known V1 Limitations

You should expect these behaviors in v1:

- **Web pages** are fetched and summarized normally
- **YouTube** should prefer transcript/caption style extraction when available
- **X and TikTok** are treated more conservatively and may only produce
  metadata-style summaries
- items are **not** auto-promoted into memory
- there is **no separate web UI** yet
- browsing happens through TARS

## Set Up The iPhone Shortcut

The current live setup uses an iPhone Share Sheet Shortcut that posts directly
to the registry capture endpoint.

### Values You Need

Use these exact live values:

- URL:
  - `https://n8n.satoic.com/webhook/registry/capture`
- Header name:
  - `x-registry-webhook-secret`
- Header value:
  - read it locally from:
    - `/tmp/registry_webhook_secret_prod_2026-03-13`

To view the current secret on your Mac without pasting it into chat:

```bash
cat /tmp/registry_webhook_secret_prod_2026-03-13
```

### Build The Shortcut

On iPhone:

1. Open the `Shortcuts` app.
2. Tap `+` to create a new shortcut.
3. Name it:
   - `Save to TARS Registry`
4. Tap the info/settings area for the shortcut and enable:
   - `Show in Share Sheet`
5. Under Share Sheet types, make sure it accepts:
   - `URLs`
   - `Text`
   - `Safari web pages` if available

### Add The Actions

Add these actions in order:

1. `Get Text from Input`
2. `Get URLs from Text`
3. `Get First Item from URLs`
4. `If`:
   - `Item from List` `has any value`
5. Inside the `If` block:
   - add `Ask for Input`
   - prompt text:
     - `Add a short note?`
   - input type:
     - `Text`
6. Add `Get Contents of URL`

Configure `Get Contents of URL` like this:

- Method:
  - `POST`
- URL:
  - `https://n8n.satoic.com/webhook/registry/capture`
- Headers:
  - `x-registry-webhook-secret` = the value from `/tmp/registry_webhook_secret_prod_2026-03-13`
  - `Content-Type` = `application/json`
- Request Body:
  - `JSON`

JSON fields:

- `url`
  - value: `Item from List`
- `note`
  - value: the result of `Ask for Input`
- `capture_channel`
  - value: `ios_shortcut`

7. Add `Show Notification`
   - text:
     - `Saved to TARS Registry`

8. In the `Otherwise` block, optionally add:
   - `Show Notification`
   - text:
     - `No URL found to save`

### Minimal Shortcut Logic

The payload should look like:

```json
{
  "url": "<shared url>",
  "note": "<optional short note>",
  "capture_channel": "ios_shortcut"
}
```

### First Test

After saving the Shortcut:

1. Open Safari on iPhone.
2. Open any normal web page.
3. Tap `Share`.
4. Run `Save to TARS Registry`.
5. Enter a short test note.
6. Wait a few seconds.
7. Ask TARS:
   - `Show my reading inbox`

Expected:

- the item should appear in the registry inbox

### Recommended Note Style

Use notes that answer:

- why you saved it
- why it matters
- what bucket it belongs to

Examples:

- `good AI GTM example`
- `watch later for leadership`
- `possible Riipen strategy input`
- `interesting pricing idea`

### Current Limitation

Today this Shortcut is using:

- a public HTTPS endpoint
- plus a strong shared secret header

That is functional now, but it is not the final private-only design yet. The
planned follow-up is a true Tailnet-private front door for the Shortcut.

## How TARS Uses The Registry

TARS should use the registry first for saved-link questions like:

- `What did I save about AI GTM?`
- `Show my reading inbox`
- `What did I just save?`
- `Archive the first one`

The Openclaw workspace wrappers for that path are:

- `./bin/query-registry`
- `./bin/list-registry`
- `./bin/review-registry`

## How To Use It Day To Day

### Save Something

Primary intended flow:

1. share a URL from your phone
2. use the registry shortcut
3. optionally add a short note
4. let the system process it

Good notes look like:

- `good example of AI GTM positioning`
- `watch later for leadership ideas`
- `possible fit for Riipen follow-up thinking`

Short is better than long.

### Ask TARS About What You Saved

Examples:

- `What did I save about AI prospecting?`
- `Show my reading inbox.`
- `What were the takeaways from that YouTube video about MEDDICC?`
- `What did I save recently about Riipen?`
- `Archive the first item.`
- `Mark this one reviewed.`

### Inbox Behavior

The registry uses review states:

- `inbox`
- `reviewed`
- `archived`

The normal flow is:

1. save -> `inbox`
2. inspect or ask TARS about it
3. mark `reviewed` or `archived`

## Recommended Query Style

The best registry queries are short and concrete.

Good:

- `What did I save about pricing strategy?`
- `Show my inbox.`
- `What did I save about AI GTM?`

Less good:

- `Tell me everything I’ve ever thought about all revenue topics`

Keep registry requests closer to:

- topic
- source type
- recent saves
- specific item follow-up

## Relationship To The Second Brain

The registry is part of the second-brain architecture, but it plays a specific
role.

Use it as:

- a saved-content system
- an interest tracker
- a later retrieval surface

Then let TARS synthesize across:

- registry items
- memory
- Krisp meetings
- Obsidian notes

That separation matters because it keeps the registry clean while still making
it useful to the broader system.

## Troubleshooting From A User Perspective

If a saved link does not seem to show up:

1. wait a few seconds and ask again
2. ask TARS for:
   - `Show my reading inbox`
3. try a more concrete query:
   - title words
   - topic words
   - source type

If it still does not appear, this usually means one of:

- the save did not reach the capture endpoint
- processing failed
- the source was difficult to extract cleanly

At that point, use the UAT / operator procedures in
[registry-uat.md](/Users/sgkmeyer/ai-automation-stack/ops/registry-uat.md#L1).

## Summary

Use the registry when you want:

- fast capture of useful links
- stored summaries
- later recall through TARS
- a growing interest and knowledge trail

Use memory when you want:

- durable facts
- cross-source recall
- broader second-brain synthesis
