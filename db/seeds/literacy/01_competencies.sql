-- ============================================================================
-- ANKUR SAATHI — Layer 1 KB: R1 Literacy (Hindi) Competency Tree Seed Data
-- Part 1: Domain, Subdomains, Competencies (with A/PA/NA criteria)
-- ============================================================================
-- Coding scheme: L{grade}.{subdomain}.{sequence}
--   Grade: 0=Balvatika, 1=Grade 1, 2=Grade 2, 3=Grade 3
--   Subdomain: 1=oral_language, 2=phonological_awareness, 3=decoding,
--              4=word_reading, 5=reading_fluency, 6=comprehension, 7=writing
--
-- Hindi-specific: matras (vowel signs), conjunct consonants (संयुक्त अक्षर),
--   chandrabindu/anusvar/visarg, halant — each is a distinct decoding milestone.
-- Assessment modality follows NIPUN/EGRA norms: early literacy is predominantly
--   oral/observed, writing assessed via worksheets, fluency via oral reading.
-- ============================================================================

-- ========================
-- DOMAIN
-- ========================
INSERT INTO domains (id, name_en, name_hi, sort_order) VALUES
('r1_literacy', 'R1 Literacy (Hindi)', 'R1 साक्षरता (हिंदी)', 2);

-- ========================
-- SUBDOMAINS
-- ========================
INSERT INTO subdomains (id, domain_id, name_en, name_hi, description, sort_order) VALUES
('lit_oral_language',   'r1_literacy', 'Oral Language',             'मौखिक भाषा',         'Listening comprehension, speaking in sentences, vocabulary, narration — the foundation all literacy builds on', 1),
('lit_phonological',    'r1_literacy', 'Phonological Awareness',    'ध्वनि जागरूकता',      'Rhyming, syllable segmentation, phoneme identification — sound-level skills before letter mapping', 2),
('lit_decoding',        'r1_literacy', 'Decoding (Akshar Gyan)',    'डिकोडिंग (अक्षर ज्ञान)', 'Letter recognition, matra (vowel signs), conjunct consonants, chandrabindu/anusvar — mapping symbols to sounds', 3),
('lit_word_reading',    'r1_literacy', 'Word Reading',              'शब्द पठन',            'Sight words, decoded words, multi-syllable words — building automatic word recognition', 4),
('lit_fluency',         'r1_literacy', 'Reading Fluency',           'पठन प्रवाह',           'Connected text reading speed, accuracy, prosody — measured in CWPM', 5),
('lit_comprehension',   'r1_literacy', 'Reading Comprehension',     'पठन बोध',             'Literal recall, main idea, inference, prediction, summarisation — understanding what is read', 6),
('lit_writing',         'r1_literacy', 'Writing',                   'लेखन',                'Letter formation, word writing with matras, sentence and paragraph composition', 7);


-- ============================================================================
-- COMPETENCIES — BALVATIKA
-- Focus: oral language foundation, phonological awareness onset, letter exposure
-- ============================================================================

INSERT INTO competencies (id, subdomain_id, name_en, name_hi, grade_level, sort_order, assessment_modality, apna_criteria, number_range, problem_types) VALUES

-- === Oral Language (Balvatika) ===
('L0.1.1', 'lit_oral_language',
 'Listens to and follows 2-step instructions',
 'दो-चरणीय निर्देश सुनकर उनका पालन करता है',
 'balvatika', 1, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Follows 2-step instructions correctly on first attempt (e.g., pick up the book AND put it on the shelf)"},
   "partially_achieved": {"description": "Follows 1 step but forgets or confuses the second, or needs repetition"},
   "not_achieved": {"description": "Cannot follow even single-step instructions consistently"}
 }'::jsonb, NULL, NULL),

('L0.1.2', 'lit_oral_language',
 'Speaks in complete sentences of 4+ words',
 '4 या अधिक शब्दों के पूर्ण वाक्य बोलता है',
 'balvatika', 2, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Consistently uses 4+ word sentences with subject-verb structure when responding or narrating"},
   "partially_achieved": {"description": "Uses 2-3 word phrases; occasional complete sentences when prompted"},
   "not_achieved": {"description": "Responds in single words or gestures; does not form sentences"}
 }'::jsonb, NULL, NULL),

