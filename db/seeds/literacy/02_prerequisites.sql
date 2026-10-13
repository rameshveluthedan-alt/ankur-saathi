-- ============================================================================
-- ANKUR SAATHI — Layer 1 KB: R1 Literacy (Hindi) Seed Data
-- Part 2: Prerequisite Links (DAG) + Learning Outcomes
-- ============================================================================

-- ============================================================================
-- PREREQUISITE LINKS
-- The literacy DAG has a distinct shape from numeracy:
--   oral language → phonological awareness → decoding → word reading → fluency → comprehension
-- Writing has its own parallel chain that draws from decoding.
-- Within decoding, the Hindi-specific progression is:
--   bare letters → basic matras (ा ि ी ु ू) → remaining matras (े ै ो ौ ं ँ)
--   → conjuncts → chandrabindu/anusvar/visarg → halant → complex words
-- ============================================================================

INSERT INTO competency_prerequisites (competency_id, prerequisite_id, prerequisite_type) VALUES

-- ─── ORAL LANGUAGE FOUNDATION ───
-- Oral language is the bedrock — phonological awareness needs it
('L0.1.3', 'L0.1.2', 'hard'),       -- Narrating needs speaking in sentences
('L0.2.1', 'L0.1.1', 'soft'),       -- Rhyming helped by listening skills
('L0.2.2', 'L0.1.1', 'soft'),       -- Syllable segmentation helped by listening
('L0.2.3', 'L0.1.1', 'soft'),       -- Initial sound identification helped by listening

-- ─── PHONOLOGICAL AWARENESS CHAIN ───
('L0.2.2', 'L0.2.1', 'soft'),       -- Syllable segmentation helped by rhyming awareness
('L0.2.3', 'L0.2.2', 'hard'),       -- Initial sound needs syllable awareness first
('L1.2.1', 'L0.2.3', 'hard'),       -- Phoneme blending needs initial sound identification
('L1.2.1', 'L0.2.2', 'hard'),       -- Phoneme blending needs syllable segmentation
('L1.2.2', 'L1.2.1', 'hard'),       -- Phoneme segmentation needs blending (inverse skills develop together)

-- ─── DECODING: LETTER RECOGNITION ───
('L0.3.2', 'L0.3.1', 'hard'),       -- Letter-sound association needs letter recognition
('L0.3.2', 'L0.2.3', 'hard'),       -- Letter-sound association needs initial sound awareness
('L1.3.1', 'L0.3.1', 'hard'),       -- Full varnamala needs partial letter recognition
('L1.3.1', 'L0.3.2', 'hard'),       -- Full varnamala needs letter-sound association

-- ─── DECODING: MATRA PROGRESSION (Hindi-specific critical chain) ───
('L1.3.2', 'L1.3.1', 'hard'),       -- Basic matras need full letter recognition
('L1.3.3', 'L1.3.2', 'hard'),       -- Remaining matras need basic matras
('L1.3.4', 'L1.3.2', 'hard'),       -- CVC word decoding needs basic matras
('L1.3.4', 'L1.2.1', 'hard'),       -- Word decoding needs phoneme blending skill

-- Grade 2 decoding builds on Grade 1
('L2.3.1', 'L1.3.3', 'hard'),       -- Conjuncts need all matras mastered
('L2.3.1', 'L1.3.4', 'hard'),       -- Conjuncts need word decoding ability
('L2.3.2', 'L1.3.3', 'hard'),       -- Chandrabindu/anusvar needs all matras
('L2.3.3', 'L2.3.1', 'hard'),       -- Halant needs conjunct understanding
('L2.3.3', 'L2.3.2', 'soft'),       -- Halant helped by anusvar/visarg awareness

-- Grade 3 decoding
('L3.3.1', 'L2.3.1', 'hard'),       -- Complex words need conjunct consonants
('L3.3.1', 'L2.3.3', 'hard'),       -- Complex words need halant mastery

