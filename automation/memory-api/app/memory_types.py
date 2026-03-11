"""Shared memory-domain constants and normalization helpers."""

ENTRY_TYPES = {
    "meeting",
    "decision",
    "commitment",
    "reflection",
    "observation",
    "research",
    "conversation",
    "journal",
    "transcript_summary",
    "action_item",
    "insight",
}

ENTITY_TYPES = {"person", "company", "project", "topic"}
ENTITY_ROLES = {"mentioned", "subject", "participant", "owner"}
SOURCES = {"tars", "obsidian", "transcript", "n8n", "manual", "system"}


def normalize_extraction(raw: object) -> dict:
    """Sanitize LLM extraction output to match schema constraints."""
    if not isinstance(raw, dict):
        return {"entry_type": "observation", "entities": []}

    entry_type = raw.get("entry_type")
    if entry_type not in ENTRY_TYPES:
        entry_type = "observation"

    entities = []
    for candidate in raw.get("entities", []):
        if not isinstance(candidate, dict):
            continue

        name = str(candidate.get("name", "")).strip()
        entity_type = candidate.get("type", "topic")
        role = candidate.get("role", "mentioned")

        if not name:
            continue
        if entity_type not in ENTITY_TYPES:
            entity_type = "topic"
        if role not in ENTITY_ROLES:
            role = "mentioned"

        entities.append({"name": name, "type": entity_type, "role": role})

    return {"entry_type": entry_type, "entities": entities}
