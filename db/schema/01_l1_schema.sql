-- ============================================================================
-- ANKUR SAATHI — Layer 1 Structured Curriculum KB
-- Postgres Schema v1
-- ============================================================================
-- Covers:
--   1. NIPUN Bharat Lakshya competency tree (hierarchical with prerequisite DAG)
--   2. Per-Lakshya A/PA/NA criteria + assessment modality tags
--   3. Misconception taxonomy (error patterns → diagnostics → interventions)
--   4. State weekly curriculum plan structure
--   5. Classroom profile (teacher, children, Lakshya positions, groups)
-- ============================================================================

-- Enable pgvector (needed for Layer 2, but good to have extension ready)
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- 1. COMPETENCY TREE
-- Hierarchy: domain → subdomain → competency (= Lakshya node) → learning_outcome
-- ============================================================================

-- Top-level subject domains
CREATE TABLE domains (
    id          TEXT PRIMARY KEY,          -- 'numeracy', 'r1_literacy', 'r2_literacy'
    name_en     TEXT NOT NULL,
    name_hi     TEXT NOT NULL,             -- Hindi label for UI
    sort_order  SMALLINT NOT NULL DEFAULT 0
);

-- Subdomains within each domain
-- e.g., Numeracy: number_sense, operations, measurement, geometry, data_handling
-- e.g., R1 Literacy: phonological_awareness, decoding, fluency, comprehension, writing
CREATE TABLE subdomains (
    id          TEXT PRIMARY KEY,          -- 'num_operations', 'lit_decoding'
    domain_id   TEXT NOT NULL REFERENCES domains(id),
    name_en     TEXT NOT NULL,
    name_hi     TEXT NOT NULL,
    description TEXT,
    sort_order  SMALLINT NOT NULL DEFAULT 0
);

CREATE INDEX idx_subdomains_domain ON subdomains(domain_id);

-- The core entity: each row is one NIPUN Bharat Lakshya competency node
-- This is what the teacher selects, what children are tracked against,
-- and what drives B/P/P grouping.
CREATE TABLE competencies (
    id              TEXT PRIMARY KEY,     -- NIPUN-style code: 'N1.2.3', 'L1.3.1'
    subdomain_id    TEXT NOT NULL REFERENCES subdomains(id),
    
    -- Human-readable
    name_en         TEXT NOT NULL,        -- 'Adds two 2-digit numbers with regrouping'
    name_hi         TEXT NOT NULL,        -- Hindi equivalent
    description_en  TEXT,                 -- Fuller description if needed
    description_hi  TEXT,
    
    -- Position on the Lakshya ladder
    grade_level     TEXT NOT NULL,        -- 'balvatika', 'grade_1', 'grade_2', 'grade_3'
    sort_order      SMALLINT NOT NULL,    -- Within the subdomain, for progression ordering
    
    -- ================================================================
    -- ASSESSMENT MODALITY TAG
    -- Determines which of the 3 evidence channels is primary for this
    -- competency. Critical for the Review screen routing.
    -- ================================================================
    assessment_modality TEXT NOT NULL 
        CHECK (assessment_modality IN (
            'written',          -- worksheet / photo capture → Claude Vision
            'observed',         -- teacher real-time judgment (tap A/PA/NA)
            'oral_reading',     -- reading fluency (stopwatch + manual entry)
            'adaptive'          -- system chooses based on child's level
        )),
    
    -- ================================================================
    -- A/PA/NA CRITERIA (per-Lakshya, NOT universal)
    -- Stored as JSONB because criteria structure differs by modality type.
    -- ================================================================
    -- Example for written/computation:
    -- {
    --   "type": "computation",
    --   "achieved":          {"min_accuracy": 0.80, "sessions_required": 2, "no_persistent_misconception": true},
    --   "partially_achieved": {"accuracy_range": [0.40, 0.80], "or_has_misconception": true},
    --   "not_achieved":      {"max_accuracy": 0.40, "or_cannot_attempt": true}
    -- }
    --
    -- Example for oral_reading/fluency:
    -- {
    --   "type": "fluency",
    --   "achieved":          {"min_cwpm": 60, "min_accuracy": 0.95, "comprehension_required": true},
    --   "partially_achieved": {"cwpm_range": [40, 59], "or_accuracy_range": [0.90, 0.95], "or_no_comprehension": true},
    --   "not_achieved":      {"max_cwpm": 40, "or_max_accuracy": 0.90}
    -- }
    --
    -- Example for observed:
    -- {
    --   "type": "observational",
    --   "achieved":          {"description": "Counts 20 objects correctly with 1:1 correspondence, answers 'how many?'"},
    --   "partially_achieved": {"description": "Tagging errors or loses track beyond 15"},
    --   "not_achieved":      {"description": "Cannot count beyond 10 with 1:1 correspondence"}
    -- }
    apna_criteria   JSONB NOT NULL,       -- "apna" = A/PA/NA :)
    
    -- For worksheet generation constraints
    number_range    JSONB,                -- e.g., {"min": 10, "max": 99} for operations
    problem_types   TEXT[],               -- e.g., {'addition_no_carry', 'addition_with_carry'}
    
    -- Metadata
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_competencies_subdomain ON competencies(subdomain_id);
CREATE INDEX idx_competencies_grade ON competencies(grade_level);
CREATE INDEX idx_competencies_modality ON competencies(assessment_modality);

