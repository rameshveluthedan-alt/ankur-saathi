-- ============================================================================
-- ANKUR SAATHI — Layer 1 KB: Numeracy Competency Tree Seed Data
-- Part 1: Domain, Subdomains, Competencies (with A/PA/NA criteria)
-- ============================================================================
-- Coding scheme: N{grade}.{subdomain}.{sequence}
--   Grade: 0=Balvatika, 1=Grade 1, 2=Grade 2, 3=Grade 3
--   Subdomain: 1=pre_number, 2=number_sense, 3=operations,
--              4=measurement, 5=geometry, 6=data_handling
-- ============================================================================

-- ========================
-- DOMAIN
-- ========================
INSERT INTO domains (id, name_en, name_hi, sort_order) VALUES
('numeracy', 'Numeracy', 'गणित', 1);

-- ========================
-- SUBDOMAINS
-- ========================
INSERT INTO subdomains (id, domain_id, name_en, name_hi, description, sort_order) VALUES
('num_pre_number',   'numeracy', 'Pre-number Concepts',   'पूर्व-संख्या अवधारणाएँ',  'Sorting, classification, seriation, patterns — foundational logical thinking before formal number work', 1),
('num_number_sense', 'numeracy', 'Number Sense',          'संख्या बोध',              'Counting, numeral recognition/writing, place value, comparison, ordering', 2),
('num_operations',   'numeracy', 'Operations',            'संक्रियाएँ',               'Addition, subtraction, multiplication, division — procedural and conceptual', 3),
('num_measurement',  'numeracy', 'Measurement',           'मापन',                    'Length, weight, capacity, time, money — connecting numbers to the physical world', 4),
('num_geometry',     'numeracy', 'Geometry',              'ज्यामिति',                 'Shapes, spatial reasoning, symmetry, angles, perimeter', 5),
('num_data_handling','numeracy', 'Data Handling',         'आँकड़ों का प्रबंधन',       'Pictographs, tables, bar graphs — reading and creating data representations', 6);


-- ============================================================================
-- COMPETENCIES — BALVATIKA (Pre-primary / Kindergarten)
-- Focus: pre-number concepts, early counting, numeral recognition
-- ============================================================================

INSERT INTO competencies (id, subdomain_id, name_en, name_hi, grade_level, sort_order, assessment_modality, apna_criteria, number_range, problem_types) VALUES

-- === Pre-number Concepts ===
('N0.1.1', 'num_pre_number', 
 'Sorts objects by one attribute (colour, shape, size)',
 'वस्तुओं को एक गुण (रंग, आकार, आकृति) के आधार पर वर्गीकृत करता है',
 'balvatika', 1, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Sorts 10+ objects correctly by one attribute without prompting, can explain sorting rule"},
   "partially_achieved": {"description": "Sorts with 1-2 errors or needs prompting to identify attribute"},
   "not_achieved": {"description": "Cannot sort by any attribute, or groups randomly"}
 }'::jsonb, NULL, NULL),

('N0.1.2', 'num_pre_number',
 'Identifies and extends simple patterns (AB, ABB)',
 'सरल पैटर्न (AB, ABB) को पहचानता और आगे बढ़ाता है',
 'balvatika', 2, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Extends AB and ABB patterns correctly for 3+ repetitions, can create own pattern"},
   "partially_achieved": {"description": "Extends AB pattern but struggles with ABB, or needs hints"},
   "not_achieved": {"description": "Cannot identify the repeating unit in AB pattern"}
 }'::jsonb, NULL, NULL),

('N0.1.3', 'num_pre_number',
 'Compares quantities (more/less/same) up to 5 objects',
 '5 तक वस्तुओं में मात्रा की तुलना (ज़्यादा/कम/बराबर) करता है',
 'balvatika', 3, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Correctly compares all pairs up to 5 objects, uses vocabulary more/less/same"},
   "partially_achieved": {"description": "Compares correctly when difference is ≥2, struggles with close quantities"},
   "not_achieved": {"description": "Cannot reliably identify more vs less for groups of 3-5"}
 }'::jsonb, '{"min": 1, "max": 5}'::jsonb, NULL),

-- === Number Sense ===
('N0.2.1', 'num_number_sense',
 'Recites number names 1 to 20 in sequence',
 '1 से 20 तक गिनती बोलता है',
 'balvatika', 1, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Recites 1-20 fluently without errors or pauses >3 seconds"},
   "partially_achieved": {"description": "Recites 1-20 with 1-2 skips/errors or long pauses, self-corrects"},
   "not_achieved": {"description": "Cannot recite beyond 10, or has frequent errors/skips"}
 }'::jsonb, '{"min": 1, "max": 20}'::jsonb, NULL),

