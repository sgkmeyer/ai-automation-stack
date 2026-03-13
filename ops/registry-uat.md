# Content Registry UAT

This document gives you a practical UAT script for the live content registry.

It is split into:

- **end-user tests** you can run through the intended product experience
- **operator checks** if you want to verify the backend directly

## Scope

These tests validate:

- capture
- dedupe
- background processing
- query
- inbox listing
- review-state updates
- current source-specific limitations

## Preconditions

Before running UAT, assume:

- the production registry workflows are active
- the current live base is:
  - `https://n8n.satoic.com/webhook/registry`
- the current secret header is available to you
- your iPhone Shortcut is configured, or you can run the operator checks below

## Success Criteria

The registry is working if:

1. you can save a link successfully
2. the item appears in `inbox`
3. TARS can find it by topic or title
4. TARS can summarize it back
5. you can mark it reviewed or archived
6. duplicate saves converge into one canonical item with multiple captures

---

## End-User UAT

### Test 1: Basic Web Capture

Goal:

- prove a normal article/page saves and processes

Steps:

1. Pick a normal article or web page.
2. Save it through the registry shortcut.
3. Add a short note like:
   - `registry test basic web`
4. Wait 5-15 seconds.
5. Ask TARS:
   - `Show my reading inbox`
6. Then ask:
   - `What did I just save?`

Expected:

- the item appears in inbox
- TARS can identify the item
- title, summary, and link are available

### Test 2: Retrieval By Topic

Goal:

- confirm TARS can query the registry by meaning, not just exact URL

Steps:

1. Save a link clearly about a known topic.
2. Wait for processing.
3. Ask:
   - `What did I save about <topic>?`

Expected:

- the correct item appears
- the summary is grounded in the saved source

### Test 3: Optional Note Influence

Goal:

- confirm your save-time note is preserved and useful later

Steps:

1. Save a link with a distinctive note such as:
   - `possible Riipen strategy reference`
2. Wait for processing.
3. Ask:
   - `What did I save related to Riipen strategy?`

Expected:

- the item should be easier to retrieve because of the note context

### Test 4: Duplicate Save / Canonicalization

Goal:

- confirm one canonical item plus multiple captures

Steps:

1. Save a URL once.
2. Save the same URL again.
3. If possible, save a slightly different version:
   - with tracking params
   - shortened form
   - canonical form
4. Ask TARS:
   - `Show my reading inbox`
5. If needed, run the operator check below to inspect capture history.

Expected:

- one registry item
- multiple captures attached to it
- not multiple near-identical registry items

### Test 5: Review-State Flow

Goal:

- confirm inbox curation works

Steps:

1. Ask:
   - `Show my reading inbox`
2. Then ask:
   - `Mark the first one reviewed`
3. Then ask:
   - `Show my reading inbox`

Expected:

- the reviewed item should no longer behave like an unread inbox item

Optional:

- `Archive the first one`

### Test 6: YouTube Save

Goal:

- validate YouTube handling

Steps:

1. Save a YouTube link through the registry shortcut.
2. Wait for processing.
3. Ask:
   - `What did I save from YouTube about <topic>?`

Expected:

- the item is stored
- summary exists
- if transcript/captions were available, the summary should be richer than a pure metadata fallback

### Test 7: X Save

Goal:

- validate metadata-first fallback

Steps:

1. Save an X post.
2. Wait for processing.
3. Ask:
   - `What did I save from X today?`

Expected:

- the item is present
- summary may be lighter and more metadata-driven than a normal article

### Test 8: TikTok Save

Goal:

- validate metadata-first fallback

Steps:

1. Save a TikTok link.
2. Wait for processing.
3. Ask:
   - `What did I save from TikTok?`

Expected:

- the item is present
- summary may be limited compared with normal web content

---

## TARS Prompt Set

Use these exact prompts during UAT:

```text
Show my reading inbox.
```

```text
What did I just save?
```

```text
What did I save about AI GTM?
```

```text
What did I save from YouTube recently?
```

```text
What did I save from X today?
```

```text
Mark the first one reviewed.
```

```text
Archive the first one.
```

---

## Operator Checks

Use these when you want to validate the backend directly rather than relying
only on TARS behavior.

