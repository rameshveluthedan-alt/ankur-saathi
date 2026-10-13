-- ============================================================================
-- ANKUR SAATHI — Layer 1 KB: Numeracy Seed Data
-- Part 3: Misconception Taxonomy
-- ============================================================================
-- Every entry maps: competency → error pattern → diagnostic indicator → intervention
-- Claude Vision matches worksheet responses against THIS taxonomy.
-- Nothing is hallucinated — every diagnosis category is research-derived.
-- ============================================================================

INSERT INTO misconceptions (id, competency_id, name_en, name_hi, error_pattern, diagnostic_indicator, example_correct, example_incorrect, intervention_strategy, intervention_template_ids, severity, frequency, sort_order) VALUES

-- ============================================================================
-- BALVATIKA & GRADE 1: NUMBER SENSE MISCONCEPTIONS
-- ============================================================================

-- N0.2.2: 1:1 counting
('N0.2.2-M1', 'N0.2.2',
 'Double-counting (touches object twice)',
 'दोहरी गिनती (वस्तु को दो बार छूता है)',
 'Child counts the same object twice, getting a higher total',
 'Reported total is consistently higher than actual count; observed tagging shows repeated touches on same object',
 'Count: 7 objects → answer: 7',
 'Count: 7 objects → answer: 9 (touched 2 objects twice)',
 'Use line-up counting: place objects in a line, physically move each counted object to a "counted" pile. Slow down counting speed.',
 ARRAY['INT-NUM-001'], 'critical', 'very_common', 1),

('N0.2.2-M2', 'N0.2.2',
 'Skipping objects while counting',
 'गिनते समय वस्तुओं को छोड़ना',
 'Child skips objects, getting a lower total than actual',
 'Reported total is consistently lower; observed counting shows objects not tagged',
 'Count: 8 objects → answer: 8',
 'Count: 8 objects → answer: 6 (skipped 2)',
 'Use structured arrangements first (line), then move to scattered. Mark each counted object with a sticker.',
 ARRAY['INT-NUM-001'], 'critical', 'common', 2),

('N0.2.2-M3', 'N0.2.2',
 'No cardinality understanding',
 'गणनांक की समझ नहीं',
 'Child counts correctly but when asked "how many?" restarts counting or gives random number',
 'After counting 7 objects, when asked "how many are there?" child does not say 7 or restarts counting',
 'Counts to 7, asked how many → "7"',
 'Counts to 7, asked how many → recounts or says random number',
 'After each count, emphasise: "You counted 7. So there are 7. The last number tells us how many." Repeat with different quantities.',
 ARRAY['INT-NUM-002'], 'critical', 'common', 3),

-- N0.2.3: Numeral recognition
('N0.2.3-M1', 'N0.2.3',
 'Mirror confusion: 6 and 9',
 '6 और 9 में भ्रम',
 'Child confuses 6 and 9 because they are rotational mirrors',
 'Consistently reads 6 as 9 or vice versa; other numerals are correct',
 '6 → "six", 9 → "nine"',
 '6 → "nine", 9 → "six"',
 'Use tactile tracing: trace 6 starting from top-curve-down, 9 starting from top-circle-then-down. Associate with concrete anchors: 6 has belly below, 9 has head above.',
 ARRAY['INT-NUM-003'], 'moderate', 'very_common', 1),

('N0.2.3-M2', 'N0.2.3',
 'Mirror confusion: 2 and 5',
 '2 और 5 में भ्रम',
 'Child confuses 2 and 5',
 'Reads 2 as 5 or vice versa; pattern is consistent across sessions',
 NULL, NULL,
 'Trace with finger: 2 curves right then left; 5 goes down then curves right. Use body movements: "2 is a swan neck, 5 is a chair."',
 ARRAY['INT-NUM-003'], 'moderate', 'common', 2),

-- N1.2.3: Reading/writing 2-digit numerals
('N1.2.3-M1', 'N1.2.3',
 'Digit reversal in writing (writes 31 for 13)',
 'लिखते समय अंक उलटना (13 के लिए 31 लिखता है)',
 'Child reverses the digit order when writing 2-digit numbers from dictation',
 'Consistently writes digits in wrong order: "thirteen" → writes 31; but reads 31 correctly as thirty-one',
 'Thirteen → writes 13',
 'Thirteen → writes 31',
 'Emphasise: Hindi number names go ones-first (तेरह = तीन + दस) but writing goes tens-first. Use place-value chart during writing: always write in T|O columns.',
 ARRAY['INT-NUM-004'], 'critical', 'very_common', 1),

