-- Memory Layer Schema -- Week 1
-- Design: structured personal memory with entity linking
-- No embeddings/vectors yet -- retrieval is relational + full-text

SET search_path TO memory, public;

---------------------------------------------
-- ENTITIES
-- People, companies, projects, topics
---------------------------------------------
CREATE TABLE IF NOT EXISTS entities (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type     TEXT NOT NULL CHECK (entity_type IN ('person', 'company', 'project', 'topic')),
    name            TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    aliases         TEXT[] DEFAULT '{}',
    notes           TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS entities_type_name_unique
    ON entities (entity_type, normalized_name);

CREATE OR REPLACE FUNCTION memory.entities_normalize_trigger() RETURNS trigger AS $$
BEGIN
    NEW.normalized_name := LOWER(NEW.name);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS entities_normalize ON entities;
CREATE TRIGGER entities_normalize
    BEFORE INSERT OR UPDATE ON entities
    FOR EACH ROW EXECUTE FUNCTION memory.entities_normalize_trigger();

---------------------------------------------
-- ENTRIES
-- The universal event log
---------------------------------------------
CREATE TABLE IF NOT EXISTS entries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entry_type      TEXT NOT NULL CHECK (entry_type IN (
                        'meeting', 'decision', 'commitment', 'reflection',
                        'observation', 'research', 'conversation', 'journal',
                        'transcript_summary', 'action_item', 'insight'
                    )),
    body            TEXT NOT NULL,
    structured      JSONB DEFAULT '{}',
    source          TEXT NOT NULL CHECK (source IN (
                        'tars', 'obsidian', 'transcript', 'n8n', 'manual', 'system'
                    )),
    source_ref      TEXT,
    occurred_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tsv             TSVECTOR
);

CREATE INDEX IF NOT EXISTS entries_tsv_idx ON entries USING GIN (tsv);
CREATE INDEX IF NOT EXISTS entries_occurred_at_idx ON entries (occurred_at DESC);
CREATE INDEX IF NOT EXISTS entries_type_idx ON entries (entry_type);

CREATE OR REPLACE FUNCTION memory.entries_tsv_trigger() RETURNS trigger AS $$
BEGIN
    NEW.tsv := to_tsvector('english', COALESCE(NEW.body, '') || ' ' || COALESCE(NEW.entry_type, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS entries_tsv_update ON entries;
CREATE TRIGGER entries_tsv_update
    BEFORE INSERT OR UPDATE ON entries
    FOR EACH ROW EXECUTE FUNCTION memory.entries_tsv_trigger();

---------------------------------------------
-- ENTRY_ENTITIES
---------------------------------------------
CREATE TABLE IF NOT EXISTS entry_entities (
    entry_id        UUID NOT NULL REFERENCES entries(id) ON DELETE CASCADE,
    entity_id       UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    role            TEXT DEFAULT 'mentioned',
    PRIMARY KEY (entry_id, entity_id)
);

CREATE INDEX IF NOT EXISTS entry_entities_entity_idx ON entry_entities (entity_id);
CREATE INDEX IF NOT EXISTS entry_entities_entry_idx ON entry_entities (entry_id);

---------------------------------------------
-- CONTEXT_REGISTER
-- Living key-value state
---------------------------------------------
CREATE TABLE IF NOT EXISTS context_register (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain          TEXT NOT NULL,
    key             TEXT NOT NULL,
    normalized_key  TEXT NOT NULL,
    value           TEXT NOT NULL,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS context_register_domain_key_unique
    ON context_register (domain, normalized_key);

CREATE OR REPLACE FUNCTION memory.context_normalize_trigger() RETURNS trigger AS $$
BEGIN
    NEW.normalized_key := LOWER(NEW.key);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS context_normalize ON context_register;
CREATE TRIGGER context_normalize
    BEFORE INSERT OR UPDATE ON context_register
    FOR EACH ROW EXECUTE FUNCTION memory.context_normalize_trigger();

---------------------------------------------
-- INGESTION_JOBS
-- Provenance tracking
---------------------------------------------
CREATE TABLE IF NOT EXISTS ingestion_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type     TEXT NOT NULL,
    source_ref      TEXT,
    status          TEXT NOT NULL DEFAULT 'pending' CHECK (status IN (
                        'pending', 'processing', 'completed', 'failed'
                    )),
    entries_created INTEGER DEFAULT 0,
    entities_linked INTEGER DEFAULT 0,
    error_message   TEXT,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);