('N0.2.2', 'num_number_sense',
 'Counts up to 10 objects with one-to-one correspondence',
 '10 तक वस्तुओं की एक-एक करके गिनती करता है',
 'balvatika', 2, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Counts 10 objects correctly with 1:1 tagging, answers how many correctly"},
   "partially_achieved": {"description": "Counts up to 10 but makes tagging errors or loses track beyond 7"},
   "not_achieved": {"description": "Cannot count beyond 5 with 1:1 correspondence, or skips/double-counts"}
 }'::jsonb, '{"min": 1, "max": 10}'::jsonb, NULL),

('N0.2.3', 'num_number_sense',
 'Recognises numerals 1 to 9',
 'अंक 1 से 9 को पहचानता है',
 'balvatika', 3, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Identifies all 9 numerals correctly when shown in random order"},
   "partially_achieved": {"description": "Identifies 6-8 numerals, confuses visually similar ones (6/9, 2/5)"},
   "not_achieved": {"description": "Identifies fewer than 6 numerals correctly"}
 }'::jsonb, '{"min": 1, "max": 9}'::jsonb, NULL),

('N0.2.4', 'num_number_sense',
 'Writes numerals 1 to 9',
 'अंक 1 से 9 लिखता है',
 'balvatika', 4, 'written',
 '{
   "type": "written_production",
   "achieved": {"description": "Writes all 9 numerals legibly, correct formation, no reversals"},
   "partially_achieved": {"description": "Writes most numerals but 1-2 persistent reversals or illegible forms"},
   "not_achieved": {"description": "Cannot write more than 5 numerals legibly, frequent reversals"}
 }'::jsonb, '{"min": 1, "max": 9}'::jsonb, ARRAY['numeral_writing']),

-- === Geometry (Balvatika) ===
('N0.5.1', 'num_geometry',
 'Identifies basic 2D shapes (circle, square, triangle, rectangle)',
 'मूल आकृतियों (वृत्त, वर्ग, त्रिभुज, आयत) को पहचानता है',
 'balvatika', 1, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Names all 4 shapes correctly, identifies them in real-world objects"},
   "partially_achieved": {"description": "Names 2-3 shapes, confuses square/rectangle"},
   "not_achieved": {"description": "Can name only 1 or no shapes reliably"}
 }'::jsonb, NULL, NULL),


-- ============================================================================
-- COMPETENCIES — GRADE 1
-- Focus: counting to 100, 2-digit numerals, place value, single-digit operations
-- ============================================================================

-- === Pre-number / Patterns (Grade 1) ===
('N1.1.1', 'num_pre_number',
 'Extends and creates growing patterns (AB, ABC, ABB, AAB)',
 'बढ़ते पैटर्न (AB, ABC, ABB, AAB) को आगे बढ़ाता और बनाता है',
 'grade_1', 1, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.80, "sessions_required": 2, "description": "Correctly extends 4/5 pattern types and creates at least 1 original pattern"},
   "partially_achieved": {"accuracy_range": [0.50, 0.80], "description": "Extends AB/ABB but struggles with ABC/AAB"},
   "not_achieved": {"max_accuracy": 0.50, "description": "Cannot extend even AB pattern reliably"}
 }'::jsonb, NULL, ARRAY['pattern_extension', 'pattern_creation']),

-- === Number Sense (Grade 1) ===
('N1.2.1', 'num_number_sense',
 'Recites number names 1 to 100',
 '1 से 100 तक गिनती बोलता है',
 'grade_1', 1, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Recites 1-100 fluently, crosses decade boundaries (29→30, 39→40) without error"},
   "partially_achieved": {"description": "Recites to 100 but stumbles at decade boundaries, self-corrects"},
   "not_achieved": {"description": "Cannot recite beyond 50, or has frequent errors at decade boundaries"}
 }'::jsonb, '{"min": 1, "max": 100}'::jsonb, NULL),

('N1.2.2', 'num_number_sense',
 'Counts up to 20 objects with one-to-one correspondence',
 '20 तक वस्तुओं की एक-एक करके गिनती करता है',
 'grade_1', 2, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Counts 20 objects correctly with 1:1 tagging, answers cardinality question correctly"},
   "partially_achieved": {"description": "Counts to 20 but tagging errors beyond 15, or cannot answer how many"},
   "not_achieved": {"description": "Cannot count beyond 10 objects with 1:1 correspondence"}
 }'::jsonb, '{"min": 1, "max": 20}'::jsonb, NULL),

