CREATE SCHEMA IF NOT EXISTS ops;

SET search_path TO ops, public;

CREATE TABLE IF NOT EXISTS mutation_journal (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    occurred_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor_type              TEXT NOT NULL,
    actor_id                TEXT,
    subsystem               TEXT NOT NULL,
    mutation_type           TEXT NOT NULL,
    target_id               UUID NOT NULL,
    reason                  TEXT,
    before_state            JSONB NOT NULL DEFAULT '{}'::jsonb,
    after_state             JSONB NOT NULL DEFAULT '{}'::jsonb,
    rollback_mode           TEXT NOT NULL CHECK (rollback_mode IN ('inverse_mutation', 'compensating_mutation', 'operator_restore', 'source_replay')),
    rollback_status         TEXT NOT NULL DEFAULT 'available' CHECK (rollback_status IN ('available', 'rolled_back', 'not_available')),
    rolled_back_by_mutation_id UUID REFERENCES mutation_journal(id),
    metadata                JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS mutation_journal_target_idx
    ON mutation_journal (subsystem, target_id, occurred_at DESC);

CREATE INDEX IF NOT EXISTS mutation_journal_rollback_idx
    ON mutation_journal (rollback_status, occurred_at DESC);