('L0.1.3', 'lit_oral_language',
 'Narrates a familiar story or personal event in 3+ sequential steps',
 'जानी-पहचानी कहानी या घटना को 3+ क्रमिक चरणों में सुनाता है',
 'balvatika', 3, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Narrates 3+ events in correct sequence using connectors (फिर, उसके बाद)"},
   "partially_achieved": {"description": "Narrates 2-3 events but sequence is jumbled or lacks connectors"},
   "not_achieved": {"description": "Cannot narrate beyond naming a single event or character"}
 }'::jsonb, NULL, NULL),

-- === Phonological Awareness (Balvatika) ===
('L0.2.1', 'lit_phonological',
 'Identifies rhyming words in Hindi',
 'हिंदी में तुकबंदी वाले शब्द पहचानता है',
 'balvatika', 1, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Correctly identifies rhyming pair from 3 options for 4/5 sets (e.g., बिल्ली-चिल्ली vs कुत्ता)"},
   "partially_achieved": {"description": "Identifies rhymes for 2-3/5 sets, or needs the rhyme spoken repeatedly"},
   "not_achieved": {"description": "Cannot identify rhyming words; does not understand the concept of same-ending sounds"}
 }'::jsonb, NULL, NULL),

('L0.2.2', 'lit_phonological',
 'Segments words into syllables by clapping',
 'ताली बजाकर शब्दों को अक्षरांशों में तोड़ता है',
 'balvatika', 2, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Correctly segments 2- and 3-syllable words (क-मल, ति-त-ली) for 4/5 words"},
   "partially_achieved": {"description": "Segments 2-syllable words but errors on 3-syllable, or claps do not match syllable boundaries"},
   "not_achieved": {"description": "Cannot segment — claps randomly or gives only 1 clap per word regardless of length"}
 }'::jsonb, NULL, NULL),

('L0.2.3', 'lit_phonological',
 'Identifies initial sound (first akshar) of spoken Hindi words',
 'बोले गए शब्दों की पहली ध्वनि (प्रथम अक्षर) पहचानता है',
 'balvatika', 3, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Correctly identifies initial sound for 4/5 words (कमल → क, पानी → प)"},
   "partially_achieved": {"description": "Identifies initial sound for 2-3/5 words, confuses similar sounds"},
   "not_achieved": {"description": "Cannot isolate the first sound; repeats the whole word or guesses"}
 }'::jsonb, NULL, NULL),

-- === Decoding (Balvatika) ===
('L0.3.1', 'lit_decoding',
 'Recognises 15+ Hindi varnamala letters (vowels अ-औ and consonants क-ण)',
 '15+ हिंदी वर्णमाला अक्षर पहचानता है (स्वर अ-औ और व्यंजन क-ण)',
 'balvatika', 1, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Identifies 15+ letters correctly when shown in random order, names the letter sound"},
   "partially_achieved": {"description": "Identifies 8-14 letters, confuses visually similar ones (ख/रव, म/भ)"},
   "not_achieved": {"description": "Identifies fewer than 8 letters"}
 }'::jsonb, NULL, NULL),

('L0.3.2', 'lit_decoding',
 'Associates letters with initial sounds of familiar words',
 'अक्षरों को परिचित शब्दों की पहली ध्वनि से जोड़ता है',
 'balvatika', 2, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Given a letter, names a word starting with it (क → कमल) for 8/10 letters; given a word, points to correct letter"},
   "partially_achieved": {"description": "Associates 4-7/10 letters correctly, or one direction only (letter→word but not word→letter)"},
   "not_achieved": {"description": "Cannot associate letters with sounds; treats letters as meaningless shapes"}
 }'::jsonb, NULL, NULL),

-- === Writing (Balvatika) ===
('L0.7.1', 'lit_writing',
 'Traces and copies basic strokes and letter-like patterns',
 'मूल रेखाओं और अक्षर-जैसे आकारों की नकल करता है',
 'balvatika', 1, 'written',
 '{
   "type": "written_production",
   "achieved": {"description": "Traces within guidelines, copies 5+ patterns (vertical, horizontal, curved strokes) legibly"},
   "partially_achieved": {"description": "Traces with some deviation, copies 2-4 patterns but strokes are inconsistent"},
   "not_achieved": {"description": "Cannot trace within guidelines or copy basic stroke patterns"}
 }'::jsonb, NULL, ARRAY['stroke_tracing']),

