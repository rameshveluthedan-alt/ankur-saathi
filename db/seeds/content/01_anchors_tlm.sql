-- ============================================================================
-- ANKUR SAATHI — Layer 2 Seed: Anchor Activities + TLM References
-- ============================================================================

-- ============================================================================
-- TLM REFERENCES (needed first — anchors and interventions reference these)
-- ============================================================================

INSERT INTO tlm_references (id, name_en, name_hi, description_en, domain_ids, competency_ids, availability, diy_instructions) VALUES

('TLM-001', 'Bundling sticks', 'बंडल की छड़ियाँ',
 'Sets of 10 sticks bundled with rubber bands for place value. Single sticks as ones, bundles as tens. Mainly the teacher''s demonstration; children handle sticks only in the Beginner group, in pairs.',
 ARRAY['numeracy'], ARRAY['N1.2.4','N2.2.2','N2.3.2','N2.3.4'], 'diy',
 'Collect thin sticks or straws and bundle groups of 10 with rubber bands BEFORE class; children never bundle during the lesson. Teacher demo kit: 9 bundles + 9 loose sticks (99 sticks). Beginner pair kit: 4 bundles + 9 loose sticks (49 sticks) for each pair, kept in a bag or box. Rule a Tens | Ones frame on a sheet or the notebook cover. Count the sticks back in at the end. Other groups draw tens as lines and ones as dots instead of using sticks.'),

('TLM-002', 'Number chart 1-100', 'संख्या चार्ट 1-100',
 'Wall chart showing numbers 1-100 in a 10×10 grid. For counting, patterns, and number recognition.',
 ARRAY['numeracy'], ARRAY['N1.2.1','N1.2.3','N2.2.4'], 'common', NULL),

('TLM-003', 'Letter chart (varnamala)', 'वर्णमाला चार्ट',
 'Wall chart showing all Hindi vowels and consonants with associated pictures.',
 ARRAY['r1_literacy'], ARRAY['L0.3.1','L1.3.1'], 'common', NULL),

('TLM-004', 'Matra chart', 'मात्रा चार्ट',
 'Chart showing all matras with example words for each. Shows matra position relative to consonant.',
 ARRAY['r1_literacy'], ARRAY['L1.3.2','L1.3.3','L1.7.2'], 'common',
 'Draw on chart paper: each row shows the vowel, its matra form, position (before/after/above/below), and 3 example words.'),

('TLM-005', 'Place value pocket chart', 'स्थानीय मान पॉकेट चार्ट',
 'Chart with H/T/O columns and pockets where number cards can be inserted to show decomposition.',
 ARRAY['numeracy'], ARRAY['N1.2.4','N2.2.2','N3.2.2'], 'uncommon',
 'Make from cardboard: 3 columns labelled H|T|O. Cut slits below each label to insert number cards (0-9).'),

('TLM-006', 'Coins and notes (play money)', 'खिलौने के सिक्के और नोट',
 'Replica Indian currency for money-related activities.',
 ARRAY['numeracy'], ARRAY['N2.4.3'], 'diy',
 'Print denominations on card stock: ₹1, ₹2, ₹5, ₹10, ₹20, ₹50, ₹100. Children can cut and colour.'),

('TLM-007', 'Flash cards (numbers)', 'फ्लैश कार्ड (संख्या)',
 'Cards with numerals on one side, quantity representation (dots/objects) on the other.',
 ARRAY['numeracy'], ARRAY['N0.2.3','N1.2.3','N3.3.3'], 'diy',
 'Cut card stock into playing-card size. Write numeral on front, draw that many dots on back.'),

('TLM-008', 'Flash cards (letters/words)', 'फ्लैश कार्ड (अक्षर/शब्द)',
 'Cards with Hindi letters or sight words for rapid recognition drills.',
 ARRAY['r1_literacy'], ARRAY['L0.3.1','L1.3.1','L1.4.1','L2.4.2'], 'diy',
 'Cut card stock. Write one letter or word per card in large, clear Devanagari.'),

