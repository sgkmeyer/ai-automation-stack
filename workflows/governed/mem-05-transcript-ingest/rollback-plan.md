# Rollback Plan

1. Deactivate the workflow in n8n if it has already been imported.
2. Re-import the previous workflow JSON if a later revision regresses transcript payload handling.
3. Re-run the happy-path fixtures to verify the restored version.

Expected restored behavior:
- transcript ingest returns `200`
- explicit action items are preserved in the response payload