('N1.2.3-M2', 'N1.2.3',
 'Teen number confusion (11-19)',
 'किशोर संख्याओं (11-19) में भ्रम',
 'Child struggles specifically with numbers 11-19 because naming is irregular',
 'Errors concentrated in 11-19 range; numbers 20+ are written correctly',
 NULL, NULL,
 'Teach teens explicitly as "10 and ___": ग्यारह = 10 + 1, बारह = 10 + 2. Use bundling sticks: 1 bundle of 10 + loose ones.',
 ARRAY['INT-NUM-004', 'INT-NUM-005'], 'moderate', 'very_common', 2),


-- ============================================================================
-- GRADE 1: PLACE VALUE MISCONCEPTIONS — foundational for all operations
-- ============================================================================

('N1.2.4-M1', 'N1.2.4',
 'Treats digits independently (23 = "2 and 3" not "20 and 3")',
 'अंकों को स्वतंत्र मानना (23 = "2 और 3", "20 और 3" नहीं)',
 'Child sees 23 as two separate digits (2 and 3) not as 2 tens and 3 ones',
 'When asked "what does the 2 in 23 mean?" child says "2" not "20" or "2 tens"',
 '23: the 2 means 20 (or 2 tens)',
 '23: the 2 means 2',
 'Extensive bundling stick work: physically bundle 10 sticks, show that 23 = 2 bundles + 3 loose. Break and rebuild repeatedly. Use place-value mat.',
 ARRAY['INT-PV-001'], 'critical', 'very_common', 1),

('N1.2.4-M2', 'N1.2.4',
 'Reverses tens and ones positions',
 'दहाई और इकाई का स्थान बदलता है',
 'Child identifies the ones digit as tens and vice versa',
 'Points to ones digit when asked about tens, or writes 5 in tens column and 4 in ones for "forty-five"',
 '45: tens digit = 4, ones digit = 5',
 '45: tens digit = 5, ones digit = 4',
 'Always use labelled place-value chart (T|O header). Read numbers left-to-right: "first digit = tens, second = ones." Practise with physical chart daily.',
 ARRAY['INT-PV-001', 'INT-PV-002'], 'critical', 'common', 2),


-- ============================================================================
-- GRADE 1: OPERATIONS MISCONCEPTIONS
-- ============================================================================

('N1.3.1-M1', 'N1.3.1',
 'Counting-all instead of counting-on',
 'आगे गिनने की बजाय पूरा गिनना',
 'For 5+3, child counts 1,2,3,4,5...6,7,8 instead of starting from 5 and counting 6,7,8',
 'Child is slow and uses fingers from 1; accuracy may be fine but strategy is inefficient and will fail for larger numbers',
 '5 + 3: starts at 5, counts 6, 7, 8 → 8',
 '5 + 3: starts at 1, counts to 5, then 6, 7, 8 → 8 (correct but slow)',
 'Model counting-on: "Put 5 in your head, count 3 more on your fingers: 6, 7, 8." Use number line: finger on 5, jump 3. Not an error per se, but a strategy that must evolve.',
 ARRAY['INT-OP-001'], 'minor', 'very_common', 1),

('N1.3.1-M2', 'N1.3.1',
 'Off-by-one error in counting-on',
 'आगे गिनते समय एक की त्रुटि',
 'Child counts the starting number as the first count-on, getting answer that is 1 less',
 'Answers are consistently exactly 1 less than correct: 5+3=7, 4+2=5, 6+3=8',
 '5 + 3 = 8',
 '5 + 3 = 7 (counts 5, 6, 7 — counted "5" as first jump)',
 'Explicitly teach: "Say 5 in your head. Now count MORE: 6 (show 1 finger), 7 (2 fingers), 8 (3 fingers). Three fingers = three more."',
 ARRAY['INT-OP-001'], 'moderate', 'very_common', 2),

('N1.3.1-M3', 'N1.3.1',
 'Finger counting ceiling (fails when sum > 10)',
 'उँगलियों से गिनने की सीमा (योग > 10 पर असफल)',
 'Child uses fingers and cannot compute when both numbers together exceed 10 fingers',
 'Correct for sums ≤ 10 but errors when sum is 11-18; may refuse to attempt or guess',
 '7 + 5 = 12',
 '7 + 5 = "I don''t know" or random answer',
 'Teach make-10 strategy: 7 + 5 = 7 + 3 + 2 = 10 + 2 = 12. Use ten-frame to visualise. Also: use 2 sets of hands (partner counting).',
 ARRAY['INT-OP-002'], 'moderate', 'common', 3),