('N1.2.3', 'num_number_sense',
 'Reads and writes numerals 1 to 99',
 '1 से 99 तक अंक पढ़ता और लिखता है',
 'grade_1', 3, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.85, "sessions_required": 2, "description": "Reads and writes 2-digit numerals correctly, including teens (11-19)"},
   "partially_achieved": {"accuracy_range": [0.50, 0.85], "description": "Reads/writes most but reverses digits or confuses teens"},
   "not_achieved": {"max_accuracy": 0.50, "description": "Cannot write most 2-digit numerals, frequent reversals"}
 }'::jsonb, '{"min": 1, "max": 99}'::jsonb, ARRAY['numeral_reading', 'numeral_writing']),

('N1.2.4', 'num_number_sense',
 'Understands place value: tens and ones up to 99',
 'स्थानीय मान समझता है: 99 तक दहाई और इकाई',
 'grade_1', 4, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.80, "sessions_required": 2, "description": "Decomposes 2-digit numbers into tens and ones, represents with bundling sticks/blocks"},
   "partially_achieved": {"accuracy_range": [0.40, 0.80], "description": "Decomposes some numbers but reverses tens/ones for some"},
   "not_achieved": {"max_accuracy": 0.40, "description": "Cannot decompose numbers, treats 23 as 2 and 3 not 20 and 3"}
 }'::jsonb, '{"min": 10, "max": 99}'::jsonb, ARRAY['place_value_decomposition', 'place_value_representation']),

('N1.2.5', 'num_number_sense',
 'Compares two 2-digit numbers using >, <, =',
 'दो अंकों की संख्याओं की तुलना >, <, = से करता है',
 'grade_1', 5, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.80, "sessions_required": 2, "description": "Correctly uses >, <, = for all 2-digit comparisons including same-tens pairs"},
   "partially_achieved": {"accuracy_range": [0.50, 0.80], "description": "Compares correctly when tens differ, struggles with same-tens (e.g., 34 vs 38)"},
   "not_achieved": {"max_accuracy": 0.50, "description": "Cannot reliably compare, or confuses > and <"}
 }'::jsonb, '{"min": 10, "max": 99}'::jsonb, ARRAY['number_comparison']),

('N1.2.6', 'num_number_sense',
 'Orders numbers up to 99 (ascending and descending)',
 '99 तक संख्याओं को क्रम (बढ़ते/घटते) में लगाता है',
 'grade_1', 6, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.80, "sessions_required": 2, "description": "Orders 5+ numbers correctly in both ascending and descending"},
   "partially_achieved": {"accuracy_range": [0.50, 0.80], "description": "Orders ascending correctly but struggles with descending, or errors with close numbers"},
   "not_achieved": {"max_accuracy": 0.50, "description": "Cannot order more than 3 numbers correctly"}
 }'::jsonb, '{"min": 1, "max": 99}'::jsonb, ARRAY['number_ordering']),

-- === Operations (Grade 1) ===
('N1.3.1', 'num_operations',
 'Adds two single-digit numbers (sum ≤ 18)',
 'एक अंक की दो संख्याओं का जोड़ (योग ≤ 18)',
 'grade_1', 1, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.85, "sessions_required": 2, "no_persistent_misconception": true},
   "partially_achieved": {"accuracy_range": [0.50, 0.85], "or_has_misconception": true},
   "not_achieved": {"max_accuracy": 0.50, "or_cannot_attempt": true}
 }'::jsonb, '{"min": 1, "max": 9, "sum_max": 18}'::jsonb, ARRAY['single_digit_addition']),

('N1.3.2', 'num_operations',
 'Subtracts single-digit numbers (minuend ≤ 18)',
 'एक अंक की संख्याओं का घटाना (18 तक)',
 'grade_1', 2, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.85, "sessions_required": 2, "no_persistent_misconception": true},
   "partially_achieved": {"accuracy_range": [0.50, 0.85], "or_has_misconception": true},
   "not_achieved": {"max_accuracy": 0.50, "or_cannot_attempt": true}
 }'::jsonb, '{"min": 1, "max": 18}'::jsonb, ARRAY['single_digit_subtraction']),

