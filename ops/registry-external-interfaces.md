# Registry External Interfaces

The content registry is a registry-first subsystem. It is not part of the
public `memory/*` webhook surface.

## Live Base URL

Current production ingress uses the existing n8n webhook domain plus a dedicated
shared-secret header:

- Production base URL: `https://n8n.satoic.com/webhook/registry`

This means v1 is currently **secret-protected public ingress**, not a true
Tailnet-only shortcut endpoint yet.

## Planned Private-Only Follow-Up

The remaining infrastructure follow-up is to add a genuine Tailnet-private
front door for the iPhone Shortcut so capture does not rely on the public n8n
domain at all.

Until that is implemented, use the production base URL above with the shared
secret header below.

## Shared Secret Header

All registry webhook routes require the governed n8n credential:

- Header name: `x-registry-webhook-secret`
- Credential template:
  [registry-webhook-header-auth.credential.template.json](/Users/sgkmeyer/ai-automation-stack/workflows/governed/_shared/registry-webhook-header-auth.credential.template.json)

## Routes

### `POST /capture`

Private ingress for iPhone Shortcut and future TARS capture commands.

Request:

```json
{
  "url": "https://example.com/article",
  "note": "Optional short note",
  "capture_channel": "ios_shortcut"
}
```

Optional:

- `tags`: array or comma-separated string

Response:

```json
{
  "ok": true,
  "item_id": "uuid",
  "processing_status": "captured",
  "review_state": "inbox",
  "message": "Saved to TARS Registry"
}
```

### `POST /process`

Private operator/TARS reprocess path.

Request:

```json
{
  "item_id": "uuid",
  "reprocess": true
}
```

### `POST /query`

Private registry-first retrieval path for TARS/Openclaw.

Request shape:

```json
{
  "query": "ai prospecting",
  "review_state": "inbox",
  "topics": ["sales"],
  "user_tags": ["gtm"],
  "limit": 3,
  "page": 1,
  "mode": "answer"
}
```

### `POST /list`

Private inbox/list surface for TARS curation.

Request shape:

```json
{
  "review_state": "inbox",
  "limit": 3,
  "page": 1,
  "sort": "oldest"
}
```

### `POST /review`

Private review-state mutation path.

Request shape:

```json
{
  "item_id": "uuid",
  "action": "archive"
}
```

Supported actions:

- `mark_reviewed`
- `archive`
- `mark_inbox`

## Boundary With Memory

- Registry is the source of truth for saved links and their summaries.
- Registry capture does not auto-write to `memory` in v1.
- TARS should query registry first for saved-content questions.
- Memory remains available later for explicit promotion or broader synthesis.
