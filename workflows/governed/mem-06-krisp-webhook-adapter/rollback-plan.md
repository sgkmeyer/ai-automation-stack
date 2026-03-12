# Rollback Plan

1. Deactivate the workflow in n8n if it has already been imported.
2. Remove Krisp's webhook configuration or replace it with the manual fallback process.
3. Re-import the previous workflow JSON if a later revision regresses Krisp payload handling.
4. Continue using `scripts/memory-webhook.sh transcript ...` for any missed or backfill transcripts.

Expected restored behavior:
- Krisp webhook traffic no longer reaches the automation stack
- manual transcript ingest remains available
- replaying fixtures against the restored workflow returns the previous expected responses