('TLM-009', 'Ruler (30 cm)', '30 सेमी पट्टी',
 'Standard ruler for length measurement activities.',
 ARRAY['numeracy'], ARRAY['N3.4.1'], 'common', NULL),

('TLM-010', 'Blackboard/whiteboard', 'श्यामपट्ट/श्वेतपट्ट',
 'Available in every classroom. Used for demonstrations, board-copy worksheets, and group work display.',
 ARRAY['numeracy','r1_literacy'], NULL, 'universal', NULL),

('TLM-011', 'Ten-frame cards', 'दस-फ्रेम कार्ड',
 '2×5 grid cards for visualising numbers to 10 and the make-10 addition strategy.',
 ARRAY['numeracy'], ARRAY['N1.3.1','N0.2.2'], 'diy',
 'Draw a 2×5 grid on card stock (each cell ~3cm). Children place counters (stones, seeds) in the frames.'),

('TLM-012', 'Story picture cards', 'कहानी चित्र कार्ड',
 'Sequencing cards with 4-6 pictures from a story, for comprehension and narration activities.',
 ARRAY['r1_literacy'], ARRAY['L0.1.3','L1.6.2'], 'diy',
 'Draw or print 4-6 scenes from a familiar story on separate cards. Children arrange in order and narrate.');


-- ============================================================================
-- ANCHOR ACTIVITIES — Numeracy
-- Each template has {{placeholders}} Claude fills with day-specific content
-- ============================================================================

INSERT INTO anchor_activities (id, title_en, title_hi, description_en, template_body, primary_competency_ids, secondary_competency_ids, domain_id, grade_range, duration_minutes, theme, setting, requires_tlm, tlm_ids, source) VALUES

('ANC-N-001', 'Village Market Story', 'गाँव का बाज़ार',
 'A shared story about buying items at a market. Beginners count items, Progressors add prices, Proficients calculate totals with carry.',
 'Story setup (teacher narrates):
"आज हम बाज़ार जाएंगे। {{story_character}} को अपनी माँ के लिए सामान खरीदना है।"

Whole-class moment: Teacher shows/draws market items on board with prices.

Differentiated participation:
- Beginners ({{beginner_task}}): "बाज़ार में कितनी चीज़ें हैं? गिनो!" — Count the items on the board. Practice {{beginner_competency_name}}.
- Progressors ({{progressor_task}}): "{{story_character}} ने {{item_1}} और {{item_2}} खरीदा। कुल कितने पैसे लगे?" — Add prices. Practice {{progressor_competency_name}}.
- Proficients ({{proficient_task}}): "{{story_character}} के पास {{total_amount}} रुपये हैं। {{item_1}}, {{item_2}} और {{item_3}} खरीदने के बाद कितने बचे?" — Multi-step. Practice {{proficient_competency_name}}.

Closing (whole class): "सबसे महँगी चीज़ कौन सी थी? सबसे सस्ती?"',
 ARRAY['N2.3.1','N2.3.2'], ARRAY['N1.3.1','N1.2.4','N2.3.5'],
 'numeracy', ARRAY['grade_1','grade_2','grade_3'], 10,
 'market', 'universal', FALSE, NULL, 'original'),

