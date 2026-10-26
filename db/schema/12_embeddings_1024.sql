-- 12: the embeddings are vector(1024): BAAI/bge-m3 (open weights, MIT), computed OFFLINE by scripts/embed_content.py and loaded by scripts/load_embeddings.py.
-- IDEMPOTENT, and SAFE WITHOUT pgvector: where the extension is missing it only says so and changes nothing (semantic retrieval then stays off).
-- The embedding columns were never populated, so changing their size loses nothing. Any ivfflat index is dropped: at 9 to 101 rows an exact scan is instant and exactly right.
-- Adds the column to `competencies` (the skill's own stored vector is the QUERY: the running app calls no embedding service).
CREATE TABLE IF NOT EXISTS embedding_meta (
    id           INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    model        TEXT,
    revision     TEXT,
    dims         INTEGER,
    file_sha256  TEXT,
    loaded_at    TIMESTAMPTZ,
    counts       JSONB
);

DO $$
DECLARE
    t   TEXT;
    cur TEXT;
    ix  RECORD;
BEGIN
    IF to_regtype('vector') IS NULL THEN
        BEGIN
            CREATE EXTENSION IF NOT EXISTS vector;
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'pgvector could not be enabled (%): the embedding columns stay as they are and semantic retrieval stays off', SQLERRM;
        END;
    END IF;
    IF to_regtype('vector') IS NULL THEN
        RETURN;
    END IF;
    FOREACH t IN ARRAY ARRAY['anchor_activities', 'reading_passages', 'intervention_templates', 'tlm_references', 'competencies'] LOOP
        SELECT format_type(a.atttypid, a.atttypmod) INTO cur
          FROM pg_attribute a WHERE a.attrelid = t::regclass AND a.attname = 'embedding' AND NOT a.attisdropped;
        IF cur = 'vector(1024)' THEN
            CONTINUE;
        END IF;
        FOR ix IN SELECT indexname FROM pg_indexes WHERE tablename = t AND indexdef ILIKE '%ivfflat%' LOOP
            EXECUTE format('DROP INDEX IF EXISTS %I', ix.indexname);
        END LOOP;
        IF cur IS NULL THEN
            EXECUTE format('ALTER TABLE %I ADD COLUMN embedding vector(1024)', t);
        ELSE
            EXECUTE format('ALTER TABLE %I ALTER COLUMN embedding TYPE vector(1024) USING NULL', t);
        END IF;
    END LOOP;
END $$;