-- ─── WORD READING CHAIN ───
('L1.4.1', 'L1.3.4', 'hard'),       -- Sight words build on decoded word reading
('L1.4.2', 'L1.3.2', 'hard'),       -- Multi-syllable matra words need basic matras
('L1.4.2', 'L1.3.3', 'hard'),       -- Multi-syllable matra words need all matras
('L1.4.2', 'L1.4.1', 'soft'),       -- Multi-syllable helped by sight word foundation

('L2.4.1', 'L1.4.2', 'hard'),       -- Grade 2 word reading needs Grade 1 multi-syllable
('L2.4.1', 'L2.3.1', 'hard'),       -- Grade 2 word reading needs conjunct decoding
('L2.4.2', 'L1.4.1', 'hard'),       -- Extended sight words build on Grade 1 sight words

('L3.4.1', 'L2.4.1', 'hard'),       -- Unfamiliar word strategies need fluent multi-syllable reading
('L3.4.1', 'L3.3.1', 'hard'),       -- Unfamiliar word strategies need complex decoding

-- ─── READING FLUENCY CHAIN ───
('L1.5.1', 'L1.4.1', 'hard'),       -- Sentence reading needs sight word base
('L1.5.1', 'L1.4.2', 'hard'),       -- Sentence reading needs word reading with matras

('L2.5.1', 'L1.5.1', 'hard'),       -- Grade 2 ORF needs Grade 1 sentence reading
('L2.5.1', 'L2.4.1', 'hard'),       -- Grade 2 ORF needs fluent multi-syllable word reading
('L2.5.2', 'L2.5.1', 'hard'),       -- Prosody needs basic fluency first

('L3.5.1', 'L2.5.1', 'hard'),       -- Grade 3 ORF needs Grade 2 ORF
('L3.5.1', 'L3.4.1', 'hard'),       -- Grade 3 ORF needs unfamiliar word strategies
('L3.5.2', 'L3.5.1', 'hard'),       -- Expression/prosody needs fluency foundation
('L3.5.2', 'L2.5.2', 'soft'),       -- Grade 3 prosody helped by Grade 2 punctuation awareness

-- ─── COMPREHENSION CHAIN ───
('L1.6.1', 'L0.1.3', 'hard'),       -- Literal comprehension needs oral narration skills
('L1.6.1', 'L0.1.1', 'hard'),       -- Literal comprehension needs listening skills
('L1.6.2', 'L1.6.1', 'hard'),       -- Sequencing needs literal recall

('L2.6.1', 'L1.6.1', 'hard'),       -- Independent literal comprehension needs oral literal comprehension
('L2.6.1', 'L2.5.1', 'hard'),       -- Reading comprehension needs reading fluency
('L2.6.2', 'L2.6.1', 'hard'),       -- Main idea needs literal comprehension
('L2.6.3', 'L2.6.1', 'soft'),       -- Prediction helped by literal comprehension

('L3.6.1', 'L2.6.1', 'hard'),       -- Inference needs literal comprehension mastered
('L3.6.1', 'L2.6.2', 'hard'),       -- Inference needs main idea identification
('L3.6.1', 'L3.5.1', 'hard'),       -- Inference needs fluent grade-level reading
('L3.6.2', 'L3.6.1', 'hard'),       -- Cause-effect needs inference skills
('L3.6.3', 'L2.6.2', 'hard'),       -- Summarising needs main idea identification
('L3.6.3', 'L3.6.1', 'soft'),       -- Summarising helped by inference skills
('L3.6.4', 'L3.6.1', 'hard'),       -- Fact vs opinion needs inference ability

-- ─── WRITING CHAIN ───
('L0.7.2', 'L0.7.1', 'hard'),       -- Letter writing needs stroke/tracing foundation
('L0.7.2', 'L0.3.1', 'hard'),       -- Letter writing needs letter recognition