('ANC-N-002', 'Sharing Rotis', 'रोटी बाँटना',
 'A story about equal sharing at mealtime. Introduces division concept through fair distribution.',
 'Story setup:
"{{story_character}} की माँ ने {{total_rotis}} रोटियाँ बनाईं। परिवार में {{family_members}} लोग हैं।"

Whole-class question: "सबको बराबर-बराबर मिलें तो हर किसी को कितनी?"

Differentiated participation:
- Beginners ({{beginner_task}}): Count the rotis drawn on board. Practice 1:1 correspondence. "कुल कितनी रोटियाँ हैं?"
- Progressors ({{progressor_task}}): Use objects (stones/seeds) to physically distribute. "{{total_rotis}} रोटियाँ {{family_members}} लोगों में बाँटो।"
- Proficients ({{proficient_task}}): "अगर {{extra_rotis}} रोटियाँ और बन जाएँ तो? अब कितनी-कितनी?" — Division with different dividends.

Closing: "क्या हमेशा बराबर-बराबर बँट जाती हैं? जब न बँटें तो?"',
 ARRAY['N3.3.5'], ARRAY['N0.2.2','N2.3.6','N3.3.3'],
 'numeracy', ARRAY['grade_1','grade_2','grade_3'], 10,
 'kitchen', 'rural', FALSE, NULL, 'original'),

('ANC-N-003', 'Train Journey', 'रेलगाड़ी की यात्रा',
 'Children at stations board/exit a train. Addition as joining, subtraction as leaving.',
 'Story setup:
"एक रेलगाड़ी चली। पहले स्टेशन पर {{station_1_board}} लोग चढ़े।"

Teacher draws train on board, updates passenger count at each station.

Differentiated participation:
- Beginners: "ट्रेन में अभी कितने लोग हैं?" — Count at each stop.
- Progressors: "{{station_name}} पर {{board}} चढ़े और {{exit}} उतरे। अब कितने?" — Addition/subtraction within numbers they can handle.
- Proficients: "पूरी यात्रा में कुल कितने लोग चढ़े? कितने उतरे? फ़र्क कितना?" — Multi-step tracking.

Closing: Compare predictions vs actual final count.',
 ARRAY['N1.3.1','N1.3.2'], ARRAY['N2.3.1','N2.3.3','N1.3.3'],
 'numeracy', ARRAY['grade_1','grade_2'], 10,
 'travel', 'universal', FALSE, NULL, 'original'),

('ANC-N-004', 'Place Value Treasure Hunt', 'स्थानीय मान खज़ाना खोज',
 'Teacher announces a "secret number" — children decode it using place value clues.',
 'Setup: Teacher writes clues on board (or speaks them).

"मेरे पास एक गुप्त संख्या है!"
Clue 1: "इसमें {{tens_clue}} दहाइयाँ हैं" 
Clue 2: "इसमें {{ones_clue}} इकाइयाँ हैं"
Clue 3 (for 3-digit): "इसमें {{hundreds_clue}} सैकड़े हैं"

Differentiated participation:
- Beginners: Decode 2-digit numbers from clues. Build with bundling sticks.
- Progressors: Decode 2-digit, write expanded form: {{number}} = {{tens_value}} + {{ones_value}}
- Proficients: Decode 3-digit numbers. "मेरी संख्या से 10 ज़्यादा क्या होगा? 100 ज़्यादा?"

Closing: Children make their own secret number clues for a partner.',
 ARRAY['N1.2.4','N2.2.2'], ARRAY['N1.2.3','N2.2.1','N3.2.2'],
 'numeracy', ARRAY['grade_1','grade_2','grade_3'], 10,
 'school', 'universal', TRUE, ARRAY['TLM-001','TLM-005'], 'original'),

('ANC-N-005', 'Seed Counting on the Farm', 'खेत में बीज गिनती',
 'A farming story for counting, grouping by 10s, and multiplication as repeated groups.',
 'Story setup:
"{{story_character}} के खेत में बुआई का समय है। हर कतार में {{seeds_per_row}} बीज डालने हैं।"

Whole-class moment: Draw rows on board. Fill first row together.

Differentiated participation:
- Beginners: "एक कतार में बीज गिनो" — Counting to 10/20.
- Progressors: "{{num_rows}} कतारें हैं, हर कतार में {{seeds_per_row}} बीज। कुल कितने?" — Repeated addition / skip counting.
- Proficients: "{{num_rows}} × {{seeds_per_row}} = ?" — Multiplication. "अगर {{extra_rows}} कतारें और जोड़ दें तो?"

Closing: "किसान बीजों को 10-10 के बंडल में क्यों गिनता है?"',
 ARRAY['N2.3.6','N3.3.3'], ARRAY['N0.2.2','N1.2.2','N2.2.4'],
 'numeracy', ARRAY['grade_1','grade_2','grade_3'], 10,
 'farm', 'rural', FALSE, NULL, 'original'),