('L0.7.2', 'lit_writing',
 'Writes 10+ Hindi letters with correct formation on the shirorekha (headline)',
 '10+ हिंदी अक्षर शिरोरेखा सहित सही बनावट में लिखता है',
 'balvatika', 2, 'written',
 '{
   "type": "written_production",
   "achieved": {"description": "Writes 10+ letters legibly with shirorekha, correct stroke order, appropriate size"},
   "partially_achieved": {"description": "Writes 5-9 letters legibly but missing shirorekha or inconsistent formation"},
   "not_achieved": {"description": "Cannot write more than 4 letters legibly"}
 }'::jsonb, NULL, ARRAY['letter_writing']),


-- ============================================================================
-- COMPETENCIES — GRADE 1
-- Focus: complete varnamala, basic matras, simple word reading, sentence reading
-- ============================================================================

-- === Phonological Awareness (Grade 1) ===
('L1.2.1', 'lit_phonological',
 'Blends individual sounds to form words (phoneme blending)',
 'अलग-अलग ध्वनियों को जोड़कर शब्द बनाता है (ध्वनि संश्लेषण)',
 'grade_1', 1, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Blends 3-4 phonemes into words for 4/5 items (क-म-ल → कमल)"},
   "partially_achieved": {"description": "Blends 2 sounds but fails with 3-4 phoneme words"},
   "not_achieved": {"description": "Cannot blend sounds — repeats individual sounds or guesses"}
 }'::jsonb, NULL, NULL),

('L1.2.2', 'lit_phonological',
 'Segments words into individual sounds (phoneme segmentation)',
 'शब्दों को अलग-अलग ध्वनियों में तोड़ता है (ध्वनि विभाजन)',
 'grade_1', 2, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Segments 3-4 phoneme words correctly for 4/5 items (कमल → क-म-ल)"},
   "partially_achieved": {"description": "Segments 2-phoneme words but fails beyond, or gives syllables not phonemes"},
   "not_achieved": {"description": "Cannot segment — repeats the word whole or gives random sounds"}
 }'::jsonb, NULL, NULL),

-- === Decoding (Grade 1) — the critical literacy milestone ===
('L1.3.1', 'lit_decoding',
 'Recognises all Hindi consonants (व्यंजन क-ज्ञ) and vowels (स्वर अ-अः)',
 'सभी हिंदी व्यंजन (क-ज्ञ) और स्वर (अ-अः) पहचानता है',
 'grade_1', 1, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Identifies all 36 consonants and 13 vowels in random order within 2 seconds each"},
   "partially_achieved": {"description": "Identifies 30-48 of 49 letters; confuses 1-5 visually similar pairs"},
   "not_achieved": {"description": "Identifies fewer than 30 letters; significant gaps in consonant groups"}
 }'::jsonb, NULL, NULL),

('L1.3.2', 'lit_decoding',
 'Reads basic matra combinations (consonant + ा ि ी ु ू)',
 'मूल मात्रा संयोजन पढ़ता है (व्यंजन + ा ि ी ु ू)',
 'grade_1', 2, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Reads 5 basic matra combinations with any consonant fluently (का, कि, की, कु, कू → any consonant)"},
   "partially_achieved": {"description": "Reads ा (aa) matra fluently but struggles with ि/ी or ु/ू distinctions"},
   "not_achieved": {"description": "Cannot read consonant+matra combinations; reads only bare consonants"}
 }'::jsonb, NULL, NULL),

('L1.3.3', 'lit_decoding',
 'Reads remaining matra combinations (consonant + े ै ो ौ ं ँ)',
 'शेष मात्रा संयोजन पढ़ता है (व्यंजन + े ै ो ौ ं ँ)',
 'grade_1', 3, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Reads all matra combinations fluently — no confusion between े/ै or ो/ौ"},
   "partially_achieved": {"description": "Reads most matras but confuses े/ै or ो/ौ pairs consistently"},
   "not_achieved": {"description": "Cannot read most of these matra combinations"}
 }'::jsonb, NULL, NULL),

('L1.3.4', 'lit_decoding',
 'Reads simple CVC and 2-syllable words by decoding',
 'सरल CVC और 2-अक्षरांश शब्द डिकोड करके पढ़ता है',
 'grade_1', 4, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Decodes 2-syllable words with basic matras correctly for 4/5 words (कमल, नदी, पानी)"},
   "partially_achieved": {"description": "Decodes slowly with self-correction; reads 2-3/5 words correctly"},
   "not_achieved": {"description": "Cannot decode — recognises individual letters but cannot blend into words"}
 }'::jsonb, NULL, NULL),