('L1.7.1', 'L0.7.2', 'hard'),       -- Full varnamala writing needs partial letter writing
('L1.7.1', 'L1.3.1', 'hard'),       -- Writing letters needs recognising them all
('L1.7.2', 'L1.7.1', 'hard'),       -- Word writing with matras needs letter writing
('L1.7.2', 'L1.3.2', 'hard'),       -- Word writing with matras needs reading matras
('L1.7.3', 'L1.7.2', 'hard'),       -- Sentence writing needs word writing
('L1.7.3', 'L1.4.1', 'soft'),       -- Sentence writing helped by sight word knowledge

('L2.7.1', 'L1.7.2', 'hard'),       -- Dictation needs word writing ability
('L2.7.1', 'L1.3.3', 'hard'),       -- Dictation needs reading remaining matras (to write them)
('L2.7.2', 'L1.7.3', 'hard'),       -- Paragraph writing needs sentence writing
('L2.7.2', 'L2.7.1', 'hard'),       -- Paragraph writing needs dictation-level accuracy
('L2.7.3', 'L2.7.2', 'soft'),       -- Punctuation develops alongside paragraph writing

('L3.7.1', 'L2.7.2', 'hard'),       -- Coherent paragraph needs Grade 2 multi-sentence writing
('L3.7.1', 'L2.7.3', 'hard'),       -- Coherent paragraph needs punctuation
('L3.7.2', 'L3.7.1', 'hard'),       -- Grammar in writing needs paragraph writing ability
('L3.7.3', 'L3.7.1', 'hard'),       -- Letters/compositions need paragraph writing
('L3.7.3', 'L3.7.2', 'soft');       -- Letters/compositions helped by grammar


-- ============================================================================
-- LEARNING OUTCOMES
-- Granular measurable items under key competencies.
-- Focused on decoding (where Hindi-specific granularity matters most)
-- and writing (where worksheet-based assessment needs fine-grained items).
-- ============================================================================

INSERT INTO learning_outcomes (id, competency_id, name_en, name_hi, sort_order, assessment_modality) VALUES

-- L0.3.1: Letter recognition (Balvatika)
('L0.3.1.a', 'L0.3.1', 'Recognises vowels अ-औ', 'स्वर अ-औ पहचानता है', 1, 'observed'),
('L0.3.1.b', 'L0.3.1', 'Recognises consonants क-ण (first 20)', 'व्यंजन क-ण पहचानता है (पहले 20)', 2, 'observed'),
('L0.3.1.c', 'L0.3.1', 'Names the sound each letter makes', 'प्रत्येक अक्षर की ध्वनि बताता है', 3, 'observed'),

-- L1.3.1: Full varnamala recognition
('L1.3.1.a', 'L1.3.1', 'Recognises all 13 vowels (अ-अः)', 'सभी 13 स्वर (अ-अः) पहचानता है', 1, 'observed'),
('L1.3.1.b', 'L1.3.1', 'Recognises consonants क-ड group', 'व्यंजन क-ड वर्ग पहचानता है', 2, 'observed'),
('L1.3.1.c', 'L1.3.1', 'Recognises consonants ण-ह and क्ष/त्र/ज्ञ', 'व्यंजन ण-ह और क्ष/त्र/ज्ञ पहचानता है', 3, 'observed'),

-- L1.3.2: Basic matras — the most diagnostic decoding milestone
('L1.3.2.a', 'L1.3.2', 'Reads consonant + ा (aa matra) combinations', 'व्यंजन + ा (आ की मात्रा) पढ़ता है', 1, 'observed'),
('L1.3.2.b', 'L1.3.2', 'Reads consonant + ि (chhoti i matra) combinations', 'व्यंजन + ि (छोटी इ की मात्रा) पढ़ता है', 2, 'observed'),
('L1.3.2.c', 'L1.3.2', 'Reads consonant + ी (badi ee matra) combinations', 'व्यंजन + ी (बड़ी ई की मात्रा) पढ़ता है', 3, 'observed'),
('L1.3.2.d', 'L1.3.2', 'Reads consonant + ु (chhota u matra) combinations', 'व्यंजन + ु (छोटा उ की मात्रा) पढ़ता है', 4, 'observed'),
('L1.3.2.e', 'L1.3.2', 'Reads consonant + ू (bada oo matra) combinations', 'व्यंजन + ू (बड़ा ऊ की मात्रा) पढ़ता है', 5, 'observed'),

