-- ============================================================================
-- ANKUR SAATHI — Classroom Profile Seed Data
-- A realistic test classroom: 1 teacher, 30 children across Grades 1-3
-- with initial Lakshya positions that create meaningful B/P/P groupings
-- ============================================================================
-- This is the "Sunita Devi" classroom from the proposal:
--   - Multi-grade: Grade 1 (10), Grade 2 (12), Grade 3 (8)
--   - Mixed levels within each grade
--   - Different groupings for numeracy vs literacy (by design)
-- ============================================================================

-- School
INSERT INTO schools (id, state_id, school_code, block_name, district_name, has_printer, num_classrooms)
VALUES ('d0000001-aaaa-bbbb-cccc-000000000001', 'mp', 'MP-DEMO-001', 'Block A', 'District Demo', FALSE, 3);

-- Teacher
INSERT INTO teachers (id, school_id, phone_hash, enrolled_grades, is_multigrade, available_minutes, preferred_language)
VALUES ('10000001-aaaa-bbbb-cccc-000000000001', 
        'd0000001-aaaa-bbbb-cccc-000000000001',
        'MPT101',  -- the demo teacher's employee code (the login name)
        ARRAY['grade_1','grade_2','grade_3'], 
        TRUE, 90, 'hi');

-- ============================================================================
-- 30 CHILDREN
-- Roll numbers 1-30. Names exist ONLY in IndexedDB on teacher's device.
-- Server knows: roll number, enrolled grade, active status. Nothing else.
-- ============================================================================

INSERT INTO children (id, teacher_id, roll_number, enrolled_grade) VALUES
-- Grade 1: Roll 1-10
('a0000000-0000-0000-0001-000000000001', '10000001-aaaa-bbbb-cccc-000000000001', 1, 'grade_1'),
('a0000000-0000-0000-0001-000000000002', '10000001-aaaa-bbbb-cccc-000000000001', 2, 'grade_1'),
('a0000000-0000-0000-0001-000000000003', '10000001-aaaa-bbbb-cccc-000000000001', 3, 'grade_1'),
('a0000000-0000-0000-0001-000000000004', '10000001-aaaa-bbbb-cccc-000000000001', 4, 'grade_1'),
('a0000000-0000-0000-0001-000000000005', '10000001-aaaa-bbbb-cccc-000000000001', 5, 'grade_1'),
('a0000000-0000-0000-0001-000000000006', '10000001-aaaa-bbbb-cccc-000000000001', 6, 'grade_1'),
('a0000000-0000-0000-0001-000000000007', '10000001-aaaa-bbbb-cccc-000000000001', 7, 'grade_1'),
('a0000000-0000-0000-0001-0000000000a8', '10000001-aaaa-bbbb-cccc-000000000001', 8, 'grade_1'),
('a0000000-0000-0000-0001-0000000000a9', '10000001-aaaa-bbbb-cccc-000000000001', 9, 'grade_1'),
('a0000000-0000-0000-0001-000000000010', '10000001-aaaa-bbbb-cccc-000000000001', 10, 'grade_1'),

-- Grade 2: Roll 11-22
('a0000000-0000-0000-0001-000000000011', '10000001-aaaa-bbbb-cccc-000000000001', 11, 'grade_2'),
('a0000000-0000-0000-0001-000000000012', '10000001-aaaa-bbbb-cccc-000000000001', 12, 'grade_2'),
('a0000000-0000-0000-0001-000000000013', '10000001-aaaa-bbbb-cccc-000000000001', 13, 'grade_2'),
('a0000000-0000-0000-0001-000000000014', '10000001-aaaa-bbbb-cccc-000000000001', 14, 'grade_2'),
('a0000000-0000-0000-0001-000000000015', '10000001-aaaa-bbbb-cccc-000000000001', 15, 'grade_2'),
('a0000000-0000-0000-0001-000000000016', '10000001-aaaa-bbbb-cccc-000000000001', 16, 'grade_2'),
('a0000000-0000-0000-0001-000000000017', '10000001-aaaa-bbbb-cccc-000000000001', 17, 'grade_2'),
('a0000000-0000-0000-0001-000000000018', '10000001-aaaa-bbbb-cccc-000000000001', 18, 'grade_2'),
('a0000000-0000-0000-0001-000000000019', '10000001-aaaa-bbbb-cccc-000000000001', 19, 'grade_2'),
('a0000000-0000-0000-0001-000000000020', '10000001-aaaa-bbbb-cccc-000000000001', 20, 'grade_2'),
('a0000000-0000-0000-0001-000000000021', '10000001-aaaa-bbbb-cccc-000000000001', 21, 'grade_2'),
('a0000000-0000-0000-0001-000000000022', '10000001-aaaa-bbbb-cccc-000000000001', 22, 'grade_2'),

