-- ============================================================================
-- ANKUR SAATHI — Layer 1 KB: Numeracy Seed Data
-- Part 2: Prerequisite Links (DAG) + Learning Outcomes
-- ============================================================================

-- ============================================================================
-- PREREQUISITE LINKS
-- These form a DAG (directed acyclic graph), not a linear chain.
-- A competency can have multiple prerequisites.
-- "hard" = must be mastered before this competency makes sense
-- "soft" = strongly helps but not strictly required
-- ============================================================================

INSERT INTO competency_prerequisites (competency_id, prerequisite_id, prerequisite_type) VALUES

-- ─── COUNTING CHAIN ───
-- Rote counting → 1:1 counting (you need the sequence before you can tag objects)
('N0.2.2', 'N0.2.1', 'hard'),       -- 1:1 counting (10) needs rote counting (20)
('N1.2.1', 'N0.2.1', 'hard'),       -- Rote counting (100) needs rote counting (20)
('N1.2.2', 'N0.2.2', 'hard'),       -- 1:1 counting (20) needs 1:1 counting (10)
('N1.2.2', 'N1.2.1', 'hard'),       -- 1:1 counting (20) needs rote counting (100)

-- ─── NUMERAL RECOGNITION → WRITING CHAIN ───
('N0.2.4', 'N0.2.3', 'hard'),       -- Writing 1-9 needs recognising 1-9
('N1.2.3', 'N0.2.4', 'hard'),       -- Reading/writing 1-99 needs writing 1-9
('N2.2.1', 'N1.2.3', 'hard'),       -- Reading/writing 100-999 needs reading/writing 1-99
('N3.2.1', 'N2.2.1', 'hard'),       -- Reading/writing 1000-9999 needs reading/writing 100-999

-- ─── PLACE VALUE CHAIN ───
-- This is the critical conceptual backbone
('N1.2.4', 'N1.2.3', 'hard'),       -- Place value (T,O) needs numeral reading/writing
('N1.2.4', 'N1.2.2', 'soft'),       -- Place value helped by 1:1 counting (conceptual grounding)
('N2.2.2', 'N1.2.4', 'hard'),       -- Place value (H,T,O) needs place value (T,O)
('N2.2.2', 'N2.2.1', 'hard'),       -- Place value (H,T,O) needs reading 3-digit numbers
('N3.2.2', 'N2.2.2', 'hard'),       -- Place value (Th,H,T,O) needs place value (H,T,O)
('N3.2.2', 'N3.2.1', 'hard'),       -- Place value (Th,H,T,O) needs reading 4-digit numbers

-- ─── NUMBER COMPARISON CHAIN ───
('N1.2.5', 'N1.2.4', 'hard'),       -- Comparing 2-digit needs place value understanding
('N1.2.5', 'N0.1.3', 'soft'),       -- Comparing 2-digit helped by early more/less/same concept
('N1.2.6', 'N1.2.5', 'hard'),       -- Ordering needs comparison
('N2.2.3', 'N2.2.2', 'hard'),       -- Comparing 3-digit needs 3-digit place value
('N2.2.3', 'N1.2.5', 'soft'),       -- Comparing 3-digit helped by comparing 2-digit
('N3.2.3', 'N3.2.2', 'hard'),       -- Comparing 4-digit needs 4-digit place value
('N3.2.3', 'N2.2.3', 'soft'),       -- Comparing 4-digit helped by comparing 3-digit

-- ─── ADDITION CHAIN ───
-- THE most important chain for daily differentiation
('N1.3.1', 'N0.2.2', 'hard'),       -- Single-digit addition needs counting objects
('N1.3.1', 'N0.2.4', 'hard'),       -- Single-digit addition needs writing numerals
('N2.3.1', 'N1.3.1', 'hard'),       -- 2-digit addition (no carry) needs single-digit addition
('N2.3.1', 'N1.2.4', 'hard'),       -- 2-digit addition needs place value (T,O) — CRITICAL prerequisite
('N2.3.2', 'N2.3.1', 'hard'),       -- 2-digit addition (carry) needs 2-digit addition (no carry)
('N3.3.1', 'N2.3.2', 'hard'),       -- 3-digit addition needs 2-digit addition with carry
('N3.3.1', 'N2.2.2', 'hard'),       -- 3-digit addition needs 3-digit place value

