# Rollback Plan

1. Deactivate the current `MEM-02 - Memory Recall Command` workflow.
2. Restore the prior version or remove the draft workflow if no prior version exists.
3. Re-run the recall fixture in dev.

Expected verification:
- recall webhook responds
- citation payload shape is preserved
- invalid `entry_type` still returns a validation error