('N1.3.2-M1', 'N1.3.2',
 'Subtracts smaller from larger regardless of order',
 'क्रम की परवाह किए बिना छोटे से बड़ा घटाता है',
 'For 3-7 or any problem where this is impossible, child reverses: computes 7-3=4',
 'When given impossible single-digit subtractions or mixed problems, child always does larger minus smaller',
 '8 - 3 = 5 (correct order)',
 'Given 5 - 8: writes 3 (computes 8-5)',
 'Use physical objects: "You have 5 blocks. Take away 8. Can you? No! You don''t have enough." Build understanding that subtraction has directionality.',
 ARRAY['INT-OP-003'], 'moderate', 'common', 1),


-- ============================================================================
-- GRADE 2: OPERATIONS MISCONCEPTIONS — the richest diagnostic territory
-- ============================================================================

-- N2.3.1: 2-digit addition without carry
('N2.3.1-M1', 'N2.3.1',
 'Column misalignment (adds ones to tens)',
 'स्तम्भ गड़बड़ (इकाई को दहाई में जोड़ना)',
 'Child does not align numbers by place value in vertical format, mixing columns',
 'Errors are random and inconsistent; when given pre-aligned problems on place-value grid, accuracy improves dramatically',
 '23 + 14: align 3+4=7 (ones), 2+1=3 (tens) → 37',
 '23 + 14: misaligned → adds 2+4=6, 3+1=4 → 64',
 'Always provide problems on place-value grid (T|O columns). Colour-code columns. Transition to self-drawn columns gradually.',
 ARRAY['INT-OP-004'], 'moderate', 'common', 1),

-- N2.3.2: 2-digit addition WITH carry — most common diagnostic target
('N2.3.2-M1', 'N2.3.2',
 'Place-value carry-over confusion: drops the carry',
 'हासिल भूलना: हासिल छोड़ देता है',
 'Child adds ones correctly but writes full sum in ones column and does not carry the tens digit',
 'Answer is exactly 10 less than correct. Ones column has a 2-digit number written, or only ones digit is written but tens carry is missing. Consistent across 3+ problems.',
 '34 + 28 = 62 (carry 1 to tens: 3+2+1=6)',
 '34 + 28 = 52 (4+8=12, writes 2, forgets to carry 1: 3+2=5)',
 'Re-teach with bundling sticks: "4 ones + 8 ones = 12 ones. But we can only keep 9 ones! Bundle 10 into a new ten. Write 2 ones, carry 1 ten." Use carry box above tens column.',
 ARRAY['INT-OP-005', 'INT-PV-001'], 'critical', 'very_common', 1),

('N2.3.2-M2', 'N2.3.2',
 'Writes full ones sum without carrying',
 'पूरा इकाई योग लिखना, हासिल न रखना',
 'Child writes the full 2-digit sum of ones in the ones column (e.g., writes 12 in ones place)',
 'Answer has 3 digits where 2 expected, or ones column shows 2 digits (e.g., 34+28 → 512 where ones shows 12)',
 '34 + 28 = 62',
 '34 + 28 = 512 (writes 12 in ones, 5 in tens)',
 'Teach: "Only ONE digit fits in each column. If the sum is 12, the 1 goes UP to the next column, the 2 stays." Physical demonstration with place-value pocket chart.',
 ARRAY['INT-OP-005'], 'critical', 'common', 2),

('N2.3.2-M3', 'N2.3.2',
 'Carries wrong digit',
 'गलत अंक हासिल रखना',
 'Child carries the ones digit instead of the tens digit (carries 2 instead of 1 from a sum of 12)',
 'Tens column is consistently 1 more than expected (double-carry effect)',
 '34 + 28: ones=12, carry 1, tens=3+2+1=6 → 62',
 '34 + 28: ones=12, carry 2, tens=3+2+2=7 → 72',
 'Colour-code: "In 12, the LEFT digit (1) goes UP, the RIGHT digit (2) stays DOWN." Practise with visible carry boxes.',
 ARRAY['INT-OP-005'], 'moderate', 'uncommon', 3),