-- ─── SUBTRACTION CHAIN ───
('N1.3.2', 'N1.3.1', 'soft'),       -- Single-digit subtraction helped by addition (inverse concept)
('N1.3.2', 'N0.2.2', 'hard'),       -- Single-digit subtraction needs counting
('N2.3.3', 'N1.3.2', 'hard'),       -- 2-digit subtraction (no borrow) needs single-digit subtraction
('N2.3.3', 'N1.2.4', 'hard'),       -- 2-digit subtraction needs place value
('N2.3.4', 'N2.3.3', 'hard'),       -- 2-digit subtraction (borrow) needs without borrowing
('N2.3.4', 'N2.2.2', 'soft'),       -- Borrowing concept benefits from deeper place value understanding
('N3.3.2', 'N2.3.4', 'hard'),       -- 3-digit subtraction needs 2-digit with borrowing
('N3.3.2', 'N2.2.2', 'hard'),       -- 3-digit subtraction needs 3-digit place value

-- ─── MULTIPLICATION CHAIN ───
('N2.3.6', 'N1.3.1', 'hard'),       -- Multiplication as repeated addition needs single-digit addition
('N2.2.4', 'N1.2.1', 'hard'),       -- Skip counting needs rote counting to 100
('N3.3.3', 'N2.3.6', 'hard'),       -- Multiplication tables need understanding multiplication concept
('N3.3.3', 'N2.2.4', 'soft'),       -- Tables helped by skip counting (2s, 5s, 10s)
('N3.3.4', 'N3.3.3', 'hard'),       -- 2-digit × 1-digit needs multiplication tables
('N3.3.4', 'N2.2.2', 'hard'),       -- 2-digit × 1-digit needs place value for partial products

-- ─── DIVISION CHAIN ───
('N3.3.5', 'N3.3.3', 'hard'),       -- Division needs multiplication tables (inverse)
('N3.3.5', 'N1.3.2', 'soft'),       -- Division concept helped by subtraction (repeated subtraction view)

-- ─── WORD PROBLEMS ───
('N1.3.3', 'N1.3.1', 'hard'),       -- Word problems need computation skills
('N1.3.3', 'N1.3.2', 'hard'),       -- Word problems need both addition and subtraction
('N2.3.5', 'N2.3.2', 'hard'),       -- 2-digit word problems need 2-digit addition
('N2.3.5', 'N2.3.4', 'hard'),       -- 2-digit word problems need 2-digit subtraction
('N2.3.5', 'N1.3.3', 'soft'),       -- 2-digit word problems helped by single-digit word problems
('N3.3.6', 'N3.3.1', 'hard'),       -- Multi-step word problems need 3-digit addition
('N3.3.6', 'N3.3.2', 'hard'),       -- Multi-step word problems need 3-digit subtraction
('N3.3.6', 'N3.3.4', 'hard'),       -- Multi-step word problems need multiplication
('N3.3.6', 'N2.3.5', 'soft'),       -- Multi-step helped by single-step word problem experience

-- ─── PATTERNS ───
('N1.1.1', 'N0.1.2', 'hard'),       -- Grade 1 patterns need Balvatika pattern foundation

-- ─── GEOMETRY CHAIN ───
('N1.5.1', 'N0.5.1', 'hard'),       -- Describing shape properties needs shape identification
('N2.5.1', 'N1.5.1', 'hard'),       -- Symmetry needs understanding of shape properties
('N3.5.1', 'N1.5.1', 'soft'),       -- Angle classification helped by shape property awareness
('N3.5.2', 'N3.3.1', 'hard'),       -- Perimeter calculation needs addition of 3-digit numbers
('N3.5.2', 'N3.4.1', 'soft'),       -- Perimeter helped by length measurement understanding

-- ─── MEASUREMENT CHAIN ───
('N2.4.1', 'N1.4.1', 'hard'),       -- Non-standard measurement needs comparison concept
('N3.4.1', 'N2.4.1', 'hard'),       -- Standard measurement needs non-standard experience
('N3.4.1', 'N2.2.2', 'soft'),       -- Standard measurement helped by 3-digit number sense (for cm values)