-- Prerequisite links between competencies (DAG — not strictly linear)
-- A child should have mastered ALL prerequisites before being taught this competency.
-- This drives: (a) what Beginners get when teacher selects a competency,
--              (b) validation that generated content is pedagogically sequenced.
CREATE TABLE competency_prerequisites (
    competency_id       TEXT NOT NULL REFERENCES competencies(id),
    prerequisite_id     TEXT NOT NULL REFERENCES competencies(id),
    
    -- How critical is this prerequisite?
    -- 'hard' = must be mastered (blocks advancement)
    -- 'soft' = strongly recommended but not blocking
    prerequisite_type   TEXT NOT NULL DEFAULT 'hard'
        CHECK (prerequisite_type IN ('hard', 'soft')),
    
    PRIMARY KEY (competency_id, prerequisite_id),
    CHECK (competency_id != prerequisite_id)
);

CREATE INDEX idx_prereqs_prerequisite ON competency_prerequisites(prerequisite_id);

-- Learning outcomes: the granular measurable items under each competency.
-- These are what individual worksheet problems or observation items map to.
-- A competency's A/PA/NA is determined by performance across its learning outcomes.
CREATE TABLE learning_outcomes (
    id              TEXT PRIMARY KEY,     -- 'N1.2.3.a', 'N1.2.3.b'
    competency_id   TEXT NOT NULL REFERENCES competencies(id),
    name_en         TEXT NOT NULL,
    name_hi         TEXT NOT NULL,
    description_en  TEXT,
    sort_order      SMALLINT NOT NULL DEFAULT 0,
    
    -- Each outcome can have its own assessment approach
    assessment_modality TEXT             -- Override competency-level modality if different
        CHECK (assessment_modality IN ('written', 'observed', 'oral_reading', 'adaptive'))
);

CREATE INDEX idx_outcomes_competency ON learning_outcomes(competency_id);


-- ============================================================================
-- 3. MISCONCEPTION TAXONOMY
-- Error patterns mapped to diagnostic indicators and interventions,
-- per competency. This is what Claude Vision matches against — NOT hallucinated.
-- ============================================================================

