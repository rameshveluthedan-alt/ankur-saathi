-- ============================================================================
-- ANKUR SAATHI — Layer 1 KB: R1 Literacy (Hindi) Seed Data
-- Part 3: Misconception Taxonomy
-- ============================================================================
-- Hindi literacy misconceptions are distinct from English literacy.
-- Key areas: matra confusion (unique to Devanagari), conjunct errors,
-- schwa deletion, letter-shape confusion, and comprehension gaps.
-- Assessment channels: decoding/word reading → observed; writing → written/photo;
-- fluency → oral_reading (teacher stopwatch); comprehension → written/observed.
-- ============================================================================

INSERT INTO misconceptions (id, competency_id, name_en, name_hi, error_pattern, diagnostic_indicator, example_correct, example_incorrect, intervention_strategy, intervention_template_ids, severity, frequency, sort_order) VALUES

-- ============================================================================
-- LETTER RECOGNITION MISCONCEPTIONS
-- ============================================================================

('L0.3.1-M1', 'L0.3.1',
 'Confuses visually similar letters (ख/रव, ध/घ, म/भ, श/स)',
 'दिखने में मिलते-जुलते अक्षरों में भ्रम (ख/रव, ध/घ, म/भ, श/स)',
 'Child confuses letter pairs that share visual features in Devanagari script',
 'Consistently misidentifies specific letter pairs; other letters are correct. Common pairs: ख↔रव, ध↔घ, म↔भ, श↔स, ब↔व',
 'ख → "kha"',
 'ख → reads as "ra" (confusing with रव shape)',
 'Teach contrastive pairs: show both letters side by side, highlight the distinguishing stroke. Use colour to mark the difference. Tactile tracing of the distinguishing feature.',
 ARRAY['INT-LIT-001'], 'critical', 'very_common', 1),

('L0.3.1-M2', 'L0.3.1',
 'Recognises letters only in sequence, not randomly',
 'अक्षर केवल क्रम में पहचानता है, बेतरतीब में नहीं',
 'Child can recite the varnamala in order but cannot identify individual letters when shown randomly',
 'Fast when pointing along a chart in sequence; very slow or wrong when shown flashcards in random order',
 'Random card: घ → "gha" (instant)',
 'Random card: घ → recites "क, ख, ग, घ..." to reach it',
 'Flash card practice in random order. Letter bingo game. "Point to the letter I say" exercises with scattered letters.',
 ARRAY['INT-LIT-001'], 'moderate', 'common', 2),

-- ============================================================================
-- MATRA MISCONCEPTIONS — THE CORE HINDI LITERACY DIAGNOSTIC AREA
-- ============================================================================

('L1.3.2-M1', 'L1.3.2',
 'Confuses छोटी इ (ि) and बड़ी ई (ी) matras',
 'छोटी इ (ि) और बड़ी ई (ी) मात्रा में भ्रम',
 'Child confuses the short-i and long-i matra — reads कि as की or vice versa',
 'Errors specifically on ि/ी distinction; other matras are read correctly. Inconsistent — sometimes correct, sometimes swapped.',
 'किला → "kila" (fort)',
 'किला → reads as "keela" (nail) — confusing ि with ी',
 'Contrastive minimal pairs: किला/कीला, दिन/दीन. Emphasise: छोटी इ = short sound, written BEFORE the letter; बड़ी ई = long sound, written AFTER. Physical: short tap for ि, long tap for ी.',
 ARRAY['INT-LIT-002'], 'critical', 'very_common', 1),

('L1.3.2-M2', 'L1.3.2',
 'Confuses छोटा उ (ु) and बड़ा ऊ (ू) matras',
 'छोटा उ (ु) और बड़ा ऊ (ू) मात्रा में भ्रम',
 'Child confuses the short-u and long-u matra — reads कुल as कूल or vice versa',
 'Errors specifically on ु/ू distinction; reads both as the same vowel sound',
 'कुल → "kul" (total), कूल → "kool" (cool)',
 'कुल → reads as "kool" — cannot distinguish length',
 'Minimal pairs: सुख/सूख, पुल/पूल. Audio drill: teacher says short-u and long-u, child points to correct matra. Written practice with circling the correct matra in words.',
 ARRAY['INT-LIT-002'], 'critical', 'very_common', 2),