('N1.3.3', 'num_operations',
 'Solves simple addition/subtraction word problems (single-digit)',
 'जोड़ और घटाव के सरल शाब्दिक प्रश्न हल करता है (एक अंक)',
 'grade_1', 3, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.75, "sessions_required": 2, "description": "Identifies operation correctly and computes answer for 3/4 word problems"},
   "partially_achieved": {"accuracy_range": [0.40, 0.75], "description": "Sometimes identifies wrong operation, or computes correctly but picks wrong operation"},
   "not_achieved": {"max_accuracy": 0.40, "description": "Cannot identify whether to add or subtract from word problem context"}
 }'::jsonb, '{"min": 1, "max": 9}'::jsonb, ARRAY['word_problem_addition', 'word_problem_subtraction']),

-- === Measurement (Grade 1) ===
('N1.4.1', 'num_measurement',
 'Compares lengths/heights using direct comparison (longer/shorter/taller)',
 'लंबाई/ऊँचाई की सीधी तुलना करता है (लंबा/छोटा/ऊँचा)',
 'grade_1', 1, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Correctly compares lengths of 3+ pairs, uses correct vocabulary, aligns baselines"},
   "partially_achieved": {"description": "Compares correctly but does not align baselines, or inconsistent vocabulary"},
   "not_achieved": {"description": "Cannot reliably compare lengths even with direct visual comparison"}
 }'::jsonb, NULL, NULL),

('N1.4.2', 'num_measurement',
 'Sequences events by time (before/after, morning/afternoon/night)',
 'समय के अनुसार घटनाओं को क्रम में रखता है (पहले/बाद, सुबह/दोपहर/रात)',
 'grade_1', 2, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Correctly sequences 4+ daily events, uses before/after vocabulary consistently"},
   "partially_achieved": {"description": "Sequences 2-3 events but confuses afternoon/evening or close events"},
   "not_achieved": {"description": "Cannot sequence even morning/afternoon/night reliably"}
 }'::jsonb, NULL, NULL),

-- === Geometry (Grade 1) ===
('N1.5.1', 'num_geometry',
 'Describes properties of 2D shapes (sides, corners)',
 '2D आकृतियों के गुणों (भुजाएँ, कोने) का वर्णन करता है',
 'grade_1', 1, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Correctly states number of sides/corners for all 4 basic shapes, distinguishes square from rectangle"},
   "partially_achieved": {"description": "Counts sides/corners for triangle and square but confuses rectangle properties"},
   "not_achieved": {"description": "Cannot count sides or corners of basic shapes"}
 }'::jsonb, NULL, NULL),

('N1.5.2', 'num_geometry',
 'Identifies basic 3D shapes (sphere, cube, cylinder, cone)',
 'मूल 3D आकृतियों (गोला, घन, बेलन, शंकु) को पहचानता है',
 'grade_1', 2, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Names all 4 shapes, identifies them in real-world objects (ball=sphere, box=cube)"},
   "partially_achieved": {"description": "Names 2-3 shapes, confuses cylinder/cone"},
   "not_achieved": {"description": "Can name only 1 or no 3D shapes"}
 }'::jsonb, NULL, NULL),


-- ============================================================================
-- COMPETENCIES — GRADE 2
-- Focus: 3-digit numbers, 2-digit operations with regrouping, measurement
-- ============================================================================

-- === Number Sense (Grade 2) ===
('N2.2.1', 'num_number_sense',
 'Reads and writes 3-digit numbers (100–999)',
 '3 अंकों की संख्याएँ (100–999) पढ़ता और लिखता है',
 'grade_2', 1, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.85, "sessions_required": 2, "description": "Reads/writes all 3-digit numbers including those with 0 in tens/ones place"},
   "partially_achieved": {"accuracy_range": [0.50, 0.85], "description": "Reads/writes most but errors with 0 in middle (e.g., 305) or hundred-boundary"},
   "not_achieved": {"max_accuracy": 0.50, "description": "Cannot read or write most 3-digit numbers"}
 }'::jsonb, '{"min": 100, "max": 999}'::jsonb, ARRAY['numeral_reading_3digit', 'numeral_writing_3digit']),

('N2.2.2', 'num_number_sense',
 'Understands place value: hundreds, tens, and ones',
 'स्थानीय मान समझता है: सैकड़ा, दहाई, इकाई',
 'grade_2', 2, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.80, "sessions_required": 2, "description": "Decomposes 3-digit numbers correctly, including with zero in a place"},
   "partially_achieved": {"accuracy_range": [0.40, 0.80], "description": "Decomposes most but confused by zero in tens place or expanded form"},
   "not_achieved": {"max_accuracy": 0.40, "description": "Cannot identify hundreds/tens/ones digits or their values"}
 }'::jsonb, '{"min": 100, "max": 999}'::jsonb, ARRAY['place_value_3digit', 'expanded_form']),