('ANC-N-006', 'Shape Hunt in the Classroom', 'कक्षा में आकृति खोज',
 'Children identify 2D and 3D shapes in real classroom objects. Counts sides and corners.',
 'Setup: "आज हम कक्षा में आकृतियाँ खोजेंगे!"

Round 1 (whole class): Teacher points to objects. "खिड़की कौन सी आकृति है?" (Rectangle)

Differentiated participation:
- Beginners: Find and name basic shapes — circle, square, triangle, rectangle.
- Progressors: Count sides and corners. "दरवाज़ा — कितनी भुजाएँ? कितने कोने?"
- Proficients: Find 3D shapes. "गेंद — गोला। डिब्बा — घन। क्या फ़र्क है 2D और 3D में?"

Closing: Each group shares their best find.',
 ARRAY['N0.5.1','N1.5.1'], ARRAY['N1.5.2'],
 'numeracy', ARRAY['balvatika','grade_1','grade_2'], 10,
 'school', 'universal', FALSE, NULL, 'original'),

('ANC-N-007', 'Festival Sweet Box', 'त्योहार की मिठाई',
 'Packing sweets into boxes for a festival. Multiplication, division, and money calculations.',
 'Story setup:
"दीवाली आ रही है! {{story_character}} की दुकान पर मिठाई पैक करनी है।"

Whole-class: "हर डिब्बे में {{sweets_per_box}} मिठाइयाँ आती हैं।"

Differentiated participation:
- Beginners: "एक डिब्बे में {{sweets_per_box}} मिठाइयाँ गिनो और रखो" — Counting.
- Progressors: "{{num_boxes}} डिब्बे भरने हैं। कुल कितनी मिठाइयाँ चाहिए?" — Multiplication.
- Proficients: "{{total_sweets}} मिठाइयाँ हैं, {{sweets_per_box}} के डिब्बों में पैक करो। कितने डिब्बे बनेंगे? कितनी बचेंगी?" — Division with remainder.

Closing: "हर डिब्बे की कीमत {{price}} रुपये है। {{num_boxes}} डिब्बों के कितने पैसे?"',
 ARRAY['N3.3.3','N3.3.5'], ARRAY['N2.3.6','N3.3.4','N3.3.6'],
 'numeracy', ARRAY['grade_2','grade_3'], 10,
 'festival', 'universal', FALSE, NULL, 'original'),

('ANC-N-008', 'Measuring the Classroom', 'कक्षा को मापना',
 'Children measure classroom objects using handspans, then rulers. Connects non-standard to standard.',
 'Setup: "आज हम अपनी कक्षा की चीज़ें मापेंगे!"

Round 1 (whole class): "अपनी मेज़ कितने बित्ते लंबी है?" Everyone measures.

Differentiated participation:
- Beginners: Measure 3 objects using handspans. "कौन सी सबसे लंबी?"
- Progressors: Measure same objects with ruler. "बित्ते में {{handspan_count}}, सेमी में कितनी?"
- Proficients: "कमरे की लंबाई मीटर और सेमी में मापो। मीटर में बदलो।"

Closing: "बित्ते से मापने में क्या दिक्कत है? पट्टी से क्यों बेहतर है?"',
 ARRAY['N2.4.1','N3.4.1'], ARRAY['N1.4.1'],
 'numeracy', ARRAY['grade_1','grade_2','grade_3'], 10,
 'school', 'universal', TRUE, ARRAY['TLM-009'], 'original');


-- ============================================================================
-- ANCHOR ACTIVITIES — R1 Literacy (Hindi)
-- ============================================================================