('L1.3.2-M3', 'L1.3.2',
 'Reads matra but adds it to wrong consonant in a word',
 'मात्रा पढ़ता है पर शब्द में गलत व्यंजन पर लगाता है',
 'In a multi-consonant word, child applies the matra to the wrong consonant',
 'When reading कमल + ा matra: reads कामल instead of कमाल. Pattern: matra migrates to first consonant.',
 'कमाल → ka-maal',
 'कमाल → kaa-mal (matra migrates to first consonant)',
 'Finger-point reading: point to each akshar-matra unit. Circle the consonant that "owns" the matra. Syllable-by-syllable reading with explicit matra attachment.',
 ARRAY['INT-LIT-002'], 'moderate', 'common', 3),

('L1.3.3-M1', 'L1.3.3',
 'Confuses े (e) and ै (ai) matras',
 'े (ए) और ै (ऐ) मात्रा में भ्रम',
 'Child confuses the e and ai matras — they look similar (one vs two ticks above shirorekha)',
 'Reads words with े/ै interchangeably; specifically: reads मेला as मैला or vice versa',
 'मेला → "mela" (fair)',
 'मेला → reads as "maila" (dirty)',
 'Visual contrast: "े has ONE line, ै has TWO lines. ONE = ए sound, TWO = ऐ sound." Highlight with colour in worksheets. Minimal pairs: मेल/मैल, सेर/सैर.',
 ARRAY['INT-LIT-002'], 'critical', 'very_common', 1),

('L1.3.3-M2', 'L1.3.3',
 'Confuses ो (o) and ौ (au) matras',
 'ो (ओ) और ौ (औ) मात्रा में भ्रम',
 'Child confuses the o and au matras — ो has one element, ौ has an additional tick',
 'Reads words with ो/ौ interchangeably; reads गोल as गौल or vice versa',
 'मोर → "mor" (peacock)',
 'मोर → reads as "maur"',
 'Same strategy as े/ै: "ो has ा + े (two parts), ौ has ा + ै (three parts — extra tick)." Colour-code the distinguishing element.',
 ARRAY['INT-LIT-002'], 'critical', 'very_common', 2),

-- ============================================================================
-- WORD READING / DECODING MISCONCEPTIONS
-- ============================================================================

('L1.3.4-M1', 'L1.3.4',
 'Decodes letters individually but cannot blend into word',
 'अक्षर अलग-अलग पढ़ता है पर शब्द में जोड़ नहीं पाता',
 'Child correctly identifies each letter/matra but cannot blend them into a spoken word',
 'Says "क-म-ल" but cannot say "कमल" — the blending step fails',
 'क-म-ल → "kamal"',
 'क-म-ल → "ka... ma... la..." (stays segmented)',
 'Successive blending: "Say क. Now add म: कम. Now add ल: कमल." Start with 2-sound words, build to 3. Use sliding finger under the word to prompt continuous blending.',
 ARRAY['INT-LIT-003'], 'critical', 'very_common', 1),

('L1.3.4-M2', 'L1.3.4',
 'Guesses word from first letter instead of decoding',
 'डिकोड करने की बजाय पहले अक्षर से शब्द अनुमान लगाता है',
 'Child looks at the first letter and guesses a familiar word starting with that letter instead of reading the actual word',
 'Reads कमल as "कमरा" or "काम" — guesses a known word starting with क instead of decoding',
 'कमल → "kamal"',
 'कमल → "kamra" (guesses a more familiar word starting with क)',
 'Cover the word, reveal one akshar at a time. Insist on full decoding. Use nonsense words (pseudowords) to eliminate guessing strategy.',
 ARRAY['INT-LIT-003'], 'moderate', 'common', 2),

-- ============================================================================
-- CONJUNCT CONSONANT MISCONCEPTIONS (Grade 2)
-- ============================================================================

('L2.3.1-M1', 'L2.3.1',
 'Reads conjunct consonants as separate letters',
 'संयुक्त अक्षरों को अलग-अलग पढ़ता है',
 'Child does not recognise the conjunct form — reads the component letters separately (e.g., reads प्र as प-र)',
 'Breaks down conjuncts into component letters consistently; reads विद्यालय as "vi-da-ya-la-ya" instead of "vidyalay"',
 'विद्यालय → "vidyaalay"',
 'विद्यालय → "vi-da-ya-aa-la-ya" (ignores conjunct)',
 'Teach common conjuncts explicitly as new "letters": क्ष, त्र, ज्ञ, श्र, द्य, etc. Flash cards with the conjunct form and its sound. Reading practice with conjunct-heavy words.',
 ARRAY['INT-LIT-004'], 'critical', 'very_common', 1),

