# Rollback Plan

1. Deactivate the workflow in n8n if it has already been imported.
2. Fall back to direct operator inspection of registry rows until a corrected query workflow is imported.
3. Keep the underlying registry schema and memory-api query route in place.

Expected restored behavior:
- registry-first TARS querying stops at the n8n edge
- saved-content answers can still be recovered manually from Postgres or memory-api
