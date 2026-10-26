-- ============================================================================
-- ANKUR SAATHI — Layer 2: Curated Content Bank Schema
-- Postgres + pgvector for semantic retrieval
-- ============================================================================
-- Four content types, each with:
--   1. Structured metadata linking back to L1 (competency IDs, grade ranges)
--   2. The content itself (templates, passages, instructions)
--   3. An embedding column (vector) for semantic retrieval
--   4. A searchable text column for hybrid search (tsvector)
--
-- Retrieval pattern:
--   The orchestration engine queries L2 with the L1 context:
--   "I need an anchor activity for N2.3.2 (2-digit addition with carry),
--    Beginner group is on N1.2.4 (place value), classroom has 62 children"
--   → semantic search finds the most relevant template
--   → Claude adapts it to the specific day's context
-- ============================================================================

-- pgvector extension (skip if not available — schema works without it)
-- CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- 1. ANCHOR ACTIVITY TEMPLATES
-- Whole-class shared activities that engage all levels simultaneously.
-- The "market story" from the proposal is one of these.
-- Retrieved by: target competency + thematic context
-- ============================================================================

CREATE TABLE anchor_activities (
    id              TEXT PRIMARY KEY,          -- 'ANC-001', 'ANC-002'
    
    -- What this anchor covers
    title_en        TEXT NOT NULL,
    title_hi        TEXT NOT NULL,
    description_en  TEXT NOT NULL,             -- 1-2 sentence summary
    
    -- The template itself — structured for Claude to adapt
    -- Contains placeholders that Claude fills with day-specific content:
    --   {{beginner_task}}, {{progressor_task}}, {{proficient_task}}
    --   {{number_context}}, {{story_character}}, etc.
    template_body   TEXT NOT NULL,
    
    -- L1 linkage: which competencies this anchor works with
    -- Array because one anchor can serve multiple competencies
    primary_competency_ids   TEXT[] NOT NULL,   -- Best fit competencies
    secondary_competency_ids TEXT[],            -- Also works for these
    
    -- Constraints
    domain_id       TEXT NOT NULL REFERENCES domains(id),
    grade_range     TEXT[] NOT NULL,            -- ['grade_1','grade_2'] = works for G1-G2
    min_children    SMALLINT DEFAULT 10,        -- Minimum class size this works for
    max_children    SMALLINT DEFAULT 80,
    duration_minutes SMALLINT DEFAULT 10,       -- Target: 10 min anchor
    
    -- Thematic tags for retrieval diversity
    theme           TEXT NOT NULL,              -- 'market', 'kitchen', 'farm', 'festival', 'school', 'travel'
    setting         TEXT,                       -- 'rural', 'urban', 'universal'
    
    -- TLM requirements (what the teacher needs)
    requires_print  BOOLEAN DEFAULT FALSE,      -- Needs printed handout
    requires_tlm    BOOLEAN DEFAULT FALSE,      -- Needs physical TLM
    tlm_ids         TEXT[],                     -- References to TLM table
    
    -- Semantic search
    -- Embedding of: title + description + template_body + competency names
    embedding       vector(1024),               -- BAAI/bge-m3 dimension (migration 12)
    search_text     tsvector,                   -- For hybrid keyword search
    
    -- Metadata
    source          TEXT,                       -- 'original', 'adapted_from_pratham', etc.
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_anchor_domain ON anchor_activities(domain_id);
CREATE INDEX idx_anchor_theme ON anchor_activities(theme);
CREATE INDEX idx_anchor_grades ON anchor_activities USING GIN(grade_range);
CREATE INDEX idx_anchor_competencies ON anchor_activities USING GIN(primary_competency_ids);
CREATE INDEX idx_anchor_search ON anchor_activities USING GIN(search_text);
-- CREATE INDEX idx_anchor_embedding ON anchor_activities USING ivfflat(embedding vector_cosine_ops);


-- ============================================================================
-- 2. READING PASSAGES
-- Graded, vocabulary-controlled, culturally relevant passages for:
--   - Fluency practice (oral reading with CWPM measurement)
--   - Comprehension exercises (literal + inferential questions)
--   - Independent reading during station rotation
-- Retrieved by: target fluency level + vocabulary level + theme
-- ============================================================================

CREATE TABLE reading_passages (
    id              TEXT PRIMARY KEY,           -- 'RP-001'
    
    -- The passage
    title_hi        TEXT NOT NULL,
    passage_hi      TEXT NOT NULL,              -- The actual Hindi text
    word_count      SMALLINT NOT NULL,          -- For CWPM calculation
    
    -- Difficulty grading
    target_grade    TEXT NOT NULL,              -- 'grade_1', 'grade_2', 'grade_3'
    difficulty      TEXT NOT NULL               -- 'easy', 'medium', 'hard' within grade
        CHECK (difficulty IN ('easy', 'medium', 'hard')),
    
    -- Vocabulary control
    -- Which matra/decoding features appear in this passage
    decoding_features TEXT[] NOT NULL,          -- ['basic_matras', 'all_matras', 'conjuncts', 'halant']
    sight_word_percentage SMALLINT,             -- % of words that are high-frequency sight words
    
    -- Expected fluency range (CWPM) for this passage at each level
    -- Used to calibrate assessment: if a child reads this at 45 CWPM,
    -- and the passage is "medium grade_2", that maps to Partially Achieved
    expected_cwpm   JSONB,                     
    -- {"achieved": {"min": 40}, "partially_achieved": {"min": 25, "max": 39}, "not_achieved": {"max": 24}}
    
    -- Comprehension questions (generated or curated)
    comprehension_questions JSONB,
    -- [
    --   {"type": "literal", "question_hi": "...", "answer_hi": "..."},
    --   {"type": "inferential", "question_hi": "...", "answer_hi": "..."},
    --   {"type": "main_idea", "question_hi": "...", "answer_hi": "..."}
    -- ]
    
    -- L1 linkage
    fluency_competency_id TEXT,                -- Which fluency Lakshya this targets
    comprehension_competency_ids TEXT[],        -- Which comprehension Lakshyas
    
    -- Content metadata
    theme           TEXT,                       -- 'animals', 'family', 'festival', 'nature', 'school'
    setting         TEXT DEFAULT 'rural',
    genre           TEXT DEFAULT 'narrative'     -- 'narrative', 'informational', 'poem', 'dialogue'
        CHECK (genre IN ('narrative', 'informational', 'poem', 'dialogue')),
    
    -- Semantic search
    embedding       vector(1024),
    search_text     tsvector,
    
    source          TEXT,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_passage_grade ON reading_passages(target_grade);
CREATE INDEX idx_passage_difficulty ON reading_passages(difficulty);
CREATE INDEX idx_passage_features ON reading_passages USING GIN(decoding_features);
CREATE INDEX idx_passage_search ON reading_passages USING GIN(search_text);


-- ============================================================================
-- 3. INTERVENTION TEMPLATES
-- Remedial activities mapped to specific L1 misconceptions.
-- When Claude Vision detects a misconception → retrieves the matching
-- intervention → adapts it for tomorrow's re-teaching segment.
-- Retrieved by: misconception ID (deterministic) + semantic similarity
-- ============================================================================

CREATE TABLE intervention_templates (
    id              TEXT PRIMARY KEY,           -- 'INT-OP-005'
    
    -- What this intervention addresses
    title_en        TEXT NOT NULL,
    title_hi        TEXT NOT NULL,
    description_en  TEXT NOT NULL,              -- What the intervention does
    
    -- L1 linkage: which misconceptions this addresses
    -- Direct mapping — this is deterministic, not semantic
    misconception_ids TEXT[] NOT NULL,          -- ['N2.3.2-M1', 'N2.3.2-M2']
    competency_ids   TEXT[] NOT NULL,           -- ['N2.3.2']
    
    -- The intervention template
    -- Structured steps the teacher follows during re-teaching
    steps           JSONB NOT NULL,
    -- [
    --   {"step": 1, "type": "demonstrate", "instruction_hi": "...", "instruction_en": "...", "duration_min": 3},
    --   {"step": 2, "type": "guided_practice", "instruction_hi": "...", "instruction_en": "...", "duration_min": 5},
    --   {"step": 3, "type": "check", "instruction_hi": "...", "instruction_en": "...", "duration_min": 2}
    -- ]
    
    -- What level/modality this is designed for
    target_level    TEXT NOT NULL               -- 'beginner', 'progressor', 'any'
        CHECK (target_level IN ('beginner', 'progressor', 'any')),
    modality        TEXT NOT NULL               -- 'hands_on', 'worksheet', 'oral', 'mixed'
        CHECK (modality IN ('hands_on', 'worksheet', 'oral', 'mixed')),
    domain_id       TEXT NOT NULL REFERENCES domains(id),
    
    -- Resource requirements
    duration_minutes SMALLINT DEFAULT 10,
    requires_tlm    BOOLEAN DEFAULT FALSE,
    tlm_ids         TEXT[],
    requires_print  BOOLEAN DEFAULT FALSE,
    group_size      TEXT DEFAULT 'small'        -- 'individual', 'small', 'whole_class'
        CHECK (group_size IN ('individual', 'small', 'whole_class')),
    
    -- Effectiveness tracking (updated from field data)
    times_used      INTEGER DEFAULT 0,
    effectiveness_score NUMERIC(3,2),           -- 0.00-1.00, updated from outcomes
    
    -- Semantic search
    embedding       vector(1024),
    search_text     tsvector,
    
    source          TEXT,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_intervention_misconceptions ON intervention_templates USING GIN(misconception_ids);
CREATE INDEX idx_intervention_competencies ON intervention_templates USING GIN(competency_ids);
CREATE INDEX idx_intervention_domain ON intervention_templates(domain_id);
CREATE INDEX idx_intervention_level ON intervention_templates(target_level);
CREATE INDEX idx_intervention_search ON intervention_templates USING GIN(search_text);


-- ============================================================================
-- 4. TLM REFERENCES (Teaching-Learning Materials)
-- What physical materials are actually available in government schools.
-- Referenced by anchor activities and intervention templates.
-- ============================================================================

CREATE TABLE tlm_references (
    id              TEXT PRIMARY KEY,           -- 'TLM-001'
    
    name_en         TEXT NOT NULL,
    name_hi         TEXT NOT NULL,
    description_en  TEXT NOT NULL,
    
    -- What it's used for
    domain_ids      TEXT[] NOT NULL,            -- Which domains this TLM serves
    competency_ids  TEXT[],                     -- Specific competencies it helps with
    
    -- Availability in government schools
    availability    TEXT NOT NULL DEFAULT 'common'
        CHECK (availability IN ('universal', 'common', 'uncommon', 'diy')),
    -- universal = every school has it (blackboard, chalk)
    -- common = most schools (number chart, letter chart)
    -- uncommon = some schools (base-10 blocks, fraction kits)
    -- diy = teacher can make it (bundling sticks, paper cutouts)
    
    diy_instructions TEXT,                     -- How to make it if not available
    
    -- Semantic search
    embedding       vector(1024),
    search_text     tsvector,
    
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_tlm_domains ON tlm_references USING GIN(domain_ids);
CREATE INDEX idx_tlm_availability ON tlm_references(availability);


-- ============================================================================
-- RETRIEVAL QUERY PATTERNS
-- These are the queries the orchestration pipeline will use.
-- Included here as comments for Arjun's reference.
-- ============================================================================

-- PATTERN 1: Find anchor activity for a competency (semantic + filter)
-- SELECT id, title_en, template_body,
--        1 - (embedding <=> $query_embedding) AS similarity
-- FROM anchor_activities
-- WHERE domain_id = $domain
--   AND $grade = ANY(grade_range)
--   AND ($competency_id = ANY(primary_competency_ids) 
--        OR $competency_id = ANY(secondary_competency_ids))
--   AND is_active = TRUE
-- ORDER BY similarity DESC
-- LIMIT 3;

-- PATTERN 2: Find reading passage by difficulty (deterministic + semantic)
-- SELECT id, title_hi, passage_hi, word_count, difficulty
-- FROM reading_passages
-- WHERE target_grade = $grade
--   AND difficulty = $difficulty
--   AND $required_feature <@ decoding_features
--   AND is_active = TRUE
-- ORDER BY 1 - (embedding <=> $query_embedding) DESC
-- LIMIT 3;

-- PATTERN 3: Find intervention for a detected misconception (deterministic)
-- SELECT id, title_en, steps, modality, duration_minutes
-- FROM intervention_templates
-- WHERE $misconception_id = ANY(misconception_ids)
--   AND (target_level = $level OR target_level = 'any')
--   AND is_active = TRUE
-- ORDER BY effectiveness_score DESC NULLS LAST
-- LIMIT 2;

-- PATTERN 4: Hybrid search (keyword + semantic) for any content type
-- SELECT id, title_en,
--        ts_rank(search_text, plainto_tsquery('hindi', $query)) AS text_rank,
--        1 - (embedding <=> $query_embedding) AS semantic_rank
-- FROM anchor_activities
-- WHERE search_text @@ plainto_tsquery('hindi', $query)
--    OR (embedding <=> $query_embedding) < 0.3
-- ORDER BY (0.3 * text_rank + 0.7 * semantic_rank) DESC
-- LIMIT 5;