('L2.3.1-M2', 'L2.3.1',
 'Adds schwa (inherent अ) where conjunct should suppress it',
 'संयुक्त अक्षर में जहाँ ध्वनि लुप्त होनी चाहिए वहाँ अ जोड़ता है',
 'Child adds the inherent vowel between consonants that should be conjuncted (schwa insertion)',
 'Reads विद्या as "vidayaa" instead of "vidyaa" — inserts schwa between द and य',
 'विद्या → "vid-yaa"',
 'विद्या → "vi-da-yaa" (inserts schwa)',
 'Explain: "When two consonants join (संयुक्त), the first one loses its अ sound. They become one sound together." Practise with common clusters: प्र, स्त, न्द.',
 ARRAY['INT-LIT-004'], 'critical', 'common', 2),

-- ============================================================================
-- READING FLUENCY MISCONCEPTIONS
-- ============================================================================

('L2.5.1-M1', 'L2.5.1',
 'Word-by-word reading without phrasing',
 'वाक्यांश बनाए बिना शब्द-दर-शब्द पढ़ना',
 'Child reads each word as an isolated unit with a pause between every word — no connected phrasing',
 'CWPM may be adequate but reading sounds robotic; equal pause between all words regardless of meaning units',
 'राम ने बाज़ार से आम खरीदे → natural phrasing: "राम ने / बाज़ार से / आम खरीदे"',
 'राम...ने...बाज़ार...से...आम...खरीदे (equal pause between every word)',
 'Model phrased reading: teacher reads a sentence in phrases, child echoes. Mark phrase boundaries with slashes in text. Start with short phrases (2-3 words), build up.',
 ARRAY['INT-LIT-005'], 'moderate', 'very_common', 1),

('L2.5.1-M2', 'L2.5.1',
 'Reads accurately but extremely slowly (below CWPM threshold)',
 'शुद्ध पढ़ता है पर बहुत धीमे (CWPM सीमा से कम)',
 'Child reads every word correctly but decodes each word, never builds automaticity',
 'Accuracy ≥90% but CWPM consistently below 25; child is still sounding out known words',
 NULL, NULL,
 'This is a fluency-building issue, not an accuracy issue. Prescribe: repeated reading of the same passage 3-4 times; sight word drills for high-frequency words; paired reading with a fluent peer.',
 ARRAY['INT-LIT-005'], 'moderate', 'common', 2),

('L2.5.1-M3', 'L2.5.1',
 'Reads fast but with frequent errors (speed over accuracy)',
 'तेज़ पढ़ता है पर बार-बार गलतियाँ (गति शुद्धता पर भारी)',
 'Child reads quickly but skips words, substitutes similar-looking words, or misreads matras',
 'CWPM ≥40 but accuracy below 85%; errors are substitutions and skips rather than slow decoding',
 NULL, NULL,
 'Slow down: use a finger or pointer to track each word. Accuracy-first reading: read a sentence correctly before moving to the next. Reward accuracy, not speed.',
 ARRAY['INT-LIT-005'], 'moderate', 'common', 3),

-- ============================================================================
-- WRITING MISCONCEPTIONS
-- ============================================================================

('L1.7.2-M1', 'L1.7.2',
 'Places ि (chhoti i) matra on wrong side of consonant',
 'ि (छोटी इ) मात्रा व्यंजन के गलत तरफ रखता है',
 'Child writes ि to the right of the consonant instead of the left (e.g., writes कि as क + ि on right)',
 'ि matra consistently placed after the consonant in handwriting; other matras placed correctly',
 'कि → ि is written to the LEFT of क',
 'कि → writes ि to the RIGHT of क (looks like क + ि)',
 'This is the single most common Hindi writing error. Explicit rule: "छोटी इ is the ONLY matra that goes BEFORE (left of) the consonant. All others go after/above/below." Practice with highlighting left-placement in red.',
 ARRAY['INT-LIT-006'], 'critical', 'very_common', 1),

