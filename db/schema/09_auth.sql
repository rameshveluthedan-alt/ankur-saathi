-- PIN login, school admins and an audit trail of sign-in events. Idempotent.
--   role            teacher | school_admin  (the first teacher to register a school becomes its admin)
--   pin_hash        PBKDF2 of the PIN, never the PIN. NULL = no PIN yet: the account cannot log in until one is set
--   pin_version     bumped on every PIN change or reset, which ends every session signed before it
--   must_change_pin set by an admin reset: the temporary PIN can only be used to choose a new one
--   locked_until    5 wrong PINs lock the account for 15 minutes
--   is_demo         a demo or test account: fictional data only, shown with a banner
--   pin_fixed       a SHARED demo account: its PIN cannot be changed or reset (so one tester cannot lock out the others)
ALTER TABLE teachers ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'teacher';
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'teachers_role_check') THEN
        ALTER TABLE teachers ADD CONSTRAINT teachers_role_check CHECK (role IN ('teacher', 'school_admin'));
    END IF;
END $$;
ALTER TABLE teachers ADD COLUMN IF NOT EXISTS pin_hash            TEXT;
ALTER TABLE teachers ADD COLUMN IF NOT EXISTS pin_version         INTEGER NOT NULL DEFAULT 0;
ALTER TABLE teachers ADD COLUMN IF NOT EXISTS must_change_pin     BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE teachers ADD COLUMN IF NOT EXISTS failed_pin_attempts SMALLINT NOT NULL DEFAULT 0;
ALTER TABLE teachers ADD COLUMN IF NOT EXISTS locked_until        TIMESTAMPTZ;
ALTER TABLE teachers ADD COLUMN IF NOT EXISTS pin_changed_at      TIMESTAMPTZ;
ALTER TABLE teachers ADD COLUMN IF NOT EXISTS is_demo             BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE teachers ADD COLUMN IF NOT EXISTS pin_fixed           BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE schools  ADD COLUMN IF NOT EXISTS join_code           TEXT;

CREATE TABLE IF NOT EXISTS auth_events (
    id          BIGSERIAL PRIMARY KEY,
    teacher_id  UUID REFERENCES teachers(id) ON DELETE SET NULL,
    event       TEXT NOT NULL,              -- login_ok, login_failed, locked, pin_changed, pin_reset_by_admin, unlocked, registered, class_report_export, class_summary_view
    detail      TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_auth_events_teacher ON auth_events (teacher_id, created_at DESC);
