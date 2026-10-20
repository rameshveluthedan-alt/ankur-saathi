-- Children's names: TEACHER-ONLY. Used to show names on the teacher's own screens and in her own class report.
-- They live in their own table so that no query on `children` can pick them up by accident, and nothing that builds a
-- request to the AI may read this table (docs/PRIVACY.md; backend/tests/test_names_static_guard.py enforces it).
-- Idempotent.
CREATE TABLE IF NOT EXISTS child_names (
    child_id    UUID PRIMARY KEY REFERENCES children(id) ON DELETE CASCADE,
    name        TEXT NOT NULL CHECK (char_length(name) BETWEEN 1 AND 80),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