('N2.2.3', 'num_number_sense',
 'Compares 3-digit numbers using >, <, =',
 '3 अंकों की संख्याओं की तुलना >, <, = से करता है',
 'grade_2', 3, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.80, "sessions_required": 2},
   "partially_achieved": {"accuracy_range": [0.50, 0.80]},
   "not_achieved": {"max_accuracy": 0.50}
 }'::jsonb, '{"min": 100, "max": 999}'::jsonb, ARRAY['number_comparison_3digit']),

('N2.2.4', 'num_number_sense',
 'Skip counts by 2s, 5s, and 10s',
 '2, 5, 10 के गुणज में गिनती करता है',
 'grade_2', 4, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Skip counts by 2s, 5s, and 10s to at least 100 without error"},
   "partially_achieved": {"description": "Skip counts by 2s and 10s but errors with 5s, or cannot go beyond 50"},
   "not_achieved": {"description": "Cannot skip count by any value beyond first 5 terms"}
 }'::jsonb, '{"min": 1, "max": 100}'::jsonb, NULL),

-- === Operations (Grade 2) — the critical competencies for differentiation ===
('N2.3.1', 'num_operations',
 'Adds two 2-digit numbers without regrouping',
 'बिना हासिल के दो अंकों की संख्याओं का जोड़',
 'grade_2', 1, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.85, "sessions_required": 2, "no_persistent_misconception": true},
   "partially_achieved": {"accuracy_range": [0.50, 0.85], "or_has_misconception": true},
   "not_achieved": {"max_accuracy": 0.50, "or_cannot_attempt": true}
 }'::jsonb, '{"min": 10, "max": 99, "ones_sum_max": 9}'::jsonb, ARRAY['addition_2digit_no_carry']),

('N2.3.2', 'num_operations',
 'Adds two 2-digit numbers with regrouping (carry-over)',
 'हासिल के साथ दो अंकों की संख्याओं का जोड़',
 'grade_2', 2, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.80, "sessions_required": 2, "no_persistent_misconception": true},
   "partially_achieved": {"accuracy_range": [0.40, 0.80], "or_has_misconception": true},
   "not_achieved": {"max_accuracy": 0.40, "or_cannot_attempt": true}
 }'::jsonb, '{"min": 10, "max": 99}'::jsonb, ARRAY['addition_2digit_with_carry']),

('N2.3.3', 'num_operations',
 'Subtracts 2-digit numbers without borrowing',
 'बिना उधार के दो अंकों की संख्याओं का घटाव',
 'grade_2', 3, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.85, "sessions_required": 2, "no_persistent_misconception": true},
   "partially_achieved": {"accuracy_range": [0.50, 0.85], "or_has_misconception": true},
   "not_achieved": {"max_accuracy": 0.50, "or_cannot_attempt": true}
 }'::jsonb, '{"min": 10, "max": 99}'::jsonb, ARRAY['subtraction_2digit_no_borrow']),

('N2.3.4', 'num_operations',
 'Subtracts 2-digit numbers with borrowing (regrouping)',
 'उधार (पुनर्समूहन) के साथ दो अंकों की संख्याओं का घटाव',
 'grade_2', 4, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.80, "sessions_required": 2, "no_persistent_misconception": true},
   "partially_achieved": {"accuracy_range": [0.40, 0.80], "or_has_misconception": true},
   "not_achieved": {"max_accuracy": 0.40, "or_cannot_attempt": true}
 }'::jsonb, '{"min": 10, "max": 99}'::jsonb, ARRAY['subtraction_2digit_with_borrow']),

('N2.3.5', 'num_operations',
 'Solves addition and subtraction word problems (2-digit)',
 'जोड़ और घटाव के शाब्दिक प्रश्न हल करता है (दो अंक)',
 'grade_2', 5, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.75, "sessions_required": 2, "description": "Correctly identifies operation and computes for ≥3/4 problems"},
   "partially_achieved": {"accuracy_range": [0.40, 0.75], "description": "Computation correct but operation selection errors, or vice versa"},
   "not_achieved": {"max_accuracy": 0.40, "description": "Cannot identify operation from context or compute 2-digit operations"}
 }'::jsonb, '{"min": 10, "max": 99}'::jsonb, ARRAY['word_problem_2digit']),