CREATE TABLE misconceptions (
    id                  TEXT PRIMARY KEY,     -- 'N2.4.2-M1' (competency + sequence)
    competency_id       TEXT NOT NULL REFERENCES competencies(id),
    
    -- What the error pattern looks like
    name_en             TEXT NOT NULL,        -- 'Place-value carry-over confusion'
    name_hi             TEXT NOT NULL,
    error_pattern       TEXT NOT NULL,        -- 'Writes ones digit of sum, drops tens carry'
    
    -- How to detect it (for Claude Vision prompt + teacher guidance)
    diagnostic_indicator TEXT NOT NULL,       -- 'Answer is exactly 10 less than correct, consistent across 3+ problems'
    
    -- Example of the error (for Claude Vision context)
    example_correct     TEXT,                 -- '34 + 28 = 62'
    example_incorrect   TEXT,                 -- '34 + 28 = 52'
    
    -- What to do about it (maps to Layer 2 intervention templates)
    intervention_strategy TEXT NOT NULL,      -- 'Re-teach place value with bundling sticks...'
    intervention_template_ids TEXT[],         -- References to Layer 2 content bank
    
    -- Severity helps prioritise re-teaching
    severity            TEXT NOT NULL DEFAULT 'moderate'
        CHECK (severity IN ('critical', 'moderate', 'minor')),
        -- critical = blocks all further progress in this subdomain
        -- moderate = specific to this competency
        -- minor = arithmetic slip, self-correctable
    
    -- Frequency in the field (helps Claude Vision weigh competing diagnoses)
    frequency           TEXT DEFAULT 'common'
        CHECK (frequency IN ('very_common', 'common', 'uncommon')),
    
    sort_order          SMALLINT NOT NULL DEFAULT 0
);

CREATE INDEX idx_misconceptions_competency ON misconceptions(competency_id);
CREATE INDEX idx_misconceptions_severity ON misconceptions(severity);


-- ============================================================================
-- 4. STATE WEEKLY CURRICULUM PLAN
-- Maps: state → grade → week → ordered topics (Lakshya competencies)
-- Only state-specific layer; everything else is national.
-- ============================================================================

CREATE TABLE states (
    id          TEXT PRIMARY KEY,          -- 'mp', 'up', 'rj', 'cg'
    name_en     TEXT NOT NULL,
    name_hi     TEXT NOT NULL,
    scert_name  TEXT,                      -- Official SCERT name
    is_active   BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE curriculum_plans (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    state_id    TEXT NOT NULL REFERENCES states(id),
    
    -- Which academic year / version
    academic_year   TEXT NOT NULL,         -- '2026-27'
    version         TEXT DEFAULT 'v1',
    
    -- Metadata
    source          TEXT,                  -- 'SCERT weekly plan circular'
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(state_id, academic_year, version)
);

CREATE TABLE curriculum_weeks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    plan_id         UUID NOT NULL REFERENCES curriculum_plans(id) ON DELETE CASCADE,
    
    grade_level     TEXT NOT NULL,         -- 'grade_1', 'grade_2', 'grade_3'
    domain_id       TEXT NOT NULL REFERENCES domains(id),
    week_number     SMALLINT NOT NULL,     -- 1-52
    
    -- What the state plan prescribes for this week
    topic_title_en  TEXT NOT NULL,         -- 'Two-digit addition with regrouping'
    topic_title_hi  TEXT NOT NULL,
    
    -- Map to our competency tree (the critical link)
    competency_ids  TEXT[] NOT NULL,       -- Array of competency IDs covered this week
    
    -- Optional: state's own pacing notes
    notes           TEXT,
    
    -- Ordering within the week (some weeks cover multiple topics in sequence)
    sort_order      SMALLINT NOT NULL DEFAULT 0,
    
    UNIQUE(plan_id, grade_level, domain_id, week_number, sort_order)
);

CREATE INDEX idx_curriculum_weeks_plan ON curriculum_weeks(plan_id);
CREATE INDEX idx_curriculum_weeks_grade_domain ON curriculum_weeks(grade_level, domain_id);
CREATE INDEX idx_curriculum_weeks_week ON curriculum_weeks(week_number);


-- ============================================================================
-- 5. CLASSROOM PROFILE
-- Teacher → school → classroom → children → Lakshya positions → groups
-- Privacy: names stored ONLY on-device (IndexedDB). Server has roll numbers only.
-- ============================================================================

