-- The school's confirmation that the children's parents or guardians have been told, and have given their permission (docs/PRIVACY.md, "Consent").
-- One row each time a school confirms: the exact wording it agreed to and the version of that wording are kept with it, so what a school agreed to can always be shown.
-- Created on first use by app/services/auth_service.py (ensure_consent_table), the same way scripts/load_bridges.py creates skill_bridges: no manual database step, and
-- no ALTER of an existing table. The latest row for a school is the one that counts.
CREATE TABLE IF NOT EXISTS school_consents (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id    UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    attested_by  UUID REFERENCES teachers(id) ON DELETE SET NULL,
    version      TEXT NOT NULL,
    statement    TEXT NOT NULL,
    attested_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_school_consents_school ON school_consents (school_id, attested_at DESC);
