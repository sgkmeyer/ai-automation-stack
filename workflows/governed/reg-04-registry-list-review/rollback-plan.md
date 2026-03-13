# Rollback Plan

1. Deactivate the workflow in n8n if it has already been imported.
2. Fall back to operator-driven SQL or direct memory-api calls for list/review actions until a corrected revision is imported.
3. Keep registry capture and processing active if those workflows remain healthy.

Expected restored behavior:
- TARS loses the curated inbox/list/review surface
- registry items already stored remain intact
- capture and processing can continue independently