-- Grade 3: Roll 23-30
('a0000000-0000-0000-0001-000000000023', '10000001-aaaa-bbbb-cccc-000000000001', 23, 'grade_3'),
('a0000000-0000-0000-0001-000000000024', '10000001-aaaa-bbbb-cccc-000000000001', 24, 'grade_3'),
('a0000000-0000-0000-0001-000000000025', '10000001-aaaa-bbbb-cccc-000000000001', 25, 'grade_3'),
('a0000000-0000-0000-0001-000000000026', '10000001-aaaa-bbbb-cccc-000000000001', 26, 'grade_3'),
('a0000000-0000-0000-0001-000000000027', '10000001-aaaa-bbbb-cccc-000000000001', 27, 'grade_3'),
('a0000000-0000-0000-0001-000000000028', '10000001-aaaa-bbbb-cccc-000000000001', 28, 'grade_3'),
('a0000000-0000-0000-0001-000000000029', '10000001-aaaa-bbbb-cccc-000000000001', 29, 'grade_3'),
('a0000000-0000-0000-0001-000000000030', '10000001-aaaa-bbbb-cccc-000000000001', 30, 'grade_3');


-- ============================================================================
-- INITIAL LAKSHYA POSITIONS (post-baseline)
-- Each child has a position per domain. Grouping is per-subject.
-- 
-- Realistic distribution:
--   NUMERACY: Some Grade 2 children still at Grade 1 level (Beginner),
--     most at Grade 2 (Progressor), a few ahead (Proficient).
--     A Grade 3 child at Grade 1 level joins the Beginner group.
--   LITERACY: Different distribution — a child who is Progressor in
--     numeracy might be Beginner in literacy (different strengths).
-- ============================================================================

INSERT INTO child_lakshya_positions (child_id, domain_id, current_competency_id, bpp_level, source, evidence_days, last_assessed) VALUES

-- ─── NUMERACY POSITIONS ───

