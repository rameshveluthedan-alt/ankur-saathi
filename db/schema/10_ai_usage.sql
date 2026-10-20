-- A meter for every call to the AI, so spending can be capped and reported. Idempotent.
-- Tokens are the ground truth. Money is computed from them with the CURRENT prices in the settings (AI_PRICE_*), so correcting a
-- price corrects every estimate, past and future. est_cost_usd is a convenience copy for reading the table by eye.
CREATE TABLE IF NOT EXISTS ai_usage (
    id            BIGSERIAL PRIMARY KEY,
    teacher_id    UUID REFERENCES teachers(id) ON DELETE SET NULL,
    school_id     UUID,
    kind          TEXT NOT NULL,                 -- plan | plan_repair | vision
    model         TEXT,
    input_tokens  INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    est_cost_usd  NUMERIC(10, 4),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_ai_usage_created ON ai_usage (created_at);
CREATE INDEX IF NOT EXISTS idx_ai_usage_teacher ON ai_usage (teacher_id, created_at);
CREATE INDEX IF NOT EXISTS idx_ai_usage_school ON ai_usage (school_id, created_at);