('N2.3.6', 'num_operations',
 'Understands multiplication as repeated addition',
 'गुणा को बार-बार जोड़ के रूप में समझता है',
 'grade_2', 6, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.80, "sessions_required": 2, "description": "Converts between 3×4 and 4+4+4, solves both representations"},
   "partially_achieved": {"accuracy_range": [0.40, 0.80], "description": "Understands concept but errors in computation of repeated addition"},
   "not_achieved": {"max_accuracy": 0.40, "description": "Cannot connect multiplication notation to repeated addition"}
 }'::jsonb, '{"min": 1, "max": 10, "product_max": 50}'::jsonb, ARRAY['multiplication_as_repeated_addition']),

-- === Measurement (Grade 2) ===
('N2.4.1', 'num_measurement',
 'Measures length using non-standard units (handspans, footsteps)',
 'अमानक इकाइयों (बित्ता, कदम) से लंबाई मापता है',
 'grade_2', 1, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Measures consistently with chosen unit, no gaps between units, states measurement with unit name"},
   "partially_achieved": {"description": "Measures but leaves gaps between units or does not state unit"},
   "not_achieved": {"description": "Cannot measure — places units randomly or does not understand the concept"}
 }'::jsonb, NULL, NULL),

('N2.4.2', 'num_measurement',
 'Reads a calendar (days of week, months, dates)',
 'कैलेंडर पढ़ता है (सप्ताह के दिन, महीने, तारीख)',
 'grade_2', 2, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Names all 7 days and 12 months in order, reads today''s date from calendar"},
   "partially_achieved": {"description": "Names days but not months in order, or cannot read a specific date"},
   "not_achieved": {"description": "Cannot name days of week in order"}
 }'::jsonb, NULL, NULL),

('N2.4.3', 'num_measurement',
 'Identifies Indian coins and currency notes, makes simple amounts',
 'भारतीय सिक्के और नोट पहचानता है, सरल राशि बनाता है',
 'grade_2', 3, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Identifies all common denominations, makes given amount using different combinations"},
   "partially_achieved": {"description": "Identifies denominations but cannot make amounts with mixed coins/notes"},
   "not_achieved": {"description": "Cannot identify denominations beyond ₹1 and ₹10"}
 }'::jsonb, NULL, NULL),

-- === Geometry (Grade 2) ===
('N2.5.1', 'num_geometry',
 'Identifies lines of symmetry in simple shapes',
 'सरल आकृतियों में सममिति रेखा पहचानता है',
 'grade_2', 1, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.75, "sessions_required": 1, "description": "Draws line of symmetry correctly for rectangle, square, circle, and simple figures"},
   "partially_achieved": {"accuracy_range": [0.40, 0.75]},
   "not_achieved": {"max_accuracy": 0.40}
 }'::jsonb, NULL, ARRAY['symmetry_identification']),

-- === Data Handling (Grade 2) ===
('N2.6.1', 'num_data_handling',
 'Reads and interprets simple pictographs',
 'सरल चित्र-आलेख पढ़ता और समझता है',
 'grade_2', 1, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.80, "sessions_required": 1, "description": "Reads values from pictograph, answers most/least/how many questions correctly"},
   "partially_achieved": {"accuracy_range": [0.40, 0.80], "description": "Reads individual values but cannot compare or answer inference questions"},
   "not_achieved": {"max_accuracy": 0.40, "description": "Cannot read values from pictograph"}
 }'::jsonb, NULL, ARRAY['pictograph_reading']),


-- ============================================================================
-- COMPETENCIES — GRADE 3
-- Focus: 4-digit numbers, 3-digit operations, multiplication/division,
--        standard measurement, basic data handling
-- ============================================================================

-- === Number Sense (Grade 3) ===
('N3.2.1', 'num_number_sense',
 'Reads and writes numbers up to 9,999',
 '9,999 तक संख्याएँ पढ़ता और लिखता है',
 'grade_3', 1, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.85, "sessions_required": 2},
   "partially_achieved": {"accuracy_range": [0.50, 0.85]},
   "not_achieved": {"max_accuracy": 0.50}
 }'::jsonb, '{"min": 1000, "max": 9999}'::jsonb, ARRAY['numeral_reading_4digit', 'numeral_writing_4digit']),

('N3.2.2', 'num_number_sense',
 'Understands place value up to thousands (Th, H, T, O)',
 'हज़ार तक स्थानीय मान समझता है (ह, स, द, इ)',
 'grade_3', 2, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.80, "sessions_required": 2, "description": "Decomposes 4-digit numbers, writes expanded form, identifies value of each digit"},
   "partially_achieved": {"accuracy_range": [0.40, 0.80]},
   "not_achieved": {"max_accuracy": 0.40}
 }'::jsonb, '{"min": 1000, "max": 9999}'::jsonb, ARRAY['place_value_4digit', 'expanded_form_4digit']),

