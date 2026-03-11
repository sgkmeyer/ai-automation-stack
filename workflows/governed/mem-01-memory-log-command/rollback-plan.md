# Rollback Plan

If a dev or production instance of `MEM-01 - Memory Log Command` is created and must be reverted:

1. Deactivate the workflow in n8n.
2. Restore the previous workflow version if one exists.
3. Re-run the `/log` smoke fixture to verify the restored version.

Expected verification:
- webhook no longer routes to the faulty version
- happy-path `/log` request succeeds
- invalid requests still fail cleanly
