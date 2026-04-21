#!/usr/bin/env bash
# verify-krisp-ingest.sh — read-only production checks for Krisp ingest wiring.

set -euo pipefail

VM_HOST="${VM_HOST:-satoic-production}"
DB_USER="${KRISP_VERIFY_DB_USER:-n8n_admin}"
DB_NAME="${KRISP_VERIFY_DB_NAME:-n8n_database}"
LOOKBACK_HOURS="${KRISP_VERIFY_LOOKBACK_HOURS:-72}"

say() { printf "%s\n" "$*"; }

run_ssh() {
  # SC2029: the command string is intentionally assembled client-side and sent to the VM.
  # shellcheck disable=SC2029
  ssh "${VM_HOST}" "$1"
}

say "Krisp ingest verification"
say "Host: ${VM_HOST}"

workflow_sql="select name, active from workflow_entity where name in ('MEM-05 - Transcript Ingest','MEM-06 - Krisp Webhook Adapter') order by name;"
workflow_rows="$(run_ssh "docker exec automation-db-1 psql -U ${DB_USER} -d ${DB_NAME} -Atc $(printf '%q' "${workflow_sql}")")"

WORKFLOW_ROWS="${workflow_rows}" python3 - <<'PY'
import os

rows = [line.split("|", 1) for line in os.environ["WORKFLOW_ROWS"].splitlines() if line.strip()]
required = {
    "MEM-05 - Transcript Ingest": "t",
    "MEM-06 - Krisp Webhook Adapter": "t",
}
found = {name: active for name, active in rows}
missing = [name for name, active in required.items() if found.get(name) != active]
if missing:
    raise SystemExit(f"workflow verification failed: {missing!r}; found={found!r}")
PY
say "OK   Krisp workflows active"

recent_jobs_sql="select to_char(started_at at time zone 'UTC', 'YYYY-MM-DD HH24:MI:SS'), status, source_ref from memory.ingestion_jobs where source_ref like 'krisp:%' and started_at >= now() - interval '${LOOKBACK_HOURS} hours' order by started_at desc limit 10;"
recent_jobs="$(run_ssh "docker exec automation-db-1 psql -U ${DB_USER} -d ${DB_NAME} -Atc $(printf '%q' "${recent_jobs_sql}")")"

RECENT_JOBS="${recent_jobs}" python3 - <<'PY'
import os

rows = [line for line in os.environ["RECENT_JOBS"].splitlines() if line.strip()]
if not rows:
    raise SystemExit("no recent krisp ingestion jobs found")
PY
say "OK   Recent krisp ingestion jobs found"
printf '%s\n' "${recent_jobs}"

audit_tail="$(run_ssh "docker exec automation-n8n-webhook-1 sh -lc 'test -f /home/node/.n8n/krisp-ingest.ndjson && tail -n 10 /home/node/.n8n/krisp-ingest.ndjson'")"

AUDIT_TAIL="${audit_tail}" python3 - <<'PY'
import json
import os

rows = [line for line in os.environ["AUDIT_TAIL"].splitlines() if line.strip()]
if not rows:
    raise SystemExit("krisp audit log is empty")
for line in rows:
    payload = json.loads(line)
    if not {"received_at", "source_ref", "decision"} <= payload.keys():
        raise SystemExit(f"unexpected audit payload: {payload!r}")
PY
say "OK   Krisp audit log present inside n8n volume"
printf '%s\n' "${audit_tail}"

say "Krisp ingest verification passed."
