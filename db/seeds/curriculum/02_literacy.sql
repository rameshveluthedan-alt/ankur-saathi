-- ============================================================================
-- R1 LITERACY (HINDI) WEEKLY PLAN — Grades 1, 2, 3
-- Plan ID: a0000000-0000-0000-0000-000000000001
-- ============================================================================

INSERT INTO curriculum_weeks (plan_id, grade_level, domain_id, week_number, topic_title_en, topic_title_hi, competency_ids, notes, sort_order) VALUES

-- ============================================================================
-- GRADE 1 R1 LITERACY — 36 weeks
-- Target: full varnamala, all matras, simple word/sentence reading, basic writing
-- ============================================================================

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'r1_literacy', 1,
 'Baseline assessment', 'आधारभूत मूल्यांकन',
 ARRAY['L0.1.1','L0.1.2','L0.2.1','L0.2.3','L0.3.1','L0.3.2','L0.7.2'],
 'Full diagnostic: oral language, phonological awareness, letter recognition, writing. Place children.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'r1_literacy', 2,
 'Baseline (continued) + grouping', 'आधारभूत (जारी) + समूहन',
 ARRAY['L0.1.3','L0.2.2','L1.3.1'],
 'Complete baseline. Cluster into B/P/P.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'r1_literacy', 3,
 'Oral language: Listening and speaking', 'मौखिक भाषा: सुनना और बोलना',
 ARRAY['L0.1.1','L0.1.2'],
 'Foundation week. Story read-alouds, following instructions, speaking in sentences.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'r1_literacy', 4,
 'Phonological awareness: Rhyming and syllables', 'ध्वनि जागरूकता: तुकबंदी और अक्षरांश',
 ARRAY['L0.2.1','L0.2.2'],
 'Clapping games. Hindi rhymes and poems.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'r1_literacy', 5,
 'Phonological awareness: Initial sounds + phoneme blending', 'ध्वनि जागरूकता: प्रथम ध्वनि + ध्वनि संश्लेषण',
 ARRAY['L0.2.3','L1.2.1'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'r1_literacy', 6,
 'Phoneme segmentation', 'ध्वनि विभाजन',
 ARRAY['L1.2.2'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'r1_literacy', 7,
 'Letter recognition: Vowels (अ-औ) and consonants क-वर्ग', 'अक्षर पहचान: स्वर और क-वर्ग',
 ARRAY['L0.3.1','L1.3.1'],
 'Beginners still on partial recognition; Proficients move ahead.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'r1_literacy', 8,
 'Letter recognition: च-वर्ग, ट-वर्ग, त-वर्ग', 'अक्षर पहचान: च, ट, त वर्ग',
 ARRAY['L1.3.1'],
 'Visually similar letter confusion (ख/रव, ध/घ) — diagnose early.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'r1_literacy', 9,
 'Letter recognition: प-वर्ग, य-ह, complete varnamala', 'अक्षर पहचान: प-वर्ग, य-ह, पूर्ण वर्णमाला',
 ARRAY['L1.3.1'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'r1_literacy', 10,
 'Letter writing: Full varnamala with shirorekha', 'अक्षर लेखन: शिरोरेखा सहित पूर्ण वर्णमाला',
 ARRAY['L1.7.1'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'r1_literacy', 11,
 'Matras: ा (aa) matra — reading and writing', 'मात्रा: ा (आ की मात्रा) — पठन और लेखन',
 ARRAY['L1.3.2'],
 'First and most common matra. का, खा, गा, etc.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'r1_literacy', 12,
 'Matras: ि (chhoti i) and ी (badi ee)', 'मात्रा: ि (छोटी इ) और ी (बड़ी ई)',
 ARRAY['L1.3.2'],
 'Confusing pair #1. ि goes BEFORE the consonant in writing — critical to teach.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'r1_literacy', 13,
 'Matras: ु (chhota u) and ू (bada oo)', 'मात्रा: ु (छोटा उ) और ू (बड़ा ऊ)',
 ARRAY['L1.3.2'],
 'Confusing pair #2. Both go below the consonant — length is the distinction.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'r1_literacy', 14,
 'Word reading: Simple words with basic matras', 'शब्द पठन: मूल मात्राओं वाले सरल शब्द',
 ARRAY['L1.3.4','L1.7.2'],
 'Decoding practice: कमल, नदी, पानी, किताब.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'r1_literacy', 15,
 'Matras: े (e) and ै (ai)', 'मात्रा: े (ए) और ै (ऐ)',
 ARRAY['L1.3.3'],
 'Confusing pair #3. One tick vs two ticks above shirorekha.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'r1_literacy', 16,
 'Matras: ो (o) and ौ (au)', 'मात्रा: ो (ओ) और ौ (औ)',
 ARRAY['L1.3.3'],
 'Confusing pair #4. Complete the matra set.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'r1_literacy', 17,
 'Matras: ं (anusvar) and ँ (chandrabindu)', 'मात्रा: ं (अनुस्वार) और ँ (चन्द्रबिन्दु)',
 ARRAY['L1.3.3'],
 'Nasalisation marks. Complete all matra combinations.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'r1_literacy', 18,
 'Sight words: 30 high-frequency words', 'दृष्टि शब्द: 30 उच्च-आवृत्ति शब्द',
 ARRAY['L1.4.1'],
 'यह, वह, और, में, का, है, को, से, ने, पर, etc. Flash card drills.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'r1_literacy', 19,
 'Word reading: Multi-syllable words with matras', 'शब्द पठन: मात्रा सहित बहु-अक्षरांश शब्द',
 ARRAY['L1.4.2'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'r1_literacy', 20,
 'Mid-year periodic assessment', 'अर्धवार्षिक मूल्यांकन',
 ARRAY['L1.3.1','L1.3.2','L1.3.3','L1.3.4','L1.4.1','L1.7.1','L1.7.2'],
 'Full reassessment. Regroup.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'r1_literacy', 21,
 'Sentence reading: 3-5 word simple sentences', 'वाक्य पठन: 3-5 शब्दों के सरल वाक्य',
 ARRAY['L1.5.1'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'r1_literacy', 22,
 'Sentence reading: Fluency building', 'वाक्य पठन: प्रवाह निर्माण',
 ARRAY['L1.5.1'],
 'Repeated reading. Paired reading. Target: 25 CWPM.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'r1_literacy', 23,
 'Comprehension: Read-aloud — literal questions', 'बोध: सस्वर पठन — तथ्यात्मक प्रश्न',
 ARRAY['L1.6.1'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'r1_literacy', 24,
 'Comprehension: Story sequencing', 'बोध: कहानी अनुक्रमण',
 ARRAY['L1.6.2'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'r1_literacy', 25,
 'Writing: Words with matras — dictation', 'लेखन: मात्रा सहित शब्द — श्रुतलेख',
 ARRAY['L1.7.2'],
 'ि placement error (L1.7.2-M1) — the #1 Hindi writing misconception.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'r1_literacy', 26,
 'Writing: Simple sentences with spacing', 'लेखन: खाली जगह सहित सरल वाक्य',
 ARRAY['L1.7.3'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'r1_literacy', 27,
 'Decoding spiral: Matra review with new words', 'डिकोडिंग सर्पिल: नए शब्दों से मात्रा दोहराई',
 ARRAY['L1.3.2','L1.3.3','L1.3.4'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'r1_literacy', 28,
 'Fluency and comprehension: Connected text', 'प्रवाह और बोध: जुड़ा पाठ',
 ARRAY['L1.5.1','L1.6.1'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'r1_literacy', 29,
 'Writing spiral: Sentences from picture prompts', 'लेखन सर्पिल: चित्र संकेतों से वाक्य',
 ARRAY['L1.7.3'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'r1_literacy', 30,
 'Consolidation: Full year review', 'समेकन: वार्षिक दोहराई',
 ARRAY['L1.3.2','L1.3.3','L1.4.1','L1.5.1','L1.7.2'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_1', 'r1_literacy', 31,
 'End-year periodic assessment', 'वार्षिक मूल्यांकन',
 ARRAY['L1.3.1','L1.3.2','L1.3.3','L1.3.4','L1.4.1','L1.5.1','L1.6.1','L1.7.2','L1.7.3'],
 'Full-class reassessment. Final B/P/P for year.', 0),


-- ============================================================================
-- GRADE 2 R1 LITERACY — 29 weeks
-- Target: conjuncts, 40 CWPM, literal comprehension, paragraph writing
-- ============================================================================

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'r1_literacy', 1,
 'Baseline assessment', 'आधारभूत मूल्यांकन',
 ARRAY['L1.3.2','L1.3.3','L1.3.4','L1.4.1','L1.5.1','L1.7.2'],
 'Assess Grade 1 competencies. Many children may still have matra gaps.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'r1_literacy', 2,
 'Matra remediation + sight words', 'मात्रा उपचार + दृष्टि शब्द',
 ARRAY['L1.3.2','L1.3.3','L1.4.1','L2.4.2'],
 'Beginners: matra remediation. Proficients: extended sight words.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'r1_literacy', 3,
 'Conjunct consonants: Common conjuncts (क्ष, त्र, ज्ञ, श्र)', 'संयुक्त अक्षर: सामान्य (क्ष, त्र, ज्ञ, श्र)',
 ARRAY['L2.3.1'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'r1_literacy', 4,
 'Conjunct consonants: Less common conjuncts + practice', 'संयुक्त अक्षर: कम सामान्य + अभ्यास',
 ARRAY['L2.3.1'],
 'L2.3.1-M1: reads conjuncts as separate letters. L2.3.1-M2: schwa insertion.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'r1_literacy', 5,
 'Chandrabindu, anusvar, visarg', 'चन्द्रबिन्दु, अनुस्वार, विसर्ग',
 ARRAY['L2.3.2'],
 'Nasalisation marks in reading.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'r1_literacy', 6,
 'Halant and complex matra combinations', 'हलन्त और जटिल मात्रा संयोजन',
 ARRAY['L2.3.3'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'r1_literacy', 7,
 'Multi-syllable word reading: Fluency', 'बहु-अक्षरांश शब्द पठन: प्रवाह',
 ARRAY['L2.4.1'],
 'Move from syllable-by-syllable to whole-word recognition.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'r1_literacy', 8,
 'Extended sight words + function words', 'विस्तारित दृष्टि शब्द + कार्य शब्द',
 ARRAY['L2.4.2'],
 'लेकिन, इसलिए, क्योंकि — connectors needed for comprehension.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'r1_literacy', 9,
 'Oral reading fluency: Passage reading', 'मौखिक पठन प्रवाह: अनुच्छेद पठन',
 ARRAY['L2.5.1'],
 'Teacher stopwatch + manual entry. Target: 40 CWPM.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'r1_literacy', 10,
 'Fluency: Prosody and punctuation pauses', 'प्रवाह: लय और विराम चिह्नों पर ठहराव',
 ARRAY['L2.5.1','L2.5.2'],
 'Word-by-word reading (L2.5.1-M1) is the primary diagnostic target.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'r1_literacy', 11,
 'Comprehension: Literal questions from independent reading', 'बोध: स्वतंत्र पठन से तथ्यात्मक प्रश्न',
 ARRAY['L2.6.1'],
 'Word-caller detection (L2.6.1-M1): reads but doesn''t comprehend.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'r1_literacy', 12,
 'Comprehension: Main idea identification', 'बोध: मुख्य विचार पहचान',
 ARRAY['L2.6.2'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'r1_literacy', 13,
 'Comprehension: Prediction', 'बोध: भविष्यवाणी',
 ARRAY['L2.6.3'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'r1_literacy', 14,
 'Writing: Dictation with correct matras', 'लेखन: सही मात्राओं सहित श्रुतलेख',
 ARRAY['L2.7.1'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'r1_literacy', 15,
 'Writing: 3-5 sentences on a topic', 'लेखन: विषय पर 3-5 वाक्य',
 ARRAY['L2.7.2'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'r1_literacy', 16,
 'Writing: Punctuation (। and ?)', 'लेखन: विराम चिह्न (। और ?)',
 ARRAY['L2.7.3'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'r1_literacy', 17,
 'Consolidation before mid-year', 'अर्धवार्षिक पूर्व समेकन',
 ARRAY['L2.3.1','L2.5.1','L2.6.1'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'r1_literacy', 20,
 'Mid-year periodic assessment', 'अर्धवार्षिक मूल्यांकन',
 ARRAY['L2.3.1','L2.4.1','L2.5.1','L2.6.1','L2.7.1','L2.7.2'],
 'Full reassessment. Regroup.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'r1_literacy', 21,
 'Fluency spiral: Repeated reading for speed', 'प्रवाह सर्पिल: गति के लिए बार-बार पठन',
 ARRAY['L2.5.1','L2.5.2'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'r1_literacy', 22,
 'Comprehension spiral: Literal + main idea mixed', 'बोध सर्पिल: तथ्यात्मक + मुख्य विचार मिश्रित',
 ARRAY['L2.6.1','L2.6.2'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'r1_literacy', 23,
 'Writing spiral: Extended paragraph practice', 'लेखन सर्पिल: विस्तारित अनुच्छेद अभ्यास',
 ARRAY['L2.7.2','L2.7.3'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'r1_literacy', 24,
 'Consolidation: Full year review', 'समेकन: वार्षिक दोहराई',
 ARRAY['L2.3.1','L2.5.1','L2.6.1','L2.7.2'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_2', 'r1_literacy', 25,
 'End-year periodic assessment', 'वार्षिक मूल्यांकन',
 ARRAY['L2.3.1','L2.4.1','L2.5.1','L2.6.1','L2.6.2','L2.7.1','L2.7.2'],
 'Final B/P/P. NIPUN target: 40 CWPM + comprehension.', 0),


-- ============================================================================
-- GRADE 3 R1 LITERACY — 31 weeks
-- Target: 60 CWPM, inferential comprehension, coherent paragraph writing
-- ============================================================================

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'r1_literacy', 1,
 'Baseline assessment', 'आधारभूत मूल्यांकन',
 ARRAY['L2.3.1','L2.5.1','L2.6.1','L2.6.2','L2.7.2'],
 'Assess Grade 2 competencies. Focus on fluency (CWPM) and comprehension.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'r1_literacy', 2,
 'Decoding remediation + complex words', 'डिकोडिंग उपचार + जटिल शब्द',
 ARRAY['L2.3.1','L3.3.1'],
 'Beginners: conjunct remediation. Proficients: complex/compound words.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'r1_literacy', 3,
 'Complex word reading: Double conjuncts, compound words', 'जटिल शब्द पठन',
 ARRAY['L3.3.1'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'r1_literacy', 4,
 'Unfamiliar word strategies: Syllable-breaking', 'अपरिचित शब्द रणनीतियाँ',
 ARRAY['L3.4.1'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'r1_literacy', 5,
 'Fluency: Building to 60 CWPM', 'प्रवाह: 60 CWPM की ओर',
 ARRAY['L3.5.1'],
 'Repeated reading, timed practice, paired reading.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'r1_literacy', 6,
 'Fluency: Expression and prosody', 'प्रवाह: भाव और लय',
 ARRAY['L3.5.1','L3.5.2'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'r1_literacy', 7,
 'Comprehension: Literal review + inference introduction', 'बोध: तथ्यात्मक दोहराई + अनुमान परिचय',
 ARRAY['L2.6.1','L3.6.1'],
 'Transition from literal to inferential. "Why" and "how" questions.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'r1_literacy', 8,
 'Comprehension: Inferential questions', 'बोध: अनुमानात्मक प्रश्न',
 ARRAY['L3.6.1'],
 'L3.6.1-M1: gives literal answer to inference question.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'r1_literacy', 9,
 'Comprehension: Cause and effect', 'बोध: कारण और प्रभाव',
 ARRAY['L3.6.2'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'r1_literacy', 10,
 'Comprehension: Summarisation', 'बोध: सारांश',
 ARRAY['L3.6.3'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'r1_literacy', 11,
 'Writing: Coherent paragraph (5-7 sentences)', 'लेखन: सुसंगत अनुच्छेद (5-7 वाक्य)',
 ARRAY['L3.7.1'],
 'Opening, body, closing. Connectors: फिर, इसलिए, लेकिन.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'r1_literacy', 12,
 'Writing: Grammar — gender, number, tense', 'लेखन: व्याकरण — लिंग, वचन, काल',
 ARRAY['L3.7.2'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'r1_literacy', 13,
 'Writing: Letters and compositions', 'लेखन: पत्र और रचनाएँ',
 ARRAY['L3.7.3'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'r1_literacy', 14,
 'Comprehension: Fact vs opinion', 'बोध: तथ्य बनाम राय',
 ARRAY['L3.6.4'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'r1_literacy', 15,
 'Consolidation before mid-year', 'अर्धवार्षिक पूर्व समेकन',
 ARRAY['L3.5.1','L3.6.1','L3.7.1'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'r1_literacy', 20,
 'Mid-year periodic assessment', 'अर्धवार्षिक मूल्यांकन',
 ARRAY['L3.3.1','L3.5.1','L3.6.1','L3.6.2','L3.7.1','L3.7.2'],
 'Full reassessment. Regroup. CWPM check against NIPUN target.', 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'r1_literacy', 21,
 'Fluency spiral: Push toward 60 CWPM', 'प्रवाह सर्पिल: 60 CWPM की ओर',
 ARRAY['L3.5.1','L3.5.2'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'r1_literacy', 22,
 'Comprehension spiral: All types mixed', 'बोध सर्पिल: सभी प्रकार मिश्रित',
 ARRAY['L3.6.1','L3.6.2','L3.6.3','L3.6.4'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'r1_literacy', 23,
 'Writing spiral: Extended compositions', 'लेखन सर्पिल: विस्तारित रचनाएँ',
 ARRAY['L3.7.1','L3.7.2','L3.7.3'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'r1_literacy', 24,
 'Consolidation: Full year review', 'समेकन: वार्षिक दोहराई',
 ARRAY['L3.5.1','L3.6.1','L3.7.1'],
 NULL, 0),

('a0000000-0000-0000-0000-000000000001', 'grade_3', 'r1_literacy', 25,
 'End-year periodic assessment', 'वार्षिक मूल्यांकन',
 ARRAY['L3.3.1','L3.5.1','L3.6.1','L3.6.2','L3.6.3','L3.7.1','L3.7.2','L3.7.3'],
 'Final NIPUN assessment. Target: 60 CWPM + comprehension + paragraph writing.', 0);
