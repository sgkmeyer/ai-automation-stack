# Rollback Plan

1. Deactivate the workflow in n8n if it has already been imported.
2. Continue relying on memory-api background processing triggered by REG-01 for normal capture flow.
3. Reprocess failed items manually later once a corrected revision is imported.

Expected restored behavior:
- explicit operator-driven registry reprocess requests stop
- normal background processing from capture remains available