-- Grade 1 children: spread across Balvatika → Grade 1 competencies
-- Beginners (still on Balvatika counting/number sense)
('a0000000-0000-0000-0001-000000000001', 'numeracy', 'N0.2.2', 'beginner', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000002', 'numeracy', 'N0.2.3', 'beginner', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000003', 'numeracy', 'N0.2.4', 'beginner', 'baseline_internal', 0, '2026-10-09'),
-- Progressors (working on Grade 1 number sense)
('a0000000-0000-0000-0001-000000000004', 'numeracy', 'N1.2.3', 'progressor', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000005', 'numeracy', 'N1.2.4', 'progressor', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000006', 'numeracy', 'N1.2.4', 'progressor', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000007', 'numeracy', 'N1.2.5', 'progressor', 'baseline_internal', 0, '2026-10-09'),
-- Proficients (already at Grade 1 operations)
('a0000000-0000-0000-0001-0000000000a8', 'numeracy', 'N1.3.1', 'proficient', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-0000000000a9', 'numeracy', 'N1.3.1', 'proficient', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000010', 'numeracy', 'N1.3.2', 'proficient', 'baseline_internal', 0, '2026-10-09'),

-- Grade 2 children: the main spread
-- Beginners (still on Grade 1 place value — THE critical gap)
('a0000000-0000-0000-0001-000000000011', 'numeracy', 'N1.2.4', 'beginner', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000012', 'numeracy', 'N1.3.1', 'beginner', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000013', 'numeracy', 'N1.2.4', 'beginner', 'baseline_internal', 0, '2026-10-09'),
-- Progressors (at Grade 2 operations — the target zone)
('a0000000-0000-0000-0001-000000000014', 'numeracy', 'N2.3.1', 'progressor', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000015', 'numeracy', 'N2.3.1', 'progressor', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000016', 'numeracy', 'N2.3.2', 'progressor', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000017', 'numeracy', 'N2.3.2', 'progressor', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000018', 'numeracy', 'N2.3.1', 'progressor', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000019', 'numeracy', 'N2.3.3', 'progressor', 'baseline_internal', 0, '2026-10-09'),
-- Proficients (ahead of grade level)
('a0000000-0000-0000-0001-000000000020', 'numeracy', 'N2.3.4', 'proficient', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000021', 'numeracy', 'N2.3.5', 'proficient', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000022', 'numeracy', 'N2.3.4', 'proficient', 'baseline_internal', 0, '2026-10-09'),

-- Grade 3 children: includes one child at Grade 1 level (joins Beginner group)
-- Beginners (far below grade level — this is the TaRL principle in action)
('a0000000-0000-0000-0001-000000000023', 'numeracy', 'N1.3.1', 'beginner', 'baseline_internal', 0, '2026-10-09'),
-- Progressors
('a0000000-0000-0000-0001-000000000024', 'numeracy', 'N2.3.4', 'progressor', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000025', 'numeracy', 'N3.3.1', 'progressor', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000026', 'numeracy', 'N3.3.1', 'progressor', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000027', 'numeracy', 'N3.3.2', 'progressor', 'baseline_internal', 0, '2026-10-09'),
-- Proficients
('a0000000-0000-0000-0001-000000000028', 'numeracy', 'N3.3.3', 'proficient', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000029', 'numeracy', 'N3.3.4', 'proficient', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000030', 'numeracy', 'N3.3.3', 'proficient', 'baseline_internal', 0, '2026-10-09'),


-- ─── R1 LITERACY POSITIONS ───
-- Different from numeracy! A child strong in math may struggle with reading.

-- Grade 1 children
('a0000000-0000-0000-0001-000000000001', 'r1_literacy', 'L0.3.1', 'beginner', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000002', 'r1_literacy', 'L0.2.3', 'beginner', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000003', 'r1_literacy', 'L1.3.1', 'progressor', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000004', 'r1_literacy', 'L0.3.2', 'beginner', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000005', 'r1_literacy', 'L1.3.2', 'progressor', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000006', 'r1_literacy', 'L1.3.2', 'progressor', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000007', 'r1_literacy', 'L1.3.4', 'proficient', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-0000000000a8', 'r1_literacy', 'L1.3.2', 'progressor', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-0000000000a9', 'r1_literacy', 'L0.3.1', 'beginner', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000010', 'r1_literacy', 'L1.4.1', 'proficient', 'baseline_internal', 0, '2026-10-09'),

-- Grade 2 children
('a0000000-0000-0000-0001-000000000011', 'r1_literacy', 'L1.3.3', 'beginner', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000012', 'r1_literacy', 'L1.3.2', 'beginner', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000013', 'r1_literacy', 'L1.4.1', 'beginner', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000014', 'r1_literacy', 'L2.3.1', 'progressor', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000015', 'r1_literacy', 'L2.4.1', 'progressor', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000016', 'r1_literacy', 'L2.5.1', 'progressor', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000017', 'r1_literacy', 'L2.3.1', 'progressor', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000018', 'r1_literacy', 'L2.5.1', 'progressor', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000019', 'r1_literacy', 'L2.6.1', 'proficient', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000020', 'r1_literacy', 'L2.6.2', 'proficient', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000021', 'r1_literacy', 'L2.5.1', 'progressor', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000022', 'r1_literacy', 'L2.6.1', 'proficient', 'baseline_internal', 0, '2026-10-09'),

-- Grade 3 children
('a0000000-0000-0000-0001-000000000023', 'r1_literacy', 'L1.5.1', 'beginner', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000024', 'r1_literacy', 'L2.5.1', 'beginner', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000025', 'r1_literacy', 'L3.5.1', 'progressor', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000026', 'r1_literacy', 'L3.3.1', 'progressor', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000027', 'r1_literacy', 'L3.5.1', 'progressor', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000028', 'r1_literacy', 'L3.6.1', 'proficient', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000029', 'r1_literacy', 'L3.6.1', 'proficient', 'baseline_internal', 0, '2026-10-09'),
('a0000000-0000-0000-0001-000000000030', 'r1_literacy', 'L3.5.2', 'proficient', 'baseline_internal', 0, '2026-10-09');


-- ============================================================================
-- INITIAL TEACHING GROUPS (derived from positions above)
-- These are the 3 groups per domain that the rotation schedule uses.
-- ============================================================================

-- NUMERACY GROUPS (when teacher selects a Grade 2 competency like N2.3.2)
INSERT INTO teaching_groups (teacher_id, domain_id, group_label, target_competency_id, child_ids, child_count, priority_rank, effective_from) VALUES

('10000001-aaaa-bbbb-cccc-000000000001', 'numeracy', 'beginner', 'N2.3.1',
 ARRAY['a0000000-0000-0000-0001-000000000001','a0000000-0000-0000-0001-000000000002','a0000000-0000-0000-0001-000000000003',
       'a0000000-0000-0000-0001-000000000011','a0000000-0000-0000-0001-000000000012','a0000000-0000-0000-0001-000000000013',
       'a0000000-0000-0000-0001-000000000023']::uuid[],
 7, 1, '2026-10-10'),

('10000001-aaaa-bbbb-cccc-000000000001', 'numeracy', 'progressor', 'N2.3.2',
 ARRAY['a0000000-0000-0000-0001-000000000004','a0000000-0000-0000-0001-000000000005','a0000000-0000-0000-0001-000000000006',
       'a0000000-0000-0000-0001-000000000007','a0000000-0000-0000-0001-000000000014','a0000000-0000-0000-0001-000000000015',
       'a0000000-0000-0000-0001-000000000016','a0000000-0000-0000-0001-000000000017','a0000000-0000-0000-0001-000000000018',
       'a0000000-0000-0000-0001-000000000019','a0000000-0000-0000-0001-000000000024','a0000000-0000-0000-0001-000000000025',
       'a0000000-0000-0000-0001-000000000026','a0000000-0000-0000-0001-000000000027']::uuid[],
 14, 2, '2026-10-10'),

('10000001-aaaa-bbbb-cccc-000000000001', 'numeracy', 'proficient', 'N2.3.5',
 ARRAY['a0000000-0000-0000-0001-0000000000a8','a0000000-0000-0000-0001-0000000000a9','a0000000-0000-0000-0001-000000000010',
       'a0000000-0000-0000-0001-000000000020','a0000000-0000-0000-0001-000000000021','a0000000-0000-0000-0001-000000000022',
       'a0000000-0000-0000-0001-000000000028','a0000000-0000-0000-0001-000000000029','a0000000-0000-0000-0001-000000000030']::uuid[],
 9, 3, '2026-10-10');