INSERT INTO anchor_activities (id, title_en, title_hi, description_en, template_body, primary_competency_ids, secondary_competency_ids, domain_id, grade_range, duration_minutes, theme, setting, requires_tlm, tlm_ids, source) VALUES

('ANC-L-001', 'Story Time: What Happens Next?', 'कहानी का समय: आगे क्या होगा?',
 'Teacher reads a story aloud, pauses at a key moment. All levels engage with prediction and comprehension.',
 'Setup: Teacher reads a short story aloud with expression, showing pictures if available.

Story: "{{story_title}}" — read until the turning point.

Pause: "अब क्या होगा? सोचो!"

Differentiated participation:
- Beginners: "कहानी में कौन-कौन था?" — Name characters (oral). "{{character}} ने क्या किया?" — Literal recall.
- Progressors: "आगे क्या होगा?" — Predict next event. "ऐसा क्यों सोचते हो?" — Give reason.
- Proficients: "अगर तुम {{character}} होते तो क्या करते?" — Inferential. "कहानी का संदेश क्या है?" — Main idea.

Teacher reads the ending. Compare predictions.

Closing: "किसका अनुमान सबसे करीब था? क्यों?"',
 ARRAY['L1.6.1','L2.6.2','L2.6.3'], ARRAY['L0.1.3','L3.6.1','L3.6.3'],
 'r1_literacy', ARRAY['grade_1','grade_2','grade_3'], 10,
 'school', 'universal', FALSE, NULL, 'original'),

('ANC-L-002', 'Sound Safari', 'ध्वनि सफ़ारी',
 'A phonological awareness game. Teacher says a sound, children find words starting with it.',
 'Setup: "आज हम ध्वनि खोजेंगे!"

Round 1 (whole class): Teacher says "क" — everyone finds classroom objects starting with क (कुर्सी, किताब, कलम).

Differentiated participation:
- Beginners: Find objects starting with {{target_sound}}. Point and say the word. Clap the syllables.
- Progressors: "{{target_sound}} से शुरू होने वाले 5 शब्द बोलो।" Write them with matras.
- Proficients: "{{target_sound}} बीच में आने वाले शब्द बताओ।" — Medial sound identification. Write sentences using those words.

Closing: Each group shares their best word. Class votes on the most creative one.',
 ARRAY['L0.2.3','L1.2.1'], ARRAY['L0.2.1','L0.2.2','L1.3.4'],
 'r1_literacy', ARRAY['balvatika','grade_1'], 10,
 'school', 'universal', FALSE, NULL, 'original'),

('ANC-L-003', 'Matra Magic', 'मात्रा का जादू',
 'Shows how changing the matra changes the word meaning. Minimal pairs for matra awareness.',
 'Setup: Write a base consonant cluster on the board: "कल"

"देखो, एक ही शब्द में अलग-अलग मात्रा लगाएँ तो क्या होता है!"

Whole-class demonstration:
कल (tomorrow) → काल (time/era) → कील (nail) → कूल (cool) → केला (banana) → कैसा (how)

Differentiated participation:
- Beginners: Read each word with teacher. "कौन सी मात्रा लगी?" — Identify the matra.
- Progressors: New base word: "{{base_word}}". Add different matras. Write the new words. "अर्थ बदल गया!"
- Proficients: "अपना base शब्द चुनो। कम से कम 4 मात्राएँ लगाकर नए शब्द बनाओ और वाक्य में प्रयोग करो।"

Closing: Share the funniest meaning change.',
 ARRAY['L1.3.2','L1.3.3'], ARRAY['L1.7.2','L1.4.2'],
 'r1_literacy', ARRAY['grade_1','grade_2'], 10,
 'school', 'universal', TRUE, ARRAY['TLM-004'], 'original'),

