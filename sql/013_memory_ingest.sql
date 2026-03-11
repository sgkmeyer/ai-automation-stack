SET search_path TO memory, public;

-- Week 2 ingestion support: file-backed sync needs an update timestamp and
-- a cheap lookup on source/source_ref for idempotent re-ingest.
ALTER TABLE entries
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE INDEX IF NOT EXISTS entries_source_ref_idx
    ON entries (source, source_ref)
    WHERE source_ref IS NOT NULL;

CREATE OR REPLACE FUNCTION memory.entries_tsv_trigger() RETURNS trigger AS $$
BEGIN
    NEW.tsv := to_tsvector('english', COALESCE(NEW.body, '') || ' ' || COALESCE(NEW.entry_type, ''));
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
