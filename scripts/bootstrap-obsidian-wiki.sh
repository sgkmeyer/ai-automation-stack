#!/usr/bin/env bash

set -euo pipefail

LOCAL_VAULT="${OBSIDIAN_LOCAL_VAULT:-/Users/sgkmeyer/vaults/second-brain}"
WIKI_ROOT="${LOCAL_VAULT}/wiki"

[[ -d "${LOCAL_VAULT}" ]] || {
  printf 'error: local vault not found: %s\n' "${LOCAL_VAULT}" >&2
  exit 1
}

mkdir -p \
  "${WIKI_ROOT}/people" \
  "${WIKI_ROOT}/companies" \
  "${WIKI_ROOT}/projects" \
  "${WIKI_ROOT}/topics" \
  "${WIKI_ROOT}/syntheses" \
  "${WIKI_ROOT}/sources"

if [[ ! -f "${WIKI_ROOT}/index.md" ]]; then
  cat > "${WIKI_ROOT}/index.md" <<'EOF'
# Wiki Index

Use this as the top-level navigation page for synthesized knowledge.

- [[people]]
- [[companies]]
- [[projects]]
- [[topics]]
- [[syntheses]]
- [[sources]]
EOF
fi

if [[ ! -f "${WIKI_ROOT}/log.md" ]]; then
  cat > "${WIKI_ROOT}/log.md" <<'EOF'
# Wiki Log

Append notable wiki maintenance events here when promoting important knowledge.
EOF
fi

if [[ ! -f "${WIKI_ROOT}/schema.md" ]]; then
  cat > "${WIKI_ROOT}/schema.md" <<'EOF'
# Wiki Schema

Required frontmatter:

- `title`
- `type`
- `status`
- `tags`
- `source_refs`
- `updated_at`
- `confidence`

Page types:

- `people`
- `companies`
- `projects`
- `topics`
- `syntheses`
- `sources`
EOF
fi

printf 'Wiki scaffold ready at %s\n' "${WIKI_ROOT}"