CREATE TABLE schools (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    state_id        TEXT NOT NULL REFERENCES states(id),
    
    -- Anonymised identifiers (no real school names on server)
    school_code     TEXT NOT NULL UNIQUE,  -- UDISE or internal code
    block_name      TEXT,                  -- For MLO reporting aggregation
    district_name   TEXT,                  -- For MLO reporting aggregation
    
    -- School characteristics that affect plan generation
    has_printer     BOOLEAN NOT NULL DEFAULT FALSE,
    num_classrooms  SMALLINT,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE teachers (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    school_id       UUID NOT NULL REFERENCES schools(id),
    
    -- Auth (phone-number login)
    phone_hash      TEXT NOT NULL UNIQUE,  -- Hashed phone number, not plaintext
    
    -- Teaching context
    enrolled_grades TEXT[] NOT NULL,       -- ['grade_1', 'grade_2', 'grade_3']
    is_multigrade   BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Time constraints (affect rotation schedule generation)
    available_minutes SMALLINT NOT NULL DEFAULT 90,  -- Teaching time per session
    
    -- Preferences
    preferred_language TEXT NOT NULL DEFAULT 'hi',
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active_at  TIMESTAMPTZ
);

CREATE INDEX idx_teachers_school ON teachers(school_id);

-- Children: server knows roll numbers + enrolled grade, NEVER names.
-- Name ↔ roll mapping is in IndexedDB on teacher's device only.
CREATE TABLE children (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    teacher_id      UUID NOT NULL REFERENCES teachers(id) ON DELETE CASCADE,
    
    roll_number     SMALLINT NOT NULL,     -- 1-99, unique within teacher's class
    enrolled_grade  TEXT NOT NULL,          -- 'grade_1', 'grade_2', 'grade_3'
    
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(teacher_id, roll_number)
);

CREATE INDEX idx_children_teacher ON children(teacher_id);

-- Per-child Lakshya positions: WHERE each child sits on the progression ladder.
-- Separate tracking per domain (a child can be Beginner in numeracy, Proficient in literacy).
-- This is the core adaptive state that drives grouping.
CREATE TABLE child_lakshya_positions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    child_id        UUID NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    domain_id       TEXT NOT NULL REFERENCES domains(id),
    
    -- Current position on the ladder
    -- The HIGHEST competency where the child has consistent mastery
    current_competency_id TEXT NOT NULL REFERENCES competencies(id),
    
    -- B/P/P classification (derived from A/PA/NA across the child's Lakshyas)
    -- Beginner = mostly NA, Progressor = ≥50% PA, Proficient = ≥75% A
    bpp_level       TEXT NOT NULL
        CHECK (bpp_level IN ('beginner', 'progressor', 'proficient')),
    
    -- Evidence basis for this position
    source          TEXT NOT NULL          -- 'baseline_external', 'baseline_internal', 'daily', 'periodic'
        CHECK (source IN ('baseline_external', 'baseline_internal', 'daily', 'periodic')),
    evidence_days   SMALLINT DEFAULT 0,    -- Days of consistent evidence at this level
    last_assessed   TIMESTAMPTZ,
    
    -- For level-change tracking
    previous_competency_id TEXT REFERENCES competencies(id),
    previous_bpp_level     TEXT,
    level_changed_at       TIMESTAMPTZ,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(child_id, domain_id)
);

CREATE INDEX idx_child_positions_child ON child_lakshya_positions(child_id);
CREATE INDEX idx_child_positions_domain ON child_lakshya_positions(domain_id);
CREATE INDEX idx_child_positions_bpp ON child_lakshya_positions(bpp_level);
CREATE INDEX idx_child_positions_competency ON child_lakshya_positions(current_competency_id);

-- Per-child, per-competency A/PA/NA status
-- Granular tracking: each Lakshya the child has been assessed on
CREATE TABLE child_competency_status (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    child_id        UUID NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    competency_id   TEXT NOT NULL REFERENCES competencies(id),
    
    -- Current status
    status          TEXT NOT NULL
        CHECK (status IN ('achieved', 'partially_achieved', 'not_achieved', 'not_assessed')),
    
    -- Evidence trail
    assessment_count    SMALLINT NOT NULL DEFAULT 0,
    last_assessment_date DATE,
    consecutive_days_at_status SMALLINT DEFAULT 0,  -- For the 3+ day rule
    
    -- Confidence (photo = high, observed = teacher-reported)
    confidence      TEXT DEFAULT 'teacher_reported'
        CHECK (confidence IN ('high', 'medium', 'teacher_reported')),
    
    -- Misconceptions detected (references misconception taxonomy)
    active_misconception_ids TEXT[],       -- Currently active misconceptions
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(child_id, competency_id)
);

CREATE INDEX idx_child_status_child ON child_competency_status(child_id);
CREATE INDEX idx_child_status_competency ON child_competency_status(competency_id);
CREATE INDEX idx_child_status_status ON child_competency_status(status);

-- Daily teaching groups: the 3 clusters per domain per teacher per day.
-- Groups are ephemeral — rebuilt when children move levels or during periodic assessment.
CREATE TABLE teaching_groups (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    teacher_id      UUID NOT NULL REFERENCES teachers(id) ON DELETE CASCADE,
    domain_id       TEXT NOT NULL REFERENCES domains(id),
    
    group_label     TEXT NOT NULL           -- 'beginner', 'progressor', 'proficient'
        CHECK (group_label IN ('beginner', 'progressor', 'proficient')),
    
    -- What this group is working on
    target_competency_id TEXT NOT NULL REFERENCES competencies(id),
    
    -- Children in this group (array of child IDs)
    child_ids       UUID[] NOT NULL,
    
    -- Group metadata for rotation scheduling
    child_count     SMALLINT NOT NULL,
    priority_rank   SMALLINT NOT NULL,     -- 1 = gets first/longest teaching slot
    -- Priority based on: yesterday's gap analysis, misconception density
    
    -- Validity
    effective_from  DATE NOT NULL,
    effective_until DATE,                  -- NULL = current
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_groups_teacher_domain ON teaching_groups(teacher_id, domain_id);
CREATE INDEX idx_groups_effective ON teaching_groups(effective_from, effective_until);


-- ============================================================================
-- ASSESSMENT EVIDENCE LOG
-- Records every piece of evidence across all 3 channels.
-- Feeds the adaptive loop: evidence → A/PA/NA update → group recalculation.
-- ============================================================================

CREATE TABLE assessment_evidence (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    child_id        UUID NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    competency_id   TEXT NOT NULL REFERENCES competencies(id),
    teacher_id      UUID NOT NULL REFERENCES teachers(id),
    
    -- Which channel captured this evidence
    channel         TEXT NOT NULL
        CHECK (channel IN ('written_photo', 'observed', 'oral_reading')),
    
    -- Result
    status          TEXT NOT NULL
        CHECK (status IN ('achieved', 'partially_achieved', 'not_achieved')),
    
    -- Channel-specific data
    -- For written_photo:
    --   {"answers": [{"problem_id": "P1", "response": "52", "correct": false}], 
    --    "accuracy": 0.6, "vision_confidence": 0.92}
    -- For observed:
    --   {"teacher_judgment": "partially_achieved", "notes": "loses count at 15"}
    -- For oral_reading:
    --   {"cwpm": 38, "error_count": 3, "passage_id": "RP-042", 
    --    "error_types": ["conjunct_consonant"]}
    evidence_data   JSONB NOT NULL,
    
    -- Misconceptions detected (if any)
    detected_misconception_ids TEXT[],
    
    -- Confidence level
    confidence      TEXT NOT NULL DEFAULT 'medium'
        CHECK (confidence IN ('high', 'medium', 'low', 'needs_verification')),
    
    -- Context
    session_date    DATE NOT NULL,
    assessment_tier TEXT NOT NULL DEFAULT 'daily'
        CHECK (assessment_tier IN ('baseline', 'daily', 'periodic', 'on_demand')),
    
    -- Teacher's pre-AI judgment (captured BEFORE AI analysis)
    teacher_pre_judgment TEXT
        CHECK (teacher_pre_judgment IN ('advance', 'reteach', 'not_sure')),
    
    -- AI's post-analysis recommendation
    ai_recommendation   TEXT
        CHECK (ai_recommendation IN ('advance', 'reteach', 'flag_discrepancy')),
    
    -- Final confirmed decision
    final_decision      TEXT
        CHECK (final_decision IN ('advance', 'reteach')),
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_evidence_child ON assessment_evidence(child_id);
CREATE INDEX idx_evidence_competency ON assessment_evidence(competency_id);
CREATE INDEX idx_evidence_date ON assessment_evidence(session_date);
CREATE INDEX idx_evidence_channel ON assessment_evidence(channel);
CREATE INDEX idx_evidence_tier ON assessment_evidence(assessment_tier);
CREATE INDEX idx_evidence_teacher_date ON assessment_evidence(teacher_id, session_date);


-- ============================================================================
-- DAILY PLAN LOG
-- Records what was generated each day (for explainability + debugging).
-- The "Why this plan?" panel reads from this.
-- ============================================================================

CREATE TABLE daily_plans (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    teacher_id      UUID NOT NULL REFERENCES teachers(id),
    
    plan_date       DATE NOT NULL,
    domain_id       TEXT NOT NULL REFERENCES domains(id),
    
    -- Teacher's selection
    selected_competency_id TEXT NOT NULL REFERENCES competencies(id),
    
    -- What was generated (the full Dainik Yojana as structured JSON)
    -- Includes: anchor activity, 3× worksheets, rotation schedule,
    --           talking points, transition scripts, peer monitor assignments
    plan_content    JSONB NOT NULL,
    
    -- Explainability metadata
    -- Why each component was chosen (for the "Why this plan?" panel)
    explainability  JSONB NOT NULL,
    -- {
    --   "beginner_first_because": "4/6 Beginners showed place-value misconception yesterday",
    --   "anchor_template_source": "ANC-017 (Village Market)",
    --   "reteach_segments": [{"competency": "N2.3.1", "reason": "3 children flagged"}],
    --   "l2_templates_used": ["ANC-017", "INT-003"]
    -- }
    
    -- Groups snapshot at plan generation time
    groups_snapshot JSONB NOT NULL,
    
    -- Generation metadata
    generation_time_ms  INTEGER,          -- Track the <60s target
    claude_model        TEXT,
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(teacher_id, plan_date, domain_id)
);

CREATE INDEX idx_plans_teacher_date ON daily_plans(teacher_id, plan_date);


-- ============================================================================
-- HELPER VIEWS
-- ============================================================================

-- View: competency tree with full hierarchy path (useful for UI rendering)
CREATE VIEW v_competency_tree AS
SELECT 
    c.id AS competency_id,
    c.name_en AS competency_name,
    c.name_hi AS competency_name_hi,
    c.grade_level,
    c.assessment_modality,
    c.sort_order AS competency_sort,
    s.id AS subdomain_id,
    s.name_en AS subdomain_name,
    s.sort_order AS subdomain_sort,
    d.id AS domain_id,
    d.name_en AS domain_name,
    d.sort_order AS domain_sort
FROM competencies c
JOIN subdomains s ON c.subdomain_id = s.id
JOIN domains d ON s.domain_id = d.id
WHERE c.is_active = TRUE
ORDER BY d.sort_order, s.sort_order, c.grade_level, c.sort_order;

-- View: classroom B/P/P summary (for Progress screen + MLO report)
CREATE VIEW v_classroom_bpp_summary AS
SELECT 
    t.id AS teacher_id,
    clp.domain_id,
    clp.bpp_level,
    COUNT(*) AS child_count,
    ARRAY_AGG(c.roll_number ORDER BY c.roll_number) AS roll_numbers
FROM child_lakshya_positions clp
JOIN children c ON clp.child_id = c.id
JOIN teachers t ON c.teacher_id = t.id
WHERE c.is_active = TRUE
GROUP BY t.id, clp.domain_id, clp.bpp_level;

-- View: children needing level change review (3+ consecutive days)
CREATE VIEW v_level_change_candidates AS
SELECT 
    cs.child_id,
    cs.competency_id,
    cs.status,
    cs.consecutive_days_at_status,
    c.roll_number,
    c.teacher_id,
    comp.grade_level,
    comp.name_en AS competency_name
FROM child_competency_status cs
JOIN children c ON cs.child_id = c.id
JOIN competencies comp ON cs.competency_id = comp.id
WHERE cs.consecutive_days_at_status >= 3
  AND cs.status IN ('achieved', 'not_achieved')
  AND c.is_active = TRUE;
