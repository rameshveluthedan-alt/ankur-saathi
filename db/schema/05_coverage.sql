-- How much of the knowledge base stands behind each skill, shown to the user as a label on the Plan screen.
-- Filled by scripts/build_coverage.py (seed 06_coverage.sql). Idempotent.
CREATE TABLE IF NOT EXISTS competency_coverage (
    competency_id   TEXT PRIMARY KEY REFERENCES competencies(id),
    tier            TEXT NOT NULL DEFAULT 'untested'
                    CHECK (tier IN ('tested', 'ai_written', 'experimental', 'untested')),
    anchor_match    TEXT,          -- exact | related | topic_area | loose | none
    passage_match   TEXT,          -- competency | grade | none | n/a (numeracy)
    nipun_match     TEXT,          -- exact | finer | related | none
    batch_status    TEXT,          -- ok | error | not_run
    batch_warnings  INTEGER,       -- checks still failing after the automatic repairs
    note            TEXT,          -- one plain sentence for the teacher or juror
    tested_at       TIMESTAMPTZ
);
