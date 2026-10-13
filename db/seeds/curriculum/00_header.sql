-- ============================================================================
-- ANKUR SAATHI — Layer 1 KB: Representative State Weekly Curriculum Plan
-- State: Madhya Pradesh (Mission Ankur)
-- Version: representative_v1 (to be replaced with actual SCERT plan)
-- ============================================================================
-- Academic calendar (MP): ~40 teaching weeks
--   Term 1: July (Week 1) → November (Week 20), includes mid-year assessment
--   Term 2: January (Week 21) → April (Week 38-40), includes end-year assessment
--   Weeks 1-2: Baseline assessment period
--   Week 20: Mid-year periodic assessment
--   Week 39-40: End-year periodic assessment
--
-- Pacing principles:
--   1. Follows prerequisite DAG — no competency appears before its hard prereqs
--   2. Spiral: concepts revisited at increasing depth across terms
--   3. Interleaving: number sense and operations alternate to prevent fatigue
--   4. Assessment weeks use existing baseline/periodic tools (no new content)
--   5. Consolidation weeks after major concept clusters
-- ============================================================================

-- State entry
INSERT INTO states (id, name_en, name_hi, scert_name, is_active) VALUES
('mp', 'Madhya Pradesh', 'मध्य प्रदेश', 'State Council of Educational Research and Training (SCERT), MP', TRUE);

-- Curriculum plan header
INSERT INTO curriculum_plans (id, state_id, academic_year, version, source, is_active) VALUES
('a0000000-0000-0000-0000-000000000001', 'mp', '2026-27', 'representative_v1', 
 'Representative plan based on NIPUN Bharat Lakshya progression and MP Mission Ankur grade-level targets. Replace with actual SCERT weekly plan when obtained.', 
 TRUE);
