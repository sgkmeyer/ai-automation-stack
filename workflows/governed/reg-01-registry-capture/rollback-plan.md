# Rollback Plan

1. Deactivate the workflow in n8n if it has already been imported.
2. Restore or reactivate the previous private capture path only if an operator explicitly wants the ad hoc prototype back.
3. Keep the registry schema and memory-api routes in place; rollback only the n8n ingress if the failure is isolated there.

Expected restored behavior:
- iPhone Shortcut capture into the governed registry stops
- no new registry items are created via n8n
- the prototype workflow can remain disabled unless intentionally revived