('L1.7.2-M2', 'L1.7.2',
 'Writes the vowel letter instead of the matra sign',
 'मात्रा चिह्न की बजाय स्वर अक्षर लिखता है',
 'Child writes the full vowel letter (ई) instead of the matra form (ी) when adding vowel to consonant',
 'Writes "क + ई" as two separate characters instead of "की" as one unit',
 'की → single akshar with ी matra',
 'की → writes क then ई as separate letters',
 'Teach: "When a vowel JOINS a consonant, it changes form — it becomes a matra. ई becomes ी, उ becomes ु." Chart showing vowel → matra transformation. Practice converting.',
 ARRAY['INT-LIT-006'], 'critical', 'common', 2),

('L1.7.2-M3', 'L1.7.2',
 'Missing shirorekha (headline) in written words',
 'लिखित शब्दों में शिरोरेखा छूटना',
 'Child writes letters correctly but does not connect them with the shirorekha (the horizontal line that connects Devanagari letters in a word)',
 'All letters are individually correct but float without the connecting headline; word looks like separate letters',
 'कमल → connected with shirorekha as one unit',
 'कमल → letters written separately without headline connection',
 'Teach shirorekha as the final step: "Write all your letters, THEN draw the line on top connecting them into one word." Practice with dotted shirorekha to trace.',
 ARRAY['INT-LIT-006'], 'minor', 'common', 3),

-- ============================================================================
-- COMPREHENSION MISCONCEPTIONS
-- ============================================================================

('L2.6.1-M1', 'L2.6.1',
 'Decodes text correctly but does not understand what was read',
 'पाठ सही पढ़ता है पर समझता नहीं',
 'Child reads the passage aloud accurately but cannot answer any questions — decoding without comprehension',
 'CWPM and accuracy are adequate, but answers to literal questions are wrong or "I don''t know." This is the classic "word caller" pattern.',
 NULL, NULL,
 'Stop-and-check: pause after every 2 sentences and ask "What just happened?" Build the habit of meaning-making during reading. Reduce passage length. Pre-teach key vocabulary before reading.',
 ARRAY['INT-LIT-007'], 'critical', 'common', 1),

('L2.6.2-M1', 'L2.6.2',
 'Gives a detail instead of the main idea',
 'मुख्य विचार की बजाय कोई विवरण बताता है',
 'When asked for the main idea, child gives a specific detail from the passage instead of the central message',
 'Response is factually correct but is a detail, not the main idea: "The boy had a red ball" instead of "A boy learns to share"',
 NULL, NULL,
 'Teach: "The main idea answers: What is this WHOLE passage about in ONE sentence?" Practice: give child 3 options (1 main idea + 2 details) and ask which one covers the whole story.',
 ARRAY['INT-LIT-007'], 'moderate', 'very_common', 1),

('L3.6.1-M1', 'L3.6.1',
 'Gives literal answer to inferential question',
 'अनुमानात्मक प्रश्न का तथ्यात्मक उत्तर देता है',
 'When asked "why" or "how", child quotes a sentence from the text instead of reasoning',
 'Response is a copy from the text, not a reasoned answer. E.g., "Why was Ram sad?" → "Ram went home" (quotes text) instead of "Because his friend moved away" (infers)',
 NULL, NULL,
 'Model think-aloud: "The text says Ram went home alone. I think he felt sad because his friend moved. The text doesn''t SAY sad, but I can THINK it." Teach: "Look for clues, then think."',
 ARRAY['INT-LIT-008'], 'moderate', 'very_common', 1),

('L3.6.1-M2', 'L3.6.1',
 'Makes inferences unrelated to text (uses only personal knowledge)',
 'पाठ से असंबंधित अनुमान लगाता है (केवल अपना ज्ञान प्रयोग करता है)',
 'Child ignores text evidence and answers based entirely on personal experience or world knowledge',
 'Answer is plausible in general but contradicted by or unsupported by the specific text',
 NULL, NULL,
 'Teach text-evidence habit: "Point to the sentence that makes you think so." If child cannot point to evidence, help find it. Rule: "The answer must come from the text + your thinking, not just your thinking."',
 ARRAY['INT-LIT-008'], 'moderate', 'common', 2);
