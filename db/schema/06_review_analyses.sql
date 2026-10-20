-- The result of every photo analysis, so a teacher who presses Back (or reloads, or switches phone) can open it again.
-- Roll numbers and scores only: no names, and no photos are stored. Idempotent.
CREATE TABLE IF NOT EXISTS review_analyses (
    id               BIGSERIAL PRIMARY KEY,
    teacher_id       UUID NOT NULL REFERENCES teachers(id) ON DELETE CASCADE,
    session_date     DATE NOT NULL,
    domain_id        TEXT NOT NULL,
    worksheet_level  TEXT NOT NULL,
    competency_id    TEXT,
    result           JSONB NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_review_analyses_lookup
    ON review_analyses (teacher_id, session_date, domain_id, worksheet_level, created_at DESC);