-- === Word Reading (Grade 1) ===
('L1.4.1', 'lit_word_reading',
 'Reads 30+ high-frequency Hindi sight words',
 '30+ उच्च-आवृत्ति हिंदी दृष्टि शब्द पढ़ता है',
 'grade_1', 1, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Reads 30+ sight words instantly (<2 seconds) — यह, वह, और, में, का, है, को, से, etc."},
   "partially_achieved": {"description": "Reads 15-29 sight words instantly; decodes others slowly"},
   "not_achieved": {"description": "Reads fewer than 15 sight words; attempts to decode common words letter-by-letter"}
 }'::jsonb, NULL, NULL),

('L1.4.2', 'lit_word_reading',
 'Reads simple 2-3 syllable words with matras',
 'मात्रा सहित सरल 2-3 अक्षरांश शब्द पढ़ता है',
 'grade_1', 2, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Reads multi-syllable words with matras within 3 seconds each (किताब, सुंदर, बगीचा)"},
   "partially_achieved": {"description": "Reads 2-syllable matra words but hesitates on 3-syllable words"},
   "not_achieved": {"description": "Cannot read words with matras; stalls after first syllable"}
 }'::jsonb, NULL, NULL),

-- === Reading Fluency (Grade 1) ===
('L1.5.1', 'lit_fluency',
 'Reads simple sentences (3-5 words) with appropriate pace',
 'सरल वाक्य (3-5 शब्द) उचित गति से पढ़ता है',
 'grade_1', 1, 'oral_reading',
 '{
   "type": "fluency",
   "achieved": {"min_cwpm": 25, "min_accuracy": 0.90, "description": "Reads 3-5 word sentences at ≥25 CWPM with 90%+ accuracy, pauses at full stops"},
   "partially_achieved": {"cwpm_range": [15, 24], "or_accuracy_range": [0.80, 0.90], "description": "Reads sentences but word-by-word without flow, or frequent matra errors"},
   "not_achieved": {"max_cwpm": 15, "or_max_accuracy": 0.80, "description": "Cannot read connected sentences; stalls at individual words"}
 }'::jsonb, NULL, ARRAY['sentence_reading']),

-- === Comprehension (Grade 1) ===
('L1.6.1', 'lit_comprehension',
 'Answers literal who/what/where questions about a read-aloud story',
 'सुनी गई कहानी के बारे में कौन/क्या/कहाँ प्रश्नों के उत्तर देता है',
 'grade_1', 1, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Answers 4/5 literal questions correctly about a story heard once"},
   "partially_achieved": {"description": "Answers 2-3/5 questions; recalls characters but not events or locations"},
   "not_achieved": {"description": "Cannot answer literal questions; does not recall story content"}
 }'::jsonb, NULL, NULL),

('L1.6.2', 'lit_comprehension',
 'Sequences 3-4 events from a heard or read story',
 'सुनी या पढ़ी कहानी की 3-4 घटनाओं को क्रम में रखता है',
 'grade_1', 2, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Sequences 4 events correctly using picture cards or verbal retelling"},
   "partially_achieved": {"description": "Sequences 2-3 events but misplaces the middle event"},
   "not_achieved": {"description": "Cannot sequence — lists events randomly or recalls only the ending"}
 }'::jsonb, NULL, NULL),

-- === Writing (Grade 1) ===
('L1.7.1', 'lit_writing',
 'Writes all Hindi consonants and vowels legibly',
 'सभी हिंदी व्यंजन और स्वर स्पष्ट लिखता है',
 'grade_1', 1, 'written',
 '{
   "type": "written_production",
   "achieved": {"description": "Writes all 49 letters legibly with shirorekha, correct proportions, no mirror reversals"},
   "partially_achieved": {"description": "Writes 35-48 letters legibly; some inconsistent formation or missing shirorekha"},
   "not_achieved": {"description": "Writes fewer than 35 letters legibly; frequent formation errors"}
 }'::jsonb, NULL, ARRAY['letter_writing_full']),

('L1.7.2', 'lit_writing',
 'Writes simple words with basic matras correctly',
 'मूल मात्राओं सहित सरल शब्द सही लिखता है',
 'grade_1', 2, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.80, "sessions_required": 2, "description": "Writes 8/10 dictated words with correct matra placement"},
   "partially_achieved": {"accuracy_range": [0.50, 0.80], "description": "Writes words but matra placement errors (ि before vs after consonant)"},
   "not_achieved": {"max_accuracy": 0.50, "description": "Cannot write words with matras; writes only bare consonants"}
 }'::jsonb, NULL, ARRAY['word_dictation']),

