# Rollback Plan

1. Deactivate the workflow in n8n if it has already been imported.
2. Re-import the previous workflow JSON if a later revision regresses payload handling.
3. Re-run the happy-path and idempotent fixtures to verify the restored version.

Expected restored behavior:
- note ingest returns `200`
- repeated ingest of the same checksum does not duplicate data unexpectedly
