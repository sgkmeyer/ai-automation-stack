# Rollback Plan

1. Deactivate `MEM-03 - Memory Context Command`.
2. Restore the last working version or remove the draft workflow.
3. Re-run the set/get/delete fixtures in dev.

Expected verification:
- get returns context
- set updates context
- repeated delete returns 404
