-- ============================================================================
-- NUMERACY WEEKLY PLAN — Grades 1, 2, 3
-- Plan ID: a0000000-0000-0000-0000-000000000001
-- ============================================================================

INSERT INTO curriculum_weeks (plan_id, grade_level, domain_id, week_number, topic_title_en, topic_title_hi, competency_ids, notes, sort_order) VALUES

-- ============================================================================
-- GRADE 1 NUMERACY — 40 weeks
-- Target by year-end: numbers to 99, place value, single-digit operations
-- ============================================================================

-- Term 1: Foundation (Weeks 1-20)
('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 1,
 'Baseline assessment', 'आधारभूत मूल्यांकन',
 ARRAY['N0.1.1','N0.1.3','N0.2.1','N0.2.2','N0.2.3','N0.2.4'],
 'Full diagnostic across Balvatika competencies to place children. Use baseline assessment tool.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 2,
 'Baseline assessment (continued)', 'आधारभूत मूल्यांकन (जारी)',
 ARRAY['N0.5.1','N1.2.1','N1.2.2','N1.2.3'],
 'Complete baseline for Grade 1 competencies. Cluster children into B/P/P groups.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 3,
 'Pre-number: Sorting and classification', 'पूर्व-संख्या: वर्गीकरण',
 ARRAY['N0.1.1'],
 'Revision/remediation for Beginners. Proficients start patterns.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 4,
 'Pre-number: Patterns and comparison', 'पूर्व-संख्या: पैटर्न और तुलना',
 ARRAY['N0.1.2','N0.1.3'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 5,
 'Counting: Rote counting 1-50', 'गिनती: 1-50 तक मौखिक गिनती',
 ARRAY['N0.2.1','N1.2.1'],
 'Focus on decade boundaries (19→20, 29→30). Beginners work on 1-20.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 6,
 'Counting: Rote counting 1-100 and 1:1 counting to 10', 'गिनती: 1-100 और 10 तक वस्तु गिनती',
 ARRAY['N1.2.1','N0.2.2'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 7,
 'Counting: 1:1 counting to 20 objects', 'गिनती: 20 तक वस्तु गिनती',
 ARRAY['N1.2.2'],
 'Cardinality emphasis: the last number IS the total.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 8,
 'Numeral recognition: 1-9 and writing', 'अंक पहचान: 1-9 पहचानना और लिखना',
 ARRAY['N0.2.3','N0.2.4'],
 'Beginners still here; Proficients move to 2-digit reading.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 9,
 'Numeral reading/writing: teens (11-19)', 'अंक पठन/लेखन: किशोर संख्याएँ (11-19)',
 ARRAY['N1.2.3'],
 'Hindi number names are irregular for teens — explicit teaching needed.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 10,
 'Numeral reading/writing: 20-99', 'अंक पठन/लेखन: 20-99',
 ARRAY['N1.2.3'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 11,
 'Place value: Tens and ones introduction', 'स्थानीय मान: दहाई और इकाई परिचय',
 ARRAY['N1.2.4'],
 'Use bundling sticks. Critical conceptual milestone.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 12,
 'Place value: Decomposition and expanded form', 'स्थानीय मान: विस्तारित रूप',
 ARRAY['N1.2.4'],
 'Second week on place value — it deserves it. Misconception-heavy.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 13,
 'Comparing 2-digit numbers', 'दो अंकों की संख्याओं की तुलना',
 ARRAY['N1.2.5'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 14,
 'Ordering numbers to 99', 'संख्या क्रम 99 तक',
 ARRAY['N1.2.6'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 15,
 'Geometry: 2D shape properties', 'ज्यामिति: 2D आकृतियों के गुण',
 ARRAY['N0.5.1','N1.5.1'],
 'Interleave with operations to prevent number-fatigue.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 16,
 'Addition: Concept and counting-on (sums ≤ 10)', 'जोड़: अवधारणा और आगे गिनना (योग ≤ 10)',
 ARRAY['N1.3.1'],
 'Concrete objects first. Teach counting-on, not counting-all.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 17,
 'Addition: Sums to 18, make-10 strategy', 'जोड़: 18 तक योग, 10 बनाओ रणनीति',
 ARRAY['N1.3.1'],
 'Finger ceiling misconception likely here — address proactively.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 18,
 'Addition: Fluency and doubles', 'जोड़: प्रवाह और युग्म',
 ARRAY['N1.3.1'],
 'Build automaticity. Doubles (3+3, 4+4) as anchor facts.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 19,
 'Consolidation: Number sense + addition review', 'समेकन: संख्या बोध + जोड़ दोहराई',
 ARRAY['N1.2.4','N1.3.1'],
 'Review before mid-year assessment.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 20,
 'Mid-year periodic assessment', 'अर्धवार्षिक मूल्यांकन',
 ARRAY['N0.2.2','N1.2.3','N1.2.4','N1.3.1'],
 'Full-class reassessment. Regroup all children from fresh evidence.', 0),

-- Term 2: Operations and application (Weeks 21-40)
('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 21,
 'Subtraction: Concept and taking away', 'घटाव: अवधारणा और निकालना',
 ARRAY['N1.3.2'],
 'Concrete manipulation: physically removing objects from a group.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 22,
 'Subtraction: Counting back, facts to 18', 'घटाव: पीछे गिनना, 18 तक',
 ARRAY['N1.3.2'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 23,
 'Subtraction: Fluency and relationship to addition', 'घटाव: प्रवाह और जोड़ से संबंध',
 ARRAY['N1.3.2'],
 'Teach inverse: if 5+3=8, then 8-3=5.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 24,
 'Word problems: Addition stories', 'शाब्दिक प्रश्न: जोड़ की कहानियाँ',
 ARRAY['N1.3.3'],
 'Act out with objects before abstract computation.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 25,
 'Word problems: Subtraction stories and mixed', 'शाब्दिक प्रश्न: घटाव और मिश्रित',
 ARRAY['N1.3.3'],
 'Operation selection is the diagnostic focus here.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 26,
 'Patterns: Extending and creating (AB, ABC, ABB, AAB)', 'पैटर्न: आगे बढ़ाना और बनाना',
 ARRAY['N1.1.1'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 27,
 'Measurement: Length comparison', 'मापन: लंबाई तुलना',
 ARRAY['N1.4.1'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 28,
 'Measurement: Time sequencing', 'मापन: समय क्रम',
 ARRAY['N1.4.2'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 29,
 'Geometry: 3D shapes', 'ज्यामिति: 3D आकृतियाँ',
 ARRAY['N1.5.2'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 30,
 'Number sense consolidation: Place value deep dive', 'संख्या बोध समेकन: स्थानीय मान गहराई',
 ARRAY['N1.2.4','N1.2.5'],
 'Revisit place value — spiral. Children who struggled in Term 1 get another pass.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 31,
 'Operations review: Addition + subtraction mixed', 'संक्रिया दोहराई: जोड़ + घटाव मिश्रित',
 ARRAY['N1.3.1','N1.3.2'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 32,
 'Word problems: Mixed operations with context', 'शाब्दिक प्रश्न: संदर्भ सहित मिश्रित',
 ARRAY['N1.3.3'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 33,
 'Enrichment: Number patterns and mental math', 'संवर्धन: संख्या पैटर्न और मानसिक गणित',
 ARRAY['N1.1.1','N1.3.1'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 34,
 'Consolidation: Full year review — number sense', 'समेकन: वार्षिक दोहराई — संख्या बोध',
 ARRAY['N1.2.3','N1.2.4','N1.2.5','N1.2.6'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 35,
 'Consolidation: Full year review — operations', 'समेकन: वार्षिक दोहराई — संक्रियाएँ',
 ARRAY['N1.3.1','N1.3.2','N1.3.3'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'numeracy', 36,
 'End-year periodic assessment', 'वार्षिक मूल्यांकन',
 ARRAY['N1.2.2','N1.2.3','N1.2.4','N1.2.5','N1.3.1','N1.3.2','N1.3.3'],
 'Full-class reassessment across all Grade 1 competencies. Final B/P/P for year.', 0),


-- ============================================================================
-- GRADE 2 NUMERACY — 36 weeks (representative; weeks 1-36)
-- Target: 3-digit numbers, 2-digit operations with regrouping, intro multiplication
-- ============================================================================

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'numeracy', 1,
 'Baseline assessment', 'आधारभूत मूल्यांकन',
 ARRAY['N1.2.4','N1.2.5','N1.3.1','N1.3.2','N1.3.3'],
 'Assess Grade 1 competencies. Children arriving from Grade 1 may not all be Proficient.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'numeracy', 2,
 'Baseline + Grade 1 remediation', 'आधारभूत + कक्षा 1 उपचारात्मक',
 ARRAY['N1.2.4','N1.3.1','N1.3.2'],
 'Complete baseline. Begin remediation for Beginners on Grade 1 gaps.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'numeracy', 3,
 'Place value review: Tens and ones', 'स्थानीय मान दोहराई: दहाई और इकाई',
 ARRAY['N1.2.4'],
 'Critical prerequisite for all Grade 2 operations. Beginners need solid foundation here.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'numeracy', 4,
 '3-digit numbers: Reading and writing 100-999', 'तीन अंकों की संख्याएँ: 100-999 पढ़ना-लिखना',
 ARRAY['N2.2.1'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'numeracy', 5,
 'Place value: Hundreds, tens, ones', 'स्थानीय मान: सैकड़ा, दहाई, इकाई',
 ARRAY['N2.2.2'],
 'Zero in middle (305) misconception — teach explicitly.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'numeracy', 6,
 'Place value: Expanded form and zero handling', 'स्थानीय मान: विस्तारित रूप और शून्य',
 ARRAY['N2.2.2'],
 'Second week — face value vs place value misconception focus.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'numeracy', 7,
 'Comparing 3-digit numbers', 'तीन अंकों की संख्याओं की तुलना',
 ARRAY['N2.2.3'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'numeracy', 8,
 'Skip counting: 2s, 5s, 10s', 'गुणज गिनती: 2, 5, 10',
 ARRAY['N2.2.4'],
 'Foundation for multiplication. Oral/observed assessment.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'numeracy', 9,
 '2-digit addition: Without regrouping', 'दो अंकों का जोड़: बिना हासिल',
 ARRAY['N2.3.1'],
 'Column alignment. Use place-value grid worksheets.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'numeracy', 10,
 '2-digit addition: With regrouping (carry)', 'दो अंकों का जोड़: हासिल के साथ',
 ARRAY['N2.3.2'],
 'THE most misconception-rich competency. Bundling stick demonstration essential.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'numeracy', 11,
 '2-digit addition: Carry fluency and practice', 'दो अंकों का जोड़: हासिल अभ्यास',
 ARRAY['N2.3.2'],
 'Second week on carry. Diagnose M1-M4 misconceptions from worksheets.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'numeracy', 12,
 '2-digit subtraction: Without borrowing', 'दो अंकों का घटाव: बिना उधार',
 ARRAY['N2.3.3'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'numeracy', 13,
 '2-digit subtraction: With borrowing', 'दो अंकों का घटाव: उधार के साथ',
 ARRAY['N2.3.4'],
 'Smaller-from-larger reversal (M1) is the #1 error to detect.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'numeracy', 14,
 '2-digit subtraction: Borrowing fluency', 'दो अंकों का घटाव: उधार अभ्यास',
 ARRAY['N2.3.4'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'numeracy', 15,
 'Geometry: Symmetry', 'ज्यामिति: सममिति',
 ARRAY['N2.5.1'],
 'Interleave. Hands-on paper folding activity.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'numeracy', 16,
 'Word problems: 2-digit addition and subtraction', 'शाब्दिक प्रश्न: दो अंकों का जोड़-घटाव',
 ARRAY['N2.3.5'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'numeracy', 17,
 'Word problems: Mixed operations', 'शाब्दिक प्रश्न: मिश्रित संक्रियाएँ',
 ARRAY['N2.3.5'],
 'Operation selection errors — diagnose N2.3.5-M1.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'numeracy', 18,
 'Measurement: Non-standard length, calendar', 'मापन: अमानक लंबाई, कैलेंडर',
 ARRAY['N2.4.1','N2.4.2'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'numeracy', 19,
 'Money: Coins, notes, making amounts', 'मुद्रा: सिक्के, नोट, राशि बनाना',
 ARRAY['N2.4.3'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'numeracy', 20,
 'Mid-year periodic assessment', 'अर्धवार्षिक मूल्यांकन',
 ARRAY['N2.2.2','N2.3.2','N2.3.4','N2.3.5'],
 'Full reassessment. Regroup.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'numeracy', 21,
 'Operations consolidation: Addition + subtraction mixed', 'संक्रिया समेकन',
 ARRAY['N2.3.2','N2.3.4'],
 'Post-assessment remediation based on regrouped data.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'numeracy', 22,
 'Multiplication: Repeated addition concept', 'गुणा: बार-बार जोड़ की अवधारणा',
 ARRAY['N2.3.6'],
 'Concrete groups of objects. 3 groups of 4 = 4+4+4.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'numeracy', 23,
 'Multiplication: Notation and practice', 'गुणा: संकेतन और अभ्यास',
 ARRAY['N2.3.6'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'numeracy', 24,
 'Data handling: Pictographs', 'आँकड़ा प्रबंधन: चित्र-आलेख',
 ARRAY['N2.6.1'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'numeracy', 25,
 'Number sense spiral: Place value deep revisit', 'संख्या बोध सर्पिल: स्थानीय मान गहराई',
 ARRAY['N2.2.2','N2.2.3'],
 'Spiral — students who struggled in Term 1 get another pass.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'numeracy', 26,
 'Operations spiral: Carry + borrow mixed practice', 'संक्रिया सर्पिल: हासिल + उधार मिश्रित',
 ARRAY['N2.3.2','N2.3.4'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'numeracy', 27,
 'Word problems: All operations including multiplication contexts', 'शाब्दिक प्रश्न: सभी संक्रियाएँ',
 ARRAY['N2.3.5','N2.3.6'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'numeracy', 28,
 'Consolidation: Full year review', 'समेकन: वार्षिक दोहराई',
 ARRAY['N2.2.2','N2.3.2','N2.3.4','N2.3.5','N2.3.6'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'numeracy', 29,
 'End-year periodic assessment', 'वार्षिक मूल्यांकन',
 ARRAY['N2.2.1','N2.2.2','N2.2.3','N2.3.2','N2.3.4','N2.3.5','N2.3.6'],
 'Full-class reassessment. Final B/P/P.', 0),


-- ============================================================================
-- GRADE 3 NUMERACY — 36 weeks (representative; weeks 1-36)
-- Target: 4-digit numbers, 3-digit operations, multiplication tables, division intro
-- ============================================================================

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'numeracy', 1,
 'Baseline assessment', 'आधारभूत मूल्यांकन',
 ARRAY['N2.2.2','N2.3.2','N2.3.4','N2.3.5','N2.3.6'],
 'Assess Grade 2 competencies. Identify who still has carry/borrow misconceptions.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'numeracy', 2,
 'Baseline + remediation', 'आधारभूत + उपचारात्मक',
 ARRAY['N2.3.2','N2.3.4'],
 'Beginners: remediate 2-digit operations. Proficients: preview 3-digit numbers.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'numeracy', 3,
 '4-digit numbers: Reading and writing 1000-9999', 'चार अंकों की संख्याएँ: 1000-9999',
 ARRAY['N3.2.1'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'numeracy', 4,
 'Place value: Thousands, hundreds, tens, ones', 'स्थानीय मान: हज़ार, सैकड़ा, दहाई, इकाई',
 ARRAY['N3.2.2'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'numeracy', 5,
 'Place value: Expanded form and comparison', 'स्थानीय मान: विस्तारित रूप और तुलना',
 ARRAY['N3.2.2','N3.2.3'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'numeracy', 6,
 '3-digit addition: Without and with single carry', 'तीन अंकों का जोड़: बिना और एक हासिल',
 ARRAY['N3.3.1'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'numeracy', 7,
 '3-digit addition: Double carry', 'तीन अंकों का जोड़: दोहरा हासिल',
 ARRAY['N3.3.1'],
 'N3.3.1-M1: Single carry works but double carry fails. Key diagnostic week.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'numeracy', 8,
 '3-digit subtraction: With borrowing', 'तीन अंकों का घटाव: उधार के साथ',
 ARRAY['N3.3.2'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'numeracy', 9,
 '3-digit subtraction: Borrowing across zero', 'तीन अंकों का घटाव: शून्य से उधार',
 ARRAY['N3.3.2'],
 '502-167: borrow from hundreds when tens is 0. Difficult.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'numeracy', 10,
 'Multiplication tables: 2, 5, 10', 'गुणन सारणी: 2, 5, 10',
 ARRAY['N3.3.3'],
 'Start with easy tables. Connect to skip counting from Grade 2.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'numeracy', 11,
 'Multiplication tables: 3, 4', 'गुणन सारणी: 3, 4',
 ARRAY['N3.3.3'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'numeracy', 12,
 'Multiplication tables: 6, 7, 8, 9', 'गुणन सारणी: 6, 7, 8, 9',
 ARRAY['N3.3.3'],
 'Hardest tables. Commutative property helps: 6×7 = 7×6.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'numeracy', 13,
 'Measurement: Length in cm and m', 'मापन: सेमी और मी में लंबाई',
 ARRAY['N3.4.1'],
 'Interleave. Ruler reading + unit conversion.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'numeracy', 14,
 'Multiplication: 2-digit × 1-digit introduction', 'गुणा: दो अंक × एक अंक परिचय',
 ARRAY['N3.3.4'],
 'Box/grid method as visual scaffold before column method.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'numeracy', 15,
 'Multiplication: 2-digit × 1-digit fluency', 'गुणा: दो अंक × एक अंक अभ्यास',
 ARRAY['N3.3.4'],
 'N3.3.4-M1: multiplies digits independently. Diagnose.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'numeracy', 16,
 'Geometry: Angles — right, acute, obtuse', 'ज्यामिति: कोण — समकोण, न्यूनकोण, अधिककोण',
 ARRAY['N3.5.1'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'numeracy', 17,
 'Geometry: Perimeter', 'ज्यामिति: परिमाप',
 ARRAY['N3.5.2'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'numeracy', 18,
 'Measurement: Time (clock) and weight (g, kg)', 'मापन: समय (घड़ी) और भार (ग्राम, किग्रा)',
 ARRAY['N3.4.2','N3.4.3'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'numeracy', 19,
 'Consolidation before mid-year', 'अर्धवार्षिक पूर्व समेकन',
 ARRAY['N3.3.1','N3.3.2','N3.3.3','N3.3.4'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'numeracy', 20,
 'Mid-year periodic assessment', 'अर्धवार्षिक मूल्यांकन',
 ARRAY['N3.2.2','N3.3.1','N3.3.2','N3.3.3','N3.3.4'],
 'Full reassessment. Regroup.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'numeracy', 21,
 'Division: Equal sharing concept', 'भाग: बराबर बँटवारे की अवधारणा',
 ARRAY['N3.3.5'],
 'Concrete objects: distribute 12 among 3 friends.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'numeracy', 22,
 'Division: Grouping and repeated subtraction', 'भाग: समूहन और बार-बार घटाव',
 ARRAY['N3.3.5'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'numeracy', 23,
 'Division: Remainders', 'भाग: शेषफल',
 ARRAY['N3.3.5'],
 'N3.3.5-M2: cannot handle remainders. Explicit teaching.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'numeracy', 24,
 'Division: Relationship to multiplication', 'भाग: गुणा से संबंध',
 ARRAY['N3.3.5','N3.3.3'],
 'If 4×6=24 then 24÷6=4. Inverse relationship.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'numeracy', 25,
 'Data handling: Bar graphs', 'आँकड़ा प्रबंधन: दण्ड आलेख',
 ARRAY['N3.6.1'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'numeracy', 26,
 'Data handling: Tables and tally marks', 'आँकड़ा प्रबंधन: सारणी और टैली',
 ARRAY['N3.6.2'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'numeracy', 27,
 'Multi-step word problems: Introduction', 'बहु-चरणीय शाब्दिक प्रश्न: परिचय',
 ARRAY['N3.3.6'],
 'Break into sub-questions. N3.3.6-M1: performs only one step.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'numeracy', 28,
 'Multi-step word problems: Practice', 'बहु-चरणीय शाब्दिक प्रश्न: अभ्यास',
 ARRAY['N3.3.6'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'numeracy', 29,
 'Operations spiral: All four operations mixed', 'संक्रिया सर्पिल: चारों संक्रियाएँ मिश्रित',
 ARRAY['N3.3.1','N3.3.2','N3.3.4','N3.3.5'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'numeracy', 30,
 'Consolidation: Full year review', 'समेकन: वार्षिक दोहराई',
 ARRAY['N3.2.2','N3.3.1','N3.3.2','N3.3.4','N3.3.5','N3.3.6'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'numeracy', 31,
 'End-year periodic assessment', 'वार्षिक मूल्यांकन',
 ARRAY['N3.2.2','N3.2.3','N3.3.1','N3.3.2','N3.3.3','N3.3.4','N3.3.5','N3.3.6'],
 'Full-class reassessment. NIPUN target check.', 0);