('ANC-L-004', 'Letter from a Friend', 'दोस्त का पत्र',
 'Teacher reads a letter aloud. Children respond at their level — from listening comprehension to writing back.',
 'Setup: Teacher reads a "letter" from a fictional child:

"प्रिय कक्षा,
मेरा नाम {{character_name}} है। मैं {{place}} में रहता/रहती हूँ। {{2_3_sentences_about_their_life}}
तुम्हारा दोस्त/सहेली, {{character_name}}"

Differentiated participation:
- Beginners: "{{character_name}} कहाँ रहता/रहती है?" — Literal questions (oral). Teacher writes answers on board.
- Progressors: "{{character_name}} को जवाब लिखो — 3 वाक्य।" — Sentence writing with matras.
- Proficients: "{{character_name}} को 5-7 वाक्यों का पत्र लिखो। अपने बारे में बताओ। पत्र का सही ढाँचा (प्रिय, अंत में नाम)।"

Closing: 2-3 children read their letters aloud.',
 ARRAY['L1.6.1','L2.7.2','L3.7.3'], ARRAY['L1.7.3','L3.7.1'],
 'r1_literacy', ARRAY['grade_1','grade_2','grade_3'], 10,
 'school', 'universal', FALSE, NULL, 'original'),

('ANC-L-005', 'Picture Story Sequencing', 'चित्र कहानी क्रम',
 'Four pictures from a story shown out of order. Children sequence and narrate.',
 'Setup: Display 4 story pictures on the board in jumbled order.

"ये चित्र एक कहानी के हैं, पर गलत क्रम में हैं!"

Whole-class: "पहले कौन सा चित्र आएगा? क्यों?"

Differentiated participation:
- Beginners: Arrange 3 pictures in order. Tell what happens in each (oral, 1-2 words per picture).
- Progressors: Arrange all 4 pictures. Write 1 sentence for each picture.
- Proficients: Arrange, write a full paragraph (5+ sentences) telling the story. Add "फिर," "उसके बाद," "अंत में" connectors.

Closing: One child narrates the complete story while teacher points to pictures.',
 ARRAY['L0.1.3','L1.6.2'], ARRAY['L1.7.3','L2.7.2','L3.7.1'],
 'r1_literacy', ARRAY['balvatika','grade_1','grade_2','grade_3'], 10,
 'school', 'universal', TRUE, ARRAY['TLM-012'], 'original'),

('ANC-L-006', 'Tongue Twister Challenge', 'जीभ का कसरत',
 'Hindi tongue twisters for fluency and phonological awareness. Fun competitive format.',
 'Setup: Teacher writes/reads a tongue twister:
"{{tongue_twister}}"

Round 1: Teacher reads slowly. Class repeats.
Round 2: Faster. Class repeats.
Round 3: Each group tries without the board.

Differentiated participation:
- Beginners: Repeat the tongue twister (oral). Identify repeated sounds: "कौन सी आवाज़ बार-बार आ रही है?"
- Progressors: Read the tongue twister from board. Circle the repeated letter/matra. Try to say it 3 times fast.
- Proficients: Write their own mini tongue twister using {{target_sound}}. Read it to the class.

Closing: Vote for the hardest tongue twister.',
 ARRAY['L0.2.1','L2.5.1'], ARRAY['L1.2.1','L1.5.1','L3.5.2'],
 'r1_literacy', ARRAY['grade_1','grade_2','grade_3'], 10,
 'school', 'universal', FALSE, NULL, 'original');


-- Populate search_text for all anchors (keyword search without embeddings)
UPDATE anchor_activities SET search_text = to_tsvector('simple',
    coalesce(title_en,'') || ' ' || coalesce(description_en,'') || ' ' || 
    coalesce(theme,'') || ' ' || coalesce(setting,'') || ' ' ||
    array_to_string(primary_competency_ids, ' ') || ' ' ||
    coalesce(array_to_string(secondary_competency_ids, ' '), '')
);

UPDATE tlm_references SET search_text = to_tsvector('simple',
    name_en || ' ' || description_en || ' ' || array_to_string(domain_ids, ' ')
);