-- ─── DATA HANDLING CHAIN ───
('N2.6.1', 'N1.2.5', 'soft'),       -- Pictograph reading helped by number comparison
('N3.6.1', 'N2.6.1', 'hard'),       -- Bar graphs need pictograph reading foundation
('N3.6.2', 'N2.6.1', 'soft'),       -- Data tables helped by pictograph experience
('N3.6.1', 'N2.3.3', 'soft'),       -- Bar graph interpretation helped by subtraction (finding differences)

-- ─── CROSS-DOMAIN: MONEY → OPERATIONS ───
('N2.4.3', 'N1.3.1', 'hard'),       -- Making amounts needs addition skill
('N2.4.3', 'N1.2.4', 'soft');       -- Making amounts helped by place value (₹10 = ten ₹1)


-- ============================================================================
-- LEARNING OUTCOMES
-- Granular measurable items under each competency.
-- Individual worksheet problems map to these.
-- ============================================================================
-- Covering the key competencies that drive daily differentiation.
-- Not exhaustive for every competency — focused on operations + number sense
-- where granular tracking matters most.
-- ============================================================================

INSERT INTO learning_outcomes (id, competency_id, name_en, name_hi, sort_order, assessment_modality) VALUES

-- N0.2.2: 1:1 counting to 10
('N0.2.2.a', 'N0.2.2', 'Tags each object exactly once while counting', 'गिनते समय प्रत्येक वस्तु को ठीक एक बार छूता है', 1, 'observed'),
('N0.2.2.b', 'N0.2.2', 'States the last number as the total (cardinality)', 'अंतिम संख्या को कुल बताता है (गणनांक)', 2, 'observed'),
('N0.2.2.c', 'N0.2.2', 'Counts objects in any arrangement (not just lines)', 'किसी भी व्यवस्था में वस्तुएँ गिनता है (केवल पंक्ति नहीं)', 3, 'observed'),

-- N1.2.4: Place value (tens and ones)
('N1.2.4.a', 'N1.2.4', 'Identifies tens digit and ones digit in a 2-digit number', '2 अंकों की संख्या में दहाई और इकाई अंक पहचानता है', 1, NULL),
('N1.2.4.b', 'N1.2.4', 'States the value of each digit (e.g., 3 in 34 means 30)', 'प्रत्येक अंक का मान बताता है (जैसे 34 में 3 का मतलब 30)', 2, NULL),
('N1.2.4.c', 'N1.2.4', 'Represents numbers using bundles of tens and loose ones', 'दहाई के बंडल और खुली इकाइयों से संख्या दर्शाता है', 3, 'observed'),
('N1.2.4.d', 'N1.2.4', 'Writes expanded form: 45 = 40 + 5', 'विस्तारित रूप लिखता है: 45 = 40 + 5', 4, 'written'),

-- N1.3.1: Single-digit addition
('N1.3.1.a', 'N1.3.1', 'Adds using counting-on strategy (not counting all)', 'आगे गिनकर जोड़ता है (सब गिनने की बजाय)', 1, NULL),
('N1.3.1.b', 'N1.3.1', 'Adds doubles (3+3, 4+4) fluently', 'युग्म (3+3, 4+4) तेज़ी से जोड़ता है', 2, NULL),
('N1.3.1.c', 'N1.3.1', 'Adds any two single-digit numbers with sum ≤ 18', '18 तक योग वाली किन्हीं दो संख्याओं का जोड़', 3, NULL),
('N1.3.1.d', 'N1.3.1', 'Relates addition to combining groups of objects', 'जोड़ को वस्तुओं के समूहों को मिलाने से जोड़ता है', 4, 'observed'),

-- N1.3.2: Single-digit subtraction
('N1.3.2.a', 'N1.3.2', 'Subtracts using counting-back strategy', 'पीछे गिनकर घटाता है', 1, NULL),
('N1.3.2.b', 'N1.3.2', 'Relates subtraction to taking away from a group', 'घटाव को समूह से निकालने से जोड़ता है', 2, 'observed'),
('N1.3.2.c', 'N1.3.2', 'Subtracts any single-digit number from numbers ≤ 18', '18 तक की संख्या से एक अंक घटाता है', 3, NULL),