('N3.2.3', 'num_number_sense',
 'Compares and orders 4-digit numbers',
 '4 अंकों की संख्याओं की तुलना और क्रम',
 'grade_3', 3, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.80, "sessions_required": 2},
   "partially_achieved": {"accuracy_range": [0.50, 0.80]},
   "not_achieved": {"max_accuracy": 0.50}
 }'::jsonb, '{"min": 1000, "max": 9999}'::jsonb, ARRAY['number_comparison_4digit', 'number_ordering_4digit']),

-- === Operations (Grade 3) ===
('N3.3.1', 'num_operations',
 'Adds 3-digit numbers with regrouping',
 'हासिल के साथ 3 अंकों की संख्याओं का जोड़',
 'grade_3', 1, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.80, "sessions_required": 2, "no_persistent_misconception": true},
   "partially_achieved": {"accuracy_range": [0.40, 0.80], "or_has_misconception": true},
   "not_achieved": {"max_accuracy": 0.40, "or_cannot_attempt": true}
 }'::jsonb, '{"min": 100, "max": 999}'::jsonb, ARRAY['addition_3digit_with_carry']),

('N3.3.2', 'num_operations',
 'Subtracts 3-digit numbers with borrowing',
 'उधार के साथ 3 अंकों की संख्याओं का घटाव',
 'grade_3', 2, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.80, "sessions_required": 2, "no_persistent_misconception": true},
   "partially_achieved": {"accuracy_range": [0.40, 0.80], "or_has_misconception": true},
   "not_achieved": {"max_accuracy": 0.40, "or_cannot_attempt": true}
 }'::jsonb, '{"min": 100, "max": 999}'::jsonb, ARRAY['subtraction_3digit_with_borrow']),

('N3.3.3', 'num_operations',
 'Recalls multiplication tables 2 to 10',
 'गुणन सारणी 2 से 10 याद करता है',
 'grade_3', 3, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Recalls all facts for tables 2-10 within 3 seconds per fact, no consistent errors"},
   "partially_achieved": {"description": "Recalls tables 2, 5, 10 fluently but slow/errors on 3, 4, 6, 7, 8, 9"},
   "not_achieved": {"description": "Cannot recall most multiplication facts, relies on counting/repeated addition"}
 }'::jsonb, '{"min": 2, "max": 10}'::jsonb, ARRAY['multiplication_facts']),

('N3.3.4', 'num_operations',
 'Multiplies a 2-digit number by a 1-digit number',
 '2 अंकों की संख्या को 1 अंक से गुणा करता है',
 'grade_3', 4, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.80, "sessions_required": 2, "no_persistent_misconception": true},
   "partially_achieved": {"accuracy_range": [0.40, 0.80], "or_has_misconception": true},
   "not_achieved": {"max_accuracy": 0.40, "or_cannot_attempt": true}
 }'::jsonb, '{"multiplicand_min": 10, "multiplicand_max": 99, "multiplier_min": 2, "multiplier_max": 9}'::jsonb, ARRAY['multiplication_2by1']),

('N3.3.5', 'num_operations',
 'Divides using equal sharing and grouping (dividend ≤ 100)',
 'बराबर बँटवारे और समूहन से भाग करता है (भाज्य ≤ 100)',
 'grade_3', 5, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.75, "sessions_required": 2, "description": "Divides correctly and can explain as sharing or grouping, handles remainders"},
   "partially_achieved": {"accuracy_range": [0.40, 0.75], "description": "Divides without remainder but cannot handle remainders or explain concept"},
   "not_achieved": {"max_accuracy": 0.40, "description": "Cannot perform division or confuses with subtraction"}
 }'::jsonb, '{"dividend_max": 100, "divisor_min": 2, "divisor_max": 10}'::jsonb, ARRAY['division_sharing', 'division_grouping']),

('N3.3.6', 'num_operations',
 'Solves multi-step word problems (addition, subtraction, multiplication)',
 'बहु-चरणीय शाब्दिक प्रश्न हल करता है (जोड़, घटाव, गुणा)',
 'grade_3', 6, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.70, "sessions_required": 2, "description": "Identifies both operations, sequences steps correctly, computes accurately"},
   "partially_achieved": {"accuracy_range": [0.35, 0.70], "description": "Identifies first step but not second, or correct operations but computation errors"},
   "not_achieved": {"max_accuracy": 0.35, "description": "Cannot break down multi-step problem, or attempts single operation only"}
 }'::jsonb, '{"min": 1, "max": 999}'::jsonb, ARRAY['multi_step_word_problem']),