('N2.3.2-M4', 'N2.3.2',
 'Adds left-to-right (tens first, then ones)',
 'बाएँ से दाएँ जोड़ना (पहले दहाई, फिर इकाई)',
 'Child adds tens column first, writes it, then adds ones but now cannot carry because tens is already written',
 'Tens digit is correct for no-carry scenario but wrong when carry is needed; child may cross out and rewrite',
 '34 + 28: ones first → 12 (write 2, carry 1) → tens: 3+2+1=6 → 62',
 '34 + 28: tens first → 3+2=5 → ones: 4+8=12... stuck or writes 512',
 'Teach and reinforce: "ALWAYS start from the ones (right side). इकाई से शुरू करो!" Use arrow on worksheet pointing right-to-left.',
 ARRAY['INT-OP-005'], 'moderate', 'common', 4),

-- N2.3.4: 2-digit subtraction with borrowing
('N2.3.4-M1', 'N2.3.4',
 'Smaller-from-larger reversal in ones column',
 'इकाई में छोटे से बड़ा घटाना (उल्टा)',
 'When ones digit of minuend < subtrahend, child subtracts smaller from larger (e.g., 42-17: does 7-2=5 in ones)',
 'In ones column, child always subtracts the smaller digit from the larger regardless of position. Tens column is unchanged (no borrowing attempted). Very common and persistent.',
 '42 - 17 = 25 (borrow: 12-7=5, 3-1=2)',
 '42 - 17 = 35 (ones: 7-2=5, tens: 4-1=3 — no borrow)',
 'Use concrete: "You have 2 ones. Can you take away 7? No! You need to break a ten." Physical demonstration with bundling sticks: unbundle 1 ten into 10 ones.',
 ARRAY['INT-OP-006', 'INT-PV-001'], 'critical', 'very_common', 1),

('N2.3.4-M2', 'N2.3.4',
 'Borrows but does not reduce tens digit',
 'उधार लेता है पर दहाई कम नहीं करता',
 'Child correctly adds 10 to ones digit and subtracts, but does not reduce the tens digit by 1',
 'Answer is exactly 10 more than correct. Ones column is right, tens column is 1 too high.',
 '42 - 17 = 25 (ones: 12-7=5, tens: 3-1=2)',
 '42 - 17 = 35 (ones: 12-7=5 ✓, tens: 4-1=3 — forgot to reduce 4 to 3)',
 'Teach as two-step: "Step 1: Cross out 4, write 3 above it. Step 2: Write 12 in ones column." Make crossing-out the tens digit a physical, required step.',
 ARRAY['INT-OP-006'], 'critical', 'common', 2),

('N2.3.4-M3', 'N2.3.4',
 'Borrows when not needed',
 'ज़रूरत न होने पर भी उधार लेना',
 'Child borrows even when ones digit of minuend ≥ subtrahend',
 'Errors on problems that do NOT require borrowing but are presented mixed with borrowing problems; no-borrow problems now get wrong answers',
 '48 - 13 = 35 (no borrow needed: 8-3=5, 4-1=3)',
 '48 - 13 = 45 (borrows unnecessarily: 18-3=15? or similar confusion)',
 'Teach the CHECK first: "Look at the ones. Top bigger or smaller? If top is bigger, just subtract! If top is smaller, THEN borrow." Use colour-coding: green = no borrow, red = borrow.',
 ARRAY['INT-OP-006'], 'moderate', 'common', 3),

-- N2.3.5: Word problems
('N2.3.5-M1', 'N2.3.5',
 'Operation selection error: adds when should subtract',
 'संक्रिया चयन त्रुटि: घटाने की बजाय जोड़ता है',
 'Child always adds regardless of problem context — does not distinguish additive from subtractive situations',
 'Computation is correct but operation is wrong; "gave away" / "ate" / "lost" problems are solved with addition',
 '"Ram had 45 mangoes, gave 18 to Sita. How many left?" → 45 - 18 = 27',
 '"Ram had 45 mangoes, gave 18 to Sita. How many left?" → 45 + 18 = 63',
 'Teach keyword strategy with caution (keywords can mislead). Better: act out with objects. "Ram HAD 45. Then he GAVE AWAY. Did he end up with more or less? Less = subtract."',
 ARRAY['INT-WP-001'], 'moderate', 'very_common', 1),

