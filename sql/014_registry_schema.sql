CREATE SCHEMA IF NOT EXISTS registry;

SET search_path TO registry, public;

CREATE TABLE IF NOT EXISTS items (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    original_url        TEXT NOT NULL,
    canonical_url       TEXT NOT NULL UNIQUE,
    canonical_host      TEXT NOT NULL,
    source_kind         TEXT NOT NULL CHECK (source_kind IN ('web', 'youtube', 'x', 'tiktok', 'unknown')),
    capture_channel     TEXT NOT NULL DEFAULT 'ios_shortcut',
    processing_status   TEXT NOT NULL DEFAULT 'captured' CHECK (processing_status IN ('captured', 'processing', 'ready', 'failed')),
    review_state        TEXT NOT NULL DEFAULT 'inbox' CHECK (review_state IN ('inbox', 'reviewed', 'archived')),
    title               TEXT,
    summary             TEXT,
    why_it_matters      TEXT,
    key_takeaways       TEXT[] NOT NULL DEFAULT '{}',
    topics              TEXT[] NOT NULL DEFAULT '{}',
    metadata            JSONB NOT NULL DEFAULT '{}'::jsonb,
    raw_archive_path    TEXT,
    last_error          TEXT,
    first_captured_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_captured_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    tsv                 TSVECTOR
);

CREATE INDEX IF NOT EXISTS registry_items_status_idx
    ON items (processing_status, review_state, source_kind, last_captured_at DESC);

CREATE INDEX IF NOT EXISTS registry_items_topics_idx
    ON items USING GIN (topics);

CREATE INDEX IF NOT EXISTS registry_items_tsv_idx
    ON items USING GIN (tsv);

CREATE OR REPLACE FUNCTION registry.items_tsv_trigger() RETURNS trigger AS $$
BEGIN
    NEW.tsv := to_tsvector(
        'english',
        trim(
            COALESCE(NEW.title, '') || ' ' ||
            COALESCE(NEW.summary, '') || ' ' ||
            COALESCE(NEW.why_it_matters, '') || ' ' ||
            COALESCE(array_to_string(NEW.key_takeaways, ' '), '') || ' ' ||
            COALESCE(NEW.metadata->>'note_search', '') || ' ' ||
            COALESCE(array_to_string(ARRAY(SELECT jsonb_array_elements_text(COALESCE(NEW.metadata->'user_tags', '[]'::jsonb))), ' '), '')
        )
    );
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS registry_items_tsv_update ON items;
CREATE TRIGGER registry_items_tsv_update
    BEFORE INSERT OR UPDATE ON items
    FOR EACH ROW EXECUTE FUNCTION registry.items_tsv_trigger();

CREATE TABLE IF NOT EXISTS captures (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id             UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    submitted_url       TEXT NOT NULL,
    capture_channel     TEXT NOT NULL DEFAULT 'ios_shortcut',
    user_note           TEXT,
    user_tags           TEXT[] NOT NULL DEFAULT '{}',
    captured_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata            JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS registry_captures_item_idx
    ON captures (item_id, captured_at DESC);

CREATE INDEX IF NOT EXISTS registry_captures_tags_idx
    ON captures USING GIN (user_tags);

CREATE TABLE IF NOT EXISTS jobs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id             UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    job_type            TEXT NOT NULL CHECK (job_type IN ('capture', 'process', 'reprocess')),
    status              TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    attempt_count       INTEGER NOT NULL DEFAULT 0,
    error_message       TEXT,
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS registry_jobs_item_idx
    ON jobs (item_id, created_at DESC);
