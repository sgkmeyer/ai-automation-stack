CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS leads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  company TEXT,
  domain TEXT,
  contact_name TEXT,
  email TEXT,
  role TEXT,
  linkedin TEXT,
  source TEXT,
  enrichment_json JSONB,
  score INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS leads_domain_unique
  ON leads (domain);