-- L1.3.3: Remaining matras
('L1.3.3.a', 'L1.3.3', 'Reads consonant + े (e matra) combinations', 'व्यंजन + े (ए की मात्रा) पढ़ता है', 1, 'observed'),
('L1.3.3.b', 'L1.3.3', 'Reads consonant + ै (ai matra) combinations', 'व्यंजन + ै (ऐ की मात्रा) पढ़ता है', 2, 'observed'),
('L1.3.3.c', 'L1.3.3', 'Reads consonant + ो (o matra) combinations', 'व्यंजन + ो (ओ की मात्रा) पढ़ता है', 3, 'observed'),
('L1.3.3.d', 'L1.3.3', 'Reads consonant + ौ (au matra) combinations', 'व्यंजन + ौ (औ की मात्रा) पढ़ता है', 4, 'observed'),

-- L1.7.2: Word writing with matras
('L1.7.2.a', 'L1.7.2', 'Writes words with ा matra in correct position', 'ा मात्रा सही स्थान पर लिखता है', 1, 'written'),
('L1.7.2.b', 'L1.7.2', 'Writes words with ि matra before the consonant', 'ि मात्रा व्यंजन से पहले लिखता है', 2, 'written'),
('L1.7.2.c', 'L1.7.2', 'Writes words with ु/ू matras below the consonant', 'ु/ू मात्रा व्यंजन के नीचे लिखता है', 3, 'written'),
('L1.7.2.d', 'L1.7.2', 'Writes words with े/ै matras above the consonant', 'े/ै मात्रा व्यंजन के ऊपर लिखता है', 4, 'written'),

-- L2.5.1: Oral reading fluency (Grade 2)
('L2.5.1.a', 'L2.5.1', 'Reads words in connected text without sounding out each letter', 'जुड़े पाठ में शब्द बिना अक्षर-अक्षर पढ़े पढ़ता है', 1, 'oral_reading'),
('L2.5.1.b', 'L2.5.1', 'Maintains pace of ≥40 words per minute', '≥40 शब्द प्रति मिनट की गति बनाए रखता है', 2, 'oral_reading'),
('L2.5.1.c', 'L2.5.1', 'Self-corrects errors without stopping', 'बिना रुके गलतियाँ स्वयं सुधारता है', 3, 'oral_reading'),

-- L3.6.1: Inferential comprehension
('L3.6.1.a', 'L3.6.1', 'Explains why a character acted a certain way using text evidence', 'पाठ के साक्ष्य से बताता है कि पात्र ने ऐसा क्यों किया', 1, 'written'),
('L3.6.1.b', 'L3.6.1', 'Draws conclusions not explicitly stated in text', 'पाठ में स्पष्ट रूप से न कहे निष्कर्ष निकालता है', 2, 'written'),
('L3.6.1.c', 'L3.6.1', 'Identifies author''s purpose or message', 'लेखक का उद्देश्य या संदेश पहचानता है', 3, NULL),

-- L3.7.1: Paragraph composition
('L3.7.1.a', 'L3.7.1', 'Writes an opening sentence that introduces the topic', 'विषय से परिचय कराने वाला आरंभिक वाक्य लिखता है', 1, 'written'),
('L3.7.1.b', 'L3.7.1', 'Writes 3-4 body sentences with supporting details', '3-4 मुख्य वाक्य विवरण सहित लिखता है', 2, 'written'),
('L3.7.1.c', 'L3.7.1', 'Writes a closing sentence', 'समापन वाक्य लिखता है', 3, 'written'),
('L3.7.1.d', 'L3.7.1', 'Uses connectors (फिर, इसलिए, लेकिन) between sentences', 'वाक्यों के बीच योजक (फिर, इसलिए, लेकिन) का प्रयोग करता है', 4, 'written');
