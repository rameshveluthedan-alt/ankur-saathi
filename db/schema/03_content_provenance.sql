-- Where each piece of content came from, under which licence, and whether a person has reviewed it.
-- Idempotent: run it once on an existing database, and setup.sh runs it for new ones.

ALTER TABLE reading_passages
    ADD COLUMN IF NOT EXISTS source_url      TEXT,
    ADD COLUMN IF NOT EXISTS license         TEXT,
    ADD COLUMN IF NOT EXISTS attribution     TEXT,      -- the credit line printed under the passage (required by CC BY)
    ADD COLUMN IF NOT EXISTS author          TEXT,
    ADD COLUMN IF NOT EXISTS original_level  SMALLINT,  -- the source's own reading level (StoryWeaver: 1-4)
    ADD COLUMN IF NOT EXISTS review_status   TEXT NOT NULL DEFAULT 'ai_drafted';

ALTER TABLE anchor_activities
    ADD COLUMN IF NOT EXISTS source_url      TEXT,
    ADD COLUMN IF NOT EXISTS license         TEXT,
    ADD COLUMN IF NOT EXISTS attribution     TEXT,
    ADD COLUMN IF NOT EXISTS review_status   TEXT NOT NULL DEFAULT 'ai_drafted';

ALTER TABLE intervention_templates
    ADD COLUMN IF NOT EXISTS source_url      TEXT,
    ADD COLUMN IF NOT EXISTS license         TEXT,
    ADD COLUMN IF NOT EXISTS attribution     TEXT,
    ADD COLUMN IF NOT EXISTS review_status   TEXT NOT NULL DEFAULT 'ai_drafted';

ALTER TABLE tlm_references
    ADD COLUMN IF NOT EXISTS source_url      TEXT,
    ADD COLUMN IF NOT EXISTS license         TEXT,
    ADD COLUMN IF NOT EXISTS attribution     TEXT,
    ADD COLUMN IF NOT EXISTS review_status   TEXT NOT NULL DEFAULT 'ai_drafted';

-- Rows inserted later (the seeds on a fresh database) are team-written unless an importer says otherwise.
-- Outside content (scripts/import_passages.py) always sets its licence explicitly.
ALTER TABLE reading_passages       ALTER COLUMN license SET DEFAULT 'team-written';
ALTER TABLE anchor_activities      ALTER COLUMN license SET DEFAULT 'team-written';
ALTER TABLE intervention_templates ALTER COLUMN license SET DEFAULT 'team-written';

-- Rows that already exist (an existing database): ours, no credit line needed
UPDATE reading_passages        SET license = 'team-written' WHERE source = 'original' AND license IS NULL;
UPDATE anchor_activities       SET license = 'team-written' WHERE source = 'original' AND license IS NULL;
UPDATE intervention_templates  SET license = 'team-written' WHERE source = 'original' AND license IS NULL;