('N2.3.5-M2', 'N2.3.5',
 'Correct operation but cannot compute',
 'सही संक्रिया पर गणना में त्रुटि',
 'Child selects the right operation but makes procedural errors in computation',
 'Operation symbol is correct, but answer is wrong due to carry/borrow errors — diagnose the underlying operation misconception',
 NULL, NULL,
 'This is a COMPOUND misconception — trace to the specific operation error (N2.3.2-M* or N2.3.4-M*) and address that.',
 ARRAY['INT-OP-005', 'INT-OP-006'], 'moderate', 'common', 2),


-- ============================================================================
-- GRADE 2: PLACE VALUE (3-digit) MISCONCEPTIONS
-- ============================================================================

('N2.2.2-M1', 'N2.2.2',
 'Zero in middle causes confusion (e.g., 305)',
 'बीच में शून्य से भ्रम (जैसे 305)',
 'Child cannot handle numbers with 0 in tens place — writes 35 instead of 305, or says "three hundred five" = 350',
 'Errors concentrated on numbers with internal zero; other 3-digit numbers are fine',
 '305 = 300 + 0 + 5 = "three hundred five"',
 '305 → writes as 35, or expanded form: 300 + 50',
 'Use place-value chart with explicit zero: H|T|O = 3|0|5. "Zero tens means NO tens. The zero holds the place." Physical: 3 hundred-flats, 0 ten-rods, 5 unit-cubes.',
 ARRAY['INT-PV-003'], 'critical', 'very_common', 1),

('N2.2.2-M2', 'N2.2.2',
 'Expanded form errors: confuses face value and place value',
 'विस्तारित रूप में त्रुटि: अंकित मान और स्थानीय मान में भ्रम',
 'Child writes 345 = 3 + 4 + 5 instead of 300 + 40 + 5',
 'Expanded form consistently uses face values not place values; but child can read the number correctly',
 '345 = 300 + 40 + 5',
 '345 = 3 + 4 + 5',
 'Rebuild with money: 345 rupees = three 100-rupee notes + four 10-rupee notes + five 1-rupee coins. "Is four 10-rupee notes worth 4 rupees or 40 rupees?"',
 ARRAY['INT-PV-003', 'INT-PV-001'], 'critical', 'common', 2),


-- ============================================================================
-- GRADE 3: OPERATIONS MISCONCEPTIONS
-- ============================================================================

-- N3.3.1: 3-digit addition
('N3.3.1-M1', 'N3.3.1',
 'Single carry works but double carry fails',
 'एक हासिल सही पर दोहरे हासिल में गलती',
 'Child handles carry from ones to tens but not the second carry from tens to hundreds',
 'Problems with carry in ones only are correct; problems with carry in both ones AND tens are wrong — tens-to-hundreds carry is dropped',
 '167 + 245 = 412 (carry from ones AND tens)',
 '167 + 245 = 312 (carries ones→tens ✓, but drops tens→hundreds: 6+4+1=11, writes 1, forgets carry)',
 'Practise with explicit carry boxes above EVERY column. Make the check: "Is my column sum ≥ 10? Then carry!" applicable to EVERY column, not just ones.',
 ARRAY['INT-OP-005'], 'critical', 'common', 1),

-- N3.3.3: Multiplication tables
('N3.3.3-M1', 'N3.3.3',
 'Confuses adjacent table facts',
 'पास-पास के तथ्यों में भ्रम',
 'Child recalls nearby facts instead of the correct one: says 6×7=48 (which is 6×8) or 7×8=54 (which is 6×9)',
 'Errors are within ±1 of the correct product when interpreted as an adjacent fact in the same table',
 '6 × 7 = 42',
 '6 × 7 = 48 (recalls 6×8)',
 'Use commutative pairs and anchors: "I know 6×6=36, so 6×7 is one more 6 = 42." Build from known facts rather than rote sequential recitation.',
 ARRAY['INT-OP-007'], 'moderate', 'very_common', 1),

('N3.3.3-M2', 'N3.3.3',
 'Tables known sequentially but not randomly',
 'क्रम में याद पर बेतरतीब में नहीं',
 'Child can recite "2, 4, 6, 8..." but cannot answer "2×7=?" without reciting from 2×1',
 'Fast when asked in sequence, very slow or incorrect when asked out of order',
 '7 × 4 = 28 (instant recall)',
 '7 × 4 → recites "7, 14, 21, 28" → takes 8+ seconds',
 'Flash card drills in random order. Timed games. Focus on deriving facts: "7×4 = 7×2×2 = 14×2 = 28" — build flexibility, not just sequence.',
 ARRAY['INT-OP-007'], 'moderate', 'common', 2),