('L1.7.3', 'lit_writing',
 'Writes simple sentences (3-5 words) with spaces between words',
 'शब्दों के बीच खाली जगह छोड़कर सरल वाक्य (3-5 शब्द) लिखता है',
 'grade_1', 3, 'written',
 '{
   "type": "written_production",
   "achieved": {"description": "Writes 3-5 word sentences with clear word boundaries, correct matras, and पूर्ण विराम (।)"},
   "partially_achieved": {"description": "Writes sentences but words run together, or inconsistent spacing"},
   "not_achieved": {"description": "Cannot compose a sentence; writes isolated words only"}
 }'::jsonb, NULL, ARRAY['sentence_writing']),


-- ============================================================================
-- COMPETENCIES — GRADE 2
-- Focus: conjunct consonants, fluent paragraph reading, comprehension, composition
-- ============================================================================

-- === Decoding (Grade 2) ===
('L2.3.1', 'lit_decoding',
 'Reads words with conjunct consonants (संयुक्त अक्षर: क्ष, त्र, ज्ञ, श्र, etc.)',
 'संयुक्त अक्षर वाले शब्द पढ़ता है (क्ष, त्र, ज्ञ, श्र आदि)',
 'grade_2', 1, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Reads common conjunct consonant words correctly (विद्यालय, पत्र, शक्ति) without hesitation"},
   "partially_achieved": {"description": "Reads familiar conjuncts (क्ष, त्र) but struggles with less common ones (ष्ट, ण्ड)"},
   "not_achieved": {"description": "Cannot decode conjunct consonants; skips them or reads component letters separately"}
 }'::jsonb, NULL, NULL),

('L2.3.2', 'lit_decoding',
 'Reads words with chandrabindu (ँ), anusvar (ं), and visarg (ः)',
 'चन्द्रबिन्दु (ँ), अनुस्वार (ं), विसर्ग (ः) वाले शब्द पढ़ता है',
 'grade_2', 2, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Reads words with nasalisation marks correctly (आँख, हंस, दुःख) with correct pronunciation"},
   "partially_achieved": {"description": "Reads words but ignores nasalisation — pronounces हंस as हस"},
   "not_achieved": {"description": "Cannot recognise these marks; treats them as unknown symbols"}
 }'::jsonb, NULL, NULL),

('L2.3.3', 'lit_decoding',
 'Reads words with halant and complex matra combinations',
 'हलन्त और जटिल मात्रा संयोजन वाले शब्द पढ़ता है',
 'grade_2', 3, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Reads halant words (जगत्, महत्) and complex combinations correctly"},
   "partially_achieved": {"description": "Reads some halant words but adds implicit schwa where halant should suppress it"},
   "not_achieved": {"description": "Cannot handle halant; reads जगत् as जगत or adds extra vowel sound"}
 }'::jsonb, NULL, NULL),

-- === Word Reading (Grade 2) ===
('L2.4.1', 'lit_word_reading',
 'Reads multi-syllable words with mixed matras fluently',
 'मिश्रित मात्राओं वाले बहु-अक्षरांश शब्द धाराप्रवाह पढ़ता है',
 'grade_2', 1, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Reads 4+ syllable words within 3 seconds (अध्यापिका, समझदारी) without syllable-by-syllable sounding"},
   "partially_achieved": {"description": "Reads 3-syllable words fluently but breaks down 4+ syllable words"},
   "not_achieved": {"description": "Reads all multi-syllable words syllable-by-syllable, very slow"}
 }'::jsonb, NULL, NULL),

('L2.4.2', 'lit_word_reading',
 'Reads 60+ sight words including function words and connectors',
 '60+ दृष्टि शब्द पढ़ता है जिनमें कार्य शब्द और योजक शामिल हैं',
 'grade_2', 2, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Reads 60+ words instantly — includes लेकिन, इसलिए, क्योंकि, हालाँकि, etc."},
   "partially_achieved": {"description": "Reads 40-59 words; decodes longer connectors instead of recognising instantly"},
   "not_achieved": {"description": "Reads fewer than 40 sight words"}
 }'::jsonb, NULL, NULL),