-- === Measurement (Grade 3) ===
('N3.4.1', 'num_measurement',
 'Measures length in standard units (cm, m) and converts between them',
 'मानक इकाइयों (सेमी, मी) में लंबाई मापता है और रूपांतरण करता है',
 'grade_3', 1, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.80, "sessions_required": 1, "description": "Reads ruler correctly, measures to nearest cm, converts m↔cm"},
   "partially_achieved": {"accuracy_range": [0.50, 0.80], "description": "Reads ruler but starting-point errors, or cannot convert"},
   "not_achieved": {"max_accuracy": 0.50, "description": "Cannot use a ruler to measure length"}
 }'::jsonb, NULL, ARRAY['length_measurement', 'unit_conversion_length']),

('N3.4.2', 'num_measurement',
 'Reads time on a clock (hours and half-hours, introduces minutes)',
 'घड़ी पर समय पढ़ता है (घंटे, आधे घंटे, मिनट)',
 'grade_3', 2, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Reads hours, half-hours, and quarter-hours correctly on analog clock"},
   "partially_achieved": {"description": "Reads hours correctly but confuses minute hand position for half/quarter"},
   "not_achieved": {"description": "Cannot distinguish hour and minute hands or read hours"}
 }'::jsonb, NULL, NULL),

('N3.4.3', 'num_measurement',
 'Measures weight using standard units (g, kg)',
 'मानक इकाइयों (ग्राम, किग्रा) में भार मापता है',
 'grade_3', 3, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Uses balance correctly, reads scale, converts kg↔g for simple values"},
   "partially_achieved": {"description": "Uses balance but cannot read scale precisely or convert units"},
   "not_achieved": {"description": "Cannot use a balance or understand the concept of standard weight units"}
 }'::jsonb, NULL, NULL),

-- === Geometry (Grade 3) ===
('N3.5.1', 'num_geometry',
 'Identifies angles as right, acute, or obtuse',
 'कोणों को समकोण, न्यूनकोण, अधिककोण पहचानता है',
 'grade_3', 1, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.80, "sessions_required": 1},
   "partially_achieved": {"accuracy_range": [0.50, 0.80]},
   "not_achieved": {"max_accuracy": 0.50}
 }'::jsonb, NULL, ARRAY['angle_classification']),

('N3.5.2', 'num_geometry',
 'Calculates perimeter of simple shapes (square, rectangle, triangle)',
 'सरल आकृतियों (वर्ग, आयत, त्रिभुज) का परिमाप ज्ञात करता है',
 'grade_3', 2, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.80, "sessions_required": 2, "description": "Calculates perimeter using formula, applies to word problems"},
   "partially_achieved": {"accuracy_range": [0.40, 0.80], "description": "Knows formula but computation errors, or confuses perimeter with area concept"},
   "not_achieved": {"max_accuracy": 0.40, "description": "Does not understand perimeter as sum of all sides"}
 }'::jsonb, NULL, ARRAY['perimeter_calculation']),

-- === Data Handling (Grade 3) ===
('N3.6.1', 'num_data_handling',
 'Reads and interprets bar graphs',
 'दण्ड आलेख (बार ग्राफ) पढ़ता और समझता है',
 'grade_3', 1, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.80, "sessions_required": 1, "description": "Reads values, compares bars, answers inference questions (most/least/difference)"},
   "partially_achieved": {"accuracy_range": [0.40, 0.80], "description": "Reads individual bar values but cannot compare or find differences"},
   "not_achieved": {"max_accuracy": 0.40, "description": "Cannot read values from bar graph"}
 }'::jsonb, NULL, ARRAY['bar_graph_reading']),

('N3.6.2', 'num_data_handling',
 'Collects data and organises into simple tables',
 'आँकड़े एकत्र करता है और सारणी में व्यवस्थित करता है',
 'grade_3', 2, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.75, "sessions_required": 1, "description": "Collects data using tally marks, organises into table with correct totals"},
   "partially_achieved": {"accuracy_range": [0.40, 0.75], "description": "Uses tally marks but errors in counting or table organisation"},
   "not_achieved": {"max_accuracy": 0.40, "description": "Cannot use tally marks or organise data into a table"}
 }'::jsonb, NULL, ARRAY['data_collection', 'tally_marks']);