-- N2.3.1: 2-digit addition without carry
('N2.3.1.a', 'N2.3.1', 'Aligns numbers vertically by place value', 'संख्याओं को स्थानीय मान से खड़ा लिखता है', 1, 'written'),
('N2.3.1.b', 'N2.3.1', 'Adds ones column correctly', 'इकाई का स्तम्भ सही जोड़ता है', 2, 'written'),
('N2.3.1.c', 'N2.3.1', 'Adds tens column correctly', 'दहाई का स्तम्भ सही जोड़ता है', 3, 'written'),
('N2.3.1.d', 'N2.3.1', 'Writes final answer in correct place', 'उत्तर सही स्थान पर लिखता है', 4, 'written'),

-- N2.3.2: 2-digit addition WITH carry — richest for misconception detection
('N2.3.2.a', 'N2.3.2', 'Recognises when ones sum exceeds 9 (carry needed)', 'पहचानता है कि इकाई का योग 9 से अधिक है (हासिल आवश्यक)', 1, 'written'),
('N2.3.2.b', 'N2.3.2', 'Writes ones digit of sum in ones column', 'योग का इकाई अंक इकाई स्तम्भ में लिखता है', 2, 'written'),
('N2.3.2.c', 'N2.3.2', 'Carries tens digit to tens column', 'हासिल को दहाई स्तम्भ में ले जाता है', 3, 'written'),
('N2.3.2.d', 'N2.3.2', 'Adds carry to tens column sum', 'दहाई के योग में हासिल जोड़ता है', 4, 'written'),

-- N2.3.4: 2-digit subtraction with borrowing
('N2.3.4.a', 'N2.3.4', 'Recognises when ones digit of minuend < subtrahend (borrow needed)', 'पहचानता है कि ऊपर की इकाई नीचे से छोटी है (उधार आवश्यक)', 1, 'written'),
('N2.3.4.b', 'N2.3.4', 'Borrows 1 ten and adds 10 to ones', '1 दहाई उधार लेता है और इकाई में 10 जोड़ता है', 2, 'written'),
('N2.3.4.c', 'N2.3.4', 'Reduces tens digit by 1 after borrowing', 'उधार के बाद दहाई 1 कम करता है', 3, 'written'),
('N2.3.4.d', 'N2.3.4', 'Completes subtraction after borrowing', 'उधार के बाद घटाव पूरा करता है', 4, 'written'),

-- N2.2.2: 3-digit place value
('N2.2.2.a', 'N2.2.2', 'Identifies hundreds, tens, ones digits', 'सैकड़ा, दहाई, इकाई अंक पहचानता है', 1, NULL),
('N2.2.2.b', 'N2.2.2', 'States value of each digit (e.g., 3 in 345 = 300)', 'प्रत्येक अंक का मान बताता है', 2, NULL),
('N2.2.2.c', 'N2.2.2', 'Writes expanded form: 345 = 300 + 40 + 5', 'विस्तारित रूप लिखता है', 3, 'written'),
('N2.2.2.d', 'N2.2.2', 'Handles zero in tens or ones place (e.g., 305 = 300 + 5)', 'दहाई या इकाई में शून्य संभालता है', 4, 'written'),

-- N3.3.4: 2-digit × 1-digit multiplication
('N3.3.4.a', 'N3.3.4', 'Multiplies ones digit correctly', 'इकाई अंक का गुणा सही करता है', 1, 'written'),
('N3.3.4.b', 'N3.3.4', 'Carries if ones product > 9', 'इकाई गुणनफल 9 से अधिक हो तो हासिल रखता है', 2, 'written'),
('N3.3.4.c', 'N3.3.4', 'Multiplies tens digit and adds carry', 'दहाई का गुणा करता है और हासिल जोड़ता है', 3, 'written'),

-- N3.3.5: Division
('N3.3.5.a', 'N3.3.5', 'Divides using equal sharing with concrete objects', 'वस्तुओं के बराबर बँटवारे से भाग करता है', 1, 'observed'),
('N3.3.5.b', 'N3.3.5', 'Divides using repeated subtraction/grouping', 'बार-बार घटाव/समूहन से भाग करता है', 2, 'written'),
('N3.3.5.c', 'N3.3.5', 'Identifies and expresses remainder', 'शेषफल पहचानता और व्यक्त करता है', 3, 'written'),
('N3.3.5.d', 'N3.3.5', 'Relates division to multiplication (inverse)', 'भाग को गुणा से जोड़ता है (व्युत्क्रम)', 4, NULL);