-- === Reading Fluency (Grade 2) — the ORF milestone ===
('L2.5.1', 'lit_fluency',
 'Reads grade-level passages at ≥40 CWPM with ≥90% accuracy',
 'कक्षा-स्तरीय अनुच्छेद ≥40 CWPM और ≥90% शुद्धता से पढ़ता है',
 'grade_2', 1, 'oral_reading',
 '{
   "type": "fluency",
   "achieved": {"min_cwpm": 40, "min_accuracy": 0.90, "description": "Reads connected text at ≥40 CWPM with ≥90% accuracy"},
   "partially_achieved": {"cwpm_range": [25, 39], "or_accuracy_range": [0.80, 0.90], "description": "Reads at 25-39 CWPM or 80-90% accuracy; may be choppy"},
   "not_achieved": {"max_cwpm": 25, "or_max_accuracy": 0.80, "description": "Below 25 CWPM or below 80% accuracy; word-by-word reading"}
 }'::jsonb, NULL, ARRAY['oral_reading_fluency']),

('L2.5.2', 'lit_fluency',
 'Reads with appropriate pauses at punctuation (।, ?, !)',
 'विराम चिह्नों पर उचित ठहराव से पढ़ता है (।, ?, !)',
 'grade_2', 2, 'oral_reading',
 '{
   "type": "observational",
   "achieved": {"description": "Pauses at पूर्ण विराम, raises intonation for questions, consistently across a paragraph"},
   "partially_achieved": {"description": "Pauses at full stops but ignores question marks or reads through commas"},
   "not_achieved": {"description": "No pause variation; reads everything in a monotone stream"}
 }'::jsonb, NULL, NULL),

-- === Comprehension (Grade 2) ===
('L2.6.1', 'lit_comprehension',
 'Answers literal questions about a passage read independently',
 'स्वतंत्र रूप से पढ़े अनुच्छेद के बारे में तथ्यात्मक प्रश्नों के उत्तर देता है',
 'grade_2', 1, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.80, "sessions_required": 2, "description": "Answers 4/5 who-what-when-where questions correctly from a read passage"},
   "partially_achieved": {"accuracy_range": [0.50, 0.80], "description": "Answers 2-3/5 questions; recalls details incompletely"},
   "not_achieved": {"max_accuracy": 0.50, "description": "Cannot answer most literal questions; may not have understood the passage"}
 }'::jsonb, NULL, ARRAY['comprehension_literal']),

('L2.6.2', 'lit_comprehension',
 'Identifies the main idea of a short paragraph',
 'छोटे अनुच्छेद का मुख्य विचार बताता है',
 'grade_2', 2, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "States the central topic/message of a 5-6 sentence paragraph in own words"},
   "partially_achieved": {"description": "Mentions a detail from the paragraph but not the central idea"},
   "not_achieved": {"description": "Cannot identify main idea; retells random details or says nothing"}
 }'::jsonb, NULL, NULL),

('L2.6.3', 'lit_comprehension',
 'Makes simple predictions about what will happen next in a story',
 'कहानी में आगे क्या होगा, इसकी सरल भविष्यवाणी करता है',
 'grade_2', 3, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Makes logical prediction based on story events and character behaviour"},
   "partially_achieved": {"description": "Makes a prediction but it is not connected to story events"},
   "not_achieved": {"description": "Cannot make predictions; says I don''t know or repeats what already happened"}
 }'::jsonb, NULL, NULL),

-- === Writing (Grade 2) ===
('L2.7.1', 'lit_writing',
 'Writes sentences with correct matra usage from dictation',
 'श्रुतलेख में सही मात्रा प्रयोग के साथ वाक्य लिखता है',
 'grade_2', 1, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.80, "sessions_required": 2, "description": "Writes 4/5 dictated sentences with correct matras and word boundaries"},
   "partially_achieved": {"accuracy_range": [0.50, 0.80], "description": "Writes sentences but 2-3 matra errors per sentence"},
   "not_achieved": {"max_accuracy": 0.50, "description": "Multiple matra errors per word; sentences are largely illegible"}
 }'::jsonb, NULL, ARRAY['dictation']),

('L2.7.2', 'lit_writing',
 'Writes 3-5 connected sentences on a familiar topic',
 'परिचित विषय पर 3-5 जुड़े वाक्य लिखता है',
 'grade_2', 2, 'written',
 '{
   "type": "written_production",
   "achieved": {"description": "Writes 4+ sentences that are topically connected, with matras and punctuation correct"},
   "partially_achieved": {"description": "Writes 2-3 sentences on topic but ideas are disconnected or frequent errors"},
   "not_achieved": {"description": "Writes 0-1 sentence, or sentences are off-topic / mostly illegible"}
 }'::jsonb, NULL, ARRAY['paragraph_writing']),

