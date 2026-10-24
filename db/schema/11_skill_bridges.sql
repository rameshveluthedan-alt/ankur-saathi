-- Curated skill bridges: for a skill (the day's ANCHOR), the skill the Beginners work on (its predecessor) and the skill the Proficients work on (its successor), as decided by a reviewer.
-- The app consults this table FIRST and falls back to the graph rule (group_skills.derived_beginner_id / derived_proficient_id) where a skill has no approved row, or a side is empty.
-- Loaded from db/seeds/content/07_skill_bridges.csv by scripts/load_bridges.py (which also creates this table when it is missing). Only APPROVED rows are ever stored.
CREATE TABLE IF NOT EXISTS skill_bridges (
    skill_id        TEXT PRIMARY KEY REFERENCES competencies(id) ON DELETE CASCADE,
    predecessor_id  TEXT REFERENCES competencies(id) ON DELETE SET NULL,
    successor_id    TEXT REFERENCES competencies(id) ON DELETE SET NULL,
    note            TEXT,
    approved        BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