-- N3.3.4: 2-digit × 1-digit multiplication
('N3.3.4-M1', 'N3.3.4',
 'Multiplies each digit independently without carrying',
 'प्रत्येक अंक को अलग-अलग गुणा करना, हासिल के बिना',
 'Child multiplies ones and tens digits separately: 23 × 4 → 2×4=8, 3×4=12 → writes 812 or 82',
 'Answer structure looks like concatenation of two separate products rather than proper column multiplication',
 '23 × 4 = 92 (3×4=12, write 2 carry 1; 2×4=8+1=9)',
 '23 × 4 = 812 (3×4=12, 2×4=8, concatenates)',
 'Teach column method: ones first, carry to tens. Use grid/box method as visual scaffold: 23×4 = (20×4) + (3×4) = 80 + 12 = 92.',
 ARRAY['INT-OP-008'], 'critical', 'common', 1),

('N3.3.4-M2', 'N3.3.4',
 'Adds instead of multiplying one digit',
 'एक अंक का गुणा करने की बजाय जोड़ना',
 'Child multiplies one digit but adds the other: 23 × 4 → 3×4=12, but then does 2+4=6 instead of 2×4=8',
 'Ones column is correct (multiplied) but tens result looks like addition rather than multiplication',
 '23 × 4: tens: 2×4=8 (+carry)',
 '23 × 4: tens: 2+4=6 (+carry)',
 'Reinforce: "We multiply EVERY digit by 4, not just the ones. × means multiply. Write the × symbol next to each partial product step."',
 ARRAY['INT-OP-008'], 'moderate', 'common', 2),

-- N3.3.5: Division
('N3.3.5-M1', 'N3.3.5',
 'Confuses division with subtraction',
 'भाग को घटाव समझना',
 'Child subtracts the divisor from dividend instead of dividing: 24 ÷ 6 → 24 - 6 = 18',
 'Answer equals dividend minus divisor consistently',
 '24 ÷ 6 = 4',
 '24 ÷ 6 = 18 (subtracted)',
 'Reframe with sharing: "24 toffees shared among 6 friends. Each friend gets how many? NOT how many are left." Use physical distribution.',
 ARRAY['INT-OP-009'], 'critical', 'common', 1),

('N3.3.5-M2', 'N3.3.5',
 'Cannot handle remainders',
 'शेषफल संभाल नहीं पाता',
 'Child gives wrong answer or no answer when division is not exact',
 'Correct for exact divisions (24÷6=4) but wrong/blank for inexact (25÷6)',
 '25 ÷ 6 = 4 remainder 1',
 '25 ÷ 6 = "cannot do" or 5 (rounds up)',
 'Use sharing story: "25 toffees, 6 friends. Give 4 each (4×6=24). 1 left over — that is the remainder. It is LESS than 6 so we cannot give any more."',
 ARRAY['INT-OP-009'], 'moderate', 'common', 2),

-- N3.3.6: Multi-step word problems
('N3.3.6-M1', 'N3.3.6',
 'Performs only one step',
 'केवल एक चरण करता है',
 'Child identifies and performs the first operation but stops — does not recognise that a second step is needed',
 'Answer matches the result of only the first operation; no evidence of second step attempted',
 '"Bought 3 packs of 12 pencils, gave away 8. How many left?" → 3×12=36, 36-8=28',
 'Answer: 36 (only did 3×12, stopped)',
 'Teach: underline the QUESTION. "How many LEFT?" means you need a final subtraction. Break into sub-questions: "Step 1: How many total? Step 2: How many after giving away?"',
 ARRAY['INT-WP-002'], 'moderate', 'very_common', 1),

-- N3.5.2: Perimeter
('N3.5.2-M1', 'N3.5.2',
 'Adds only 2 sides for rectangle perimeter',
 'आयत का परिमाप: केवल 2 भुजाएँ जोड़ना',
 'Child adds length + width instead of 2×(length + width)',
 'Answer is exactly half the correct perimeter',
 'Rectangle 5cm × 3cm: perimeter = 2×(5+3) = 16 cm',
 'Rectangle 5cm × 3cm: perimeter = 5+3 = 8 cm',
 'Walk around the shape with finger: "Count ALL sides. Rectangle has 4 sides: 5, 3, 5, 3. Add all four." Then introduce formula as shortcut.',
 ARRAY['INT-GE-001'], 'moderate', 'common', 1);
