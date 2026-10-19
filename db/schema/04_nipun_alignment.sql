-- Alignment of each skill to the coded learning outcomes in NIPUN Bharat Annexure I.
-- AI-proposed until a person confirms it. Idempotent: safe on a fresh database and on an existing one.
ALTER TABLE competencies
    ADD COLUMN IF NOT EXISTS nipun_codes          TEXT[],               -- e.g. {'ILM 5.14'}; NULL when the annexure has no counterpart
    ADD COLUMN IF NOT EXISTS nipun_match          TEXT,                 -- exact | finer | related | none
    ADD COLUMN IF NOT EXISTS nipun_confidence     TEXT,                 -- high | medium | low
    ADD COLUMN IF NOT EXISTS nipun_says           TEXT,                 -- our own short paraphrase of the outcome(s)
    ADD COLUMN IF NOT EXISTS nipun_note           TEXT,
    ADD COLUMN IF NOT EXISTS nipun_review_status TEXT NOT NULL DEFAULT 'ai_proposed';