### 1. Capture Directly

Replace `REPLACE_WITH_SECRET` with the current registry secret.

```bash
curl -ksS https://n8n.satoic.com/webhook/registry/capture \
  -H 'x-registry-webhook-secret: REPLACE_WITH_SECRET' \
  -H 'Content-Type: application/json' \
  -d '{
    "url": "https://example.com/?utm_source=test",
    "note": "registry operator test",
    "capture_channel": "manual_test"
  }'
```

Expected:

- `200`
- JSON with:
  - `ok`
  - `item_id`
  - `processing_status`
  - `review_state`

### 2. Query Directly

```bash
curl -ksS https://n8n.satoic.com/webhook/registry/query \
  -H 'x-registry-webhook-secret: REPLACE_WITH_SECRET' \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "example domain",
    "limit": 5,
    "page": 1,
    "mode": "answer"
  }'
```

Expected:

- `200`
- item appears once processed

### 3. List Inbox Directly

```bash
curl -ksS https://n8n.satoic.com/webhook/registry/list \
  -H 'x-registry-webhook-secret: REPLACE_WITH_SECRET' \
  -H 'Content-Type: application/json' \
  -d '{
    "review_state": "inbox",
    "limit": 5,
    "page": 1,
    "sort": "oldest"
  }'
```

Expected:

- `200`
- structured `items` array

### 4. Review Directly

```bash
curl -ksS https://n8n.satoic.com/webhook/registry/review \
  -H 'x-registry-webhook-secret: REPLACE_WITH_SECRET' \
  -H 'Content-Type: application/json' \
  -d '{
    "item_id": "REPLACE_WITH_ITEM_ID",
    "action": "mark_reviewed"
  }'
```

Expected:

- `200`
- `review_state` changes

### 5. Processing Verification In Postgres

```bash
ssh satoic-production \
  "cd /home/ubuntu/ai-automation-stack/automation && \
   docker compose --env-file .env -f docker-compose.yml exec -T db \
   psql -U n8n_admin -d n8n_database -c \"
     SELECT id, canonical_url, processing_status, review_state, title, processed_at
     FROM registry.items
     ORDER BY last_captured_at DESC
     LIMIT 10;
   \""
```

Expected:

- newly captured items should reach `processing_status = ready`

### 6. Capture History Verification

```bash
ssh satoic-production \
  "cd /home/ubuntu/ai-automation-stack/automation && \
   docker compose --env-file .env -f docker-compose.yml exec -T db \
   psql -U n8n_admin -d n8n_database -c \"
     SELECT item_id, submitted_url, captured_at, user_note
     FROM registry.captures
     ORDER BY captured_at DESC
     LIMIT 20;
   \""
```

Expected:

- repeated saves appear as multiple captures
- they should attach to the same canonical item when appropriate

---

## Failure Cases To Watch For

### Capture succeeds but item never shows up

Likely causes:

- processing failed
- extraction was weak
- wrong query phrasing

Check:

- `registry.items.processing_status`
- `registry.jobs.error_message`

### Duplicate items appear

Likely causes:

- shortened URL was not resolved cleanly
- canonicalization needs adjustment for that source pattern

Check:

- `original_url`
- `canonical_url`
- capture history rows

### X / TikTok summaries are weak

This is expected in v1.

Those sources are intentionally metadata-first for now.

### Registry item does not appear in TARS but exists in Postgres

Likely causes:

- TARS prompt was too broad
- item is stored but not the top-ranked match
- the item is reviewed/archived and not in the inbox query path

Test with:

- exact title words
- source type
- recent save framing

---

## UAT Sign-Off Checklist

Mark these complete when done:

- [ ] Basic web capture works
- [ ] TARS can retrieve by topic
- [ ] Save-time note influences retrieval
- [ ] Duplicate saves converge into one canonical item
- [ ] Inbox listing works
- [ ] Review / archive flow works
- [ ] YouTube save works
- [ ] X save works at metadata level
- [ ] TikTok save works at metadata level
- [ ] Operator query/list/review checks return expected JSON
- [ ] At least one processed item reaches `ready`

When all of those pass, the service is good enough for normal day-to-day use.