('L2.7.3', 'lit_writing',
 'Uses punctuation marks correctly (पूर्ण विराम, प्रश्नवाचक)',
 'विराम चिह्नों का सही प्रयोग करता है (।, ?)',
 'grade_2', 3, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.80, "sessions_required": 1, "description": "Uses पूर्ण विराम at sentence end and ? for questions in 4/5 instances"},
   "partially_achieved": {"accuracy_range": [0.40, 0.80], "description": "Uses पूर्ण विराम sometimes but not consistently; omits ? for questions"},
   "not_achieved": {"max_accuracy": 0.40, "description": "No punctuation used; or uses only full stop randomly"}
 }'::jsonb, NULL, ARRAY['punctuation']),


-- ============================================================================
-- COMPETENCIES — GRADE 3
-- Focus: fluent reading with expression, inferential comprehension,
--        paragraph composition, reading across genres
-- ============================================================================

-- === Decoding (Grade 3) ===
('L3.3.1', 'lit_decoding',
 'Reads all types of complex words (double conjuncts, compound words)',
 'सभी प्रकार के जटिल शब्द पढ़ता है (दोहरे संयुक्त, समास)',
 'grade_3', 1, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Reads complex words like स्वतंत्रता, अध्यापक, सर्वोत्तम without breakdown"},
   "partially_achieved": {"description": "Reads most but hesitates on unfamiliar double-conjuncts"},
   "not_achieved": {"description": "Cannot decode complex words; skips or substitutes"}
 }'::jsonb, NULL, NULL),

-- === Word Reading (Grade 3) ===
('L3.4.1', 'lit_word_reading',
 'Reads unfamiliar words using decoding strategies',
 'अपरिचित शब्दों को डिकोडिंग रणनीतियों से पढ़ता है',
 'grade_3', 1, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Attempts unfamiliar words by syllable-breaking, reads correctly for 4/5 new words"},
   "partially_achieved": {"description": "Attempts but reads 2-3/5 new words correctly; gives up on others"},
   "not_achieved": {"description": "Does not attempt unfamiliar words; skips or asks teacher"}
 }'::jsonb, NULL, NULL),

-- === Reading Fluency (Grade 3) — the NIPUN Bharat target ===
('L3.5.1', 'lit_fluency',
 'Reads grade-level passages at ≥60 CWPM with ≥95% accuracy',
 'कक्षा-स्तरीय अनुच्छेद ≥60 CWPM और ≥95% शुद्धता से पढ़ता है',
 'grade_3', 1, 'oral_reading',
 '{
   "type": "fluency",
   "achieved": {"min_cwpm": 60, "min_accuracy": 0.95, "comprehension_required": true, "description": "Reads at ≥60 CWPM with ≥95% accuracy AND demonstrates comprehension"},
   "partially_achieved": {"cwpm_range": [40, 59], "or_accuracy_range": [0.90, 0.95], "or_no_comprehension": true, "description": "Reads 40-59 CWPM or 90-95% accuracy, or reads fast but poor comprehension"},
   "not_achieved": {"max_cwpm": 40, "or_max_accuracy": 0.90, "description": "Below 40 CWPM or below 90% accuracy at grade-level text"}
 }'::jsonb, NULL, ARRAY['oral_reading_fluency_gr3']),

('L3.5.2', 'lit_fluency',
 'Reads with expression and prosody (appropriate intonation and stress)',
 'भाव और लय के साथ पढ़ता है (उचित स्वराघात और बल)',
 'grade_3', 2, 'oral_reading',
 '{
   "type": "observational",
   "achieved": {"description": "Reads with natural phrasing, varies pitch for questions/exclamations, stress on key words"},
   "partially_achieved": {"description": "Some phrasing but mostly monotone; reads in 2-3 word chunks instead of phrases"},
   "not_achieved": {"description": "Reads word-by-word with no expression variation; robotic delivery"}
 }'::jsonb, NULL, NULL),

-- === Comprehension (Grade 3) ===
('L3.6.1', 'lit_comprehension',
 'Answers inferential questions about a passage (why/how)',
 'अनुच्छेद के बारे में अनुमानात्मक प्रश्नों (क्यों/कैसे) के उत्तर देता है',
 'grade_3', 1, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.75, "sessions_required": 2, "description": "Answers 3/4 why/how questions by connecting evidence from text with reasoning"},
   "partially_achieved": {"accuracy_range": [0.40, 0.75], "description": "Answers 1-2/4 inference questions; gives literal answers to why/how questions"},
   "not_achieved": {"max_accuracy": 0.40, "description": "Cannot make inferences; answers only literal questions or guesses"}
 }'::jsonb, NULL, ARRAY['comprehension_inferential']),

