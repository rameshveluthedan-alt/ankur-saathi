-- Class register: children enrolled in bulk, in multi-grade classes where roll numbers repeat across grades.
-- children.roll_number stays the CLASS number (unique within a teacher's class, so everything that looks a child up
-- by number keeps working). school_roll keeps the roll the school knows, so "305" can be shown as Grade 3, roll 5.
-- Idempotent.
ALTER TABLE children ADD COLUMN IF NOT EXISTS school_roll SMALLINT;

CREATE TABLE IF NOT EXISTS register_uploads (
    id            BIGSERIAL PRIMARY KEY,
    teacher_id    UUID NOT NULL REFERENCES teachers(id) ON DELETE CASCADE,
    filename      TEXT,
    rows_total    INTEGER NOT NULL,
    rows_added    INTEGER NOT NULL,
    rows_skipped  INTEGER NOT NULL,
    numbering     TEXT,                      -- plain | composite
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