('L3.6.2', 'lit_comprehension',
 'Identifies cause-effect relationships in text',
 'पाठ में कारण-प्रभाव संबंधों की पहचान करता है',
 'grade_3', 2, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.75, "sessions_required": 2, "description": "Correctly identifies cause AND effect for 3/4 items; uses because/so structure"},
   "partially_achieved": {"accuracy_range": [0.40, 0.75], "description": "Identifies either cause or effect but not both, or confuses direction"},
   "not_achieved": {"max_accuracy": 0.40, "description": "Cannot identify causal relationships in text"}
 }'::jsonb, NULL, ARRAY['cause_effect']),

('L3.6.3', 'lit_comprehension',
 'Summarises a paragraph in 2-3 sentences in own words',
 'अनुच्छेद का सारांश 2-3 वाक्यों में अपने शब्दों में बताता है',
 'grade_3', 3, 'observed',
 '{
   "type": "observational",
   "achieved": {"description": "Summarises capturing main idea + 1-2 key details, in own words (not copying text)"},
   "partially_achieved": {"description": "Retells in 4+ sentences (too detailed) or misses the main idea"},
   "not_achieved": {"description": "Cannot summarise; either copies sentences from text or says unrelated content"}
 }'::jsonb, NULL, NULL),

('L3.6.4', 'lit_comprehension',
 'Distinguishes fact from opinion in age-appropriate text',
 'आयु-उपयुक्त पाठ में तथ्य और राय में अंतर करता है',
 'grade_3', 4, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.75, "sessions_required": 1, "description": "Correctly labels 3/4 statements as fact or opinion with reasoning"},
   "partially_achieved": {"accuracy_range": [0.40, 0.75], "description": "Labels some correctly but confused by opinions stated assertively"},
   "not_achieved": {"max_accuracy": 0.40, "description": "Cannot distinguish; treats all statements as facts"}
 }'::jsonb, NULL, ARRAY['fact_opinion']),

-- === Writing (Grade 3) ===
('L3.7.1', 'lit_writing',
 'Writes a coherent paragraph of 5-7 sentences on a given topic',
 'दिए गए विषय पर 5-7 वाक्यों का सुसंगत अनुच्छेद लिखता है',
 'grade_3', 1, 'written',
 '{
   "type": "written_production",
   "achieved": {"description": "Writes 5-7 topically connected sentences with opening, body, closing; correct matras and punctuation"},
   "partially_achieved": {"description": "Writes 3-5 sentences on topic but lacks structure or has frequent matra/punctuation errors"},
   "not_achieved": {"description": "Writes fewer than 3 sentences, or sentences are disconnected / mostly illegible"}
 }'::jsonb, NULL, ARRAY['paragraph_composition']),

('L3.7.2', 'lit_writing',
 'Uses basic grammar correctly (gender, number, tense agreement)',
 'मूल व्याकरण सही उपयोग करता है (लिंग, वचन, काल)',
 'grade_3', 2, 'written',
 '{
   "type": "computation",
   "achieved": {"min_accuracy": 0.75, "sessions_required": 2, "description": "Correct gender-verb agreement, singular/plural, and tense in 3/4 sentences"},
   "partially_achieved": {"accuracy_range": [0.40, 0.75], "description": "Some agreement errors, especially with feminine nouns or past tense"},
   "not_achieved": {"max_accuracy": 0.40, "description": "Frequent agreement errors; gender/tense randomly applied"}
 }'::jsonb, NULL, ARRAY['grammar_agreement']),

('L3.7.3', 'lit_writing',
 'Writes simple informal letters and short compositions',
 'सरल अनौपचारिक पत्र और लघु रचनाएँ लिखता है',
 'grade_3', 3, 'written',
 '{
   "type": "written_production",
   "achieved": {"description": "Writes letter with correct format (प्रिय, greeting, body, closing); composition has beginning-middle-end"},
   "partially_achieved": {"description": "Writes content but missing format elements; or format correct but content is 1-2 sentences only"},
   "not_achieved": {"description": "Cannot write in letter format; composition is a single unstructured sentence"}
 }'::jsonb, NULL, ARRAY['letter_writing', 'composition']);
