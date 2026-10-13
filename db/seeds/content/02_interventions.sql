-- ============================================================================
-- ANKUR SAATHI — Layer 2 Seed: Intervention Templates
-- Each maps to specific L1 misconception IDs — deterministic retrieval
-- ============================================================================

INSERT INTO intervention_templates (id, title_en, title_hi, description_en, misconception_ids, competency_ids, steps, target_level, modality, domain_id, duration_minutes, requires_tlm, tlm_ids, group_size, source) VALUES

-- ============================================================================
-- NUMERACY INTERVENTIONS
-- ============================================================================

('INT-NUM-001', 'One-to-one Counting Fix', 'एक-एक गिनती सुधार',
 'Fixes double-counting and skipping errors using structured line-up counting with physical movement of objects.',
 ARRAY['N0.2.2-M1','N0.2.2-M2'], ARRAY['N0.2.2'],
 '[
   {"step":1,"type":"demonstrate","instruction_en":"Line up 7 objects in a row. Touch and move each one to a counted pile while saying the number. Emphasise: one touch, one count, one move.","instruction_hi":"7 वस्तुओं को कतार में रखें। हर एक को छूकर गिनती कहते हुए दूसरी तरफ़ रखें। ज़ोर दें: एक छुअन, एक गिनती, एक हटाव।","duration_min":3},
   {"step":2,"type":"guided_practice","instruction_en":"Child counts 5 objects using the touch-and-move method. Teacher watches for double-touches or skips.","instruction_hi":"बच्चा 5 वस्तुओं को छूकर हटाते हुए गिने। शिक्षक दोहरी छुअन या छोड़ने पर ध्यान दें।","duration_min":4},
   {"step":3,"type":"check","instruction_en":"Give 8 scattered objects (not in a line). Can the child count correctly by moving each to a pile?","instruction_hi":"8 बिखरी वस्तुएँ दें (कतार में नहीं)। क्या बच्चा हर वस्तु हटाकर सही गिन पाता है?","duration_min":3}
 ]'::jsonb, 'beginner', 'hands_on', 'numeracy', 10, FALSE, NULL, 'small', 'original'),

('INT-NUM-002', 'Cardinality Builder', 'गणनांक निर्माण',
 'Builds cardinality understanding — the last number counted IS the total.',
 ARRAY['N0.2.2-M3'], ARRAY['N0.2.2'],
 '[
   {"step":1,"type":"demonstrate","instruction_en":"Count 6 objects together. After counting, hold up 6 fingers and say emphatically: SIX. There are SIX. Cover the objects. How many are hiding? SIX.","instruction_hi":"6 वस्तुएँ साथ गिनें। गिनने के बाद 6 उंगलियाँ दिखाएँ: छह! यहाँ छह हैं। वस्तुएँ ढकें। कितनी छिपी हैं? छह!","duration_min":3},
   {"step":2,"type":"guided_practice","instruction_en":"Child counts a set. Teacher asks: How many? If child recounts, stop and say: You just said FIVE. Five IS how many. You dont need to count again.","instruction_hi":"बच्चा गिने। शिक्षक: कितने? अगर दोबारा गिने, रोकें: तुमने अभी पाँच कहा। पाँच ही जवाब है। दोबारा गिनने की ज़रूरत नहीं।","duration_min":4},
   {"step":3,"type":"check","instruction_en":"Count 3 different quantities. For each: cover and ask how many. Child must answer without recounting.","instruction_hi":"3 अलग-अलग मात्राएँ गिनें। हर बार ढककर पूछें: कितने? बच्चा बिना गिने बताए।","duration_min":3}
 ]'::jsonb, 'beginner', 'hands_on', 'numeracy', 10, FALSE, NULL, 'small', 'original'),

('INT-PV-001', 'Place Value with Bundling Sticks', 'बंडल से स्थानीय मान',
 'Rebuilds place value understanding through physical bundling. Addresses digit-as-independent-number and tens/ones reversal.',
 ARRAY['N1.2.4-M1','N1.2.4-M2','N2.2.2-M2'], ARRAY['N1.2.4','N2.2.2'],
 '[
   {"step":1,"type":"demonstrate","instruction_en":"Show 23 loose sticks. Count all: 23. Now bundle into groups of 10: 2 bundles, 3 loose. Place on T|O chart. The 2 doesnt mean TWO, it means TWO TENS which is TWENTY.","instruction_hi":"23 खुली छड़ियाँ दिखाएँ। गिनें: 23। अब 10-10 के बंडल बनाएँ: 2 बंडल, 3 खुली। T|O चार्ट पर रखें। 2 का मतलब दो नहीं, दो दहाई यानी बीस।","duration_min":4},
   {"step":2,"type":"guided_practice","instruction_en":"Give child 45 sticks. Bundle together. Write on T|O chart. Unbundle and rebuild for 3 different numbers. Each time ask: What does the tens digit MEAN?","instruction_hi":"बच्चे को 45 छड़ियाँ दें। साथ बंडल बनाएँ। T|O चार्ट पर लिखें। 3 अलग संख्याओं के लिए खोलें-बाँधें। हर बार पूछें: दहाई का अंक क्या बताता है?","duration_min":5},
   {"step":3,"type":"check","instruction_en":"Say a number. Child builds with sticks AND writes expanded form. Check: 34 = 30 + 4, NOT 3 + 4.","instruction_hi":"एक संख्या बोलें। बच्चा छड़ियों से बनाए और विस्तारित रूप लिखे। जाँचें: 34 = 30 + 4, न कि 3 + 4।","duration_min":3}
 ]'::jsonb, 'beginner', 'hands_on', 'numeracy', 12, TRUE, ARRAY['TLM-001','TLM-005'], 'small', 'original'),

('INT-OP-005', 'Carry-over Re-teaching with Bundling', 'हासिल पुनःशिक्षण (बंडल से)',
 'Addresses carry-over misconceptions in 2-digit addition: dropping carry, writing full sum, carrying wrong digit.',
 ARRAY['N2.3.2-M1','N2.3.2-M2','N2.3.2-M3','N2.3.2-M4'], ARRAY['N2.3.2'],
 '[
   {"step":1,"type":"demonstrate","instruction_en":"Write 34 + 28 on board. Build with sticks: 3 bundles + 4 loose, and 2 bundles + 8 loose. Combine ones: 4 + 8 = 12 loose sticks. Too many for ones! Bundle 10 into a new bundle. Move it to tens column. Write: 2 in ones, carry 1 to tens.","instruction_hi":"34 + 28 बोर्ड पर लिखें। छड़ियों से बनाएँ। इकाई मिलाएँ: 4 + 8 = 12 खुली छड़ियाँ। बहुत ज़्यादा! 10 का नया बंडल बनाएँ। दहाई में रखें। लिखें: इकाई में 2, दहाई में 1 हासिल।","duration_min":4},
   {"step":2,"type":"guided_practice","instruction_en":"Child solves 3 problems with sticks alongside written work. For EACH: ones first, bundle if needed, THEN tens. Teacher watches for the specific error pattern this child makes.","instruction_hi":"बच्चा 3 सवाल छड़ियों और लिखित दोनों से हल करे। हर बार: पहले इकाई, बंडल बनाएँ अगर ज़रूरत, फिर दहाई। शिक्षक बच्चे की विशिष्ट गलती पर ध्यान दें।","duration_min":5},
   {"step":3,"type":"check","instruction_en":"Two problems WITHOUT sticks (just written). Check: Is carry present? Is only ones digit in ones column? Is carry added to tens?","instruction_hi":"दो सवाल बिना छड़ियों के (केवल लिखित)। जाँचें: क्या हासिल है? इकाई में एक ही अंक? हासिल दहाई में जुड़ा?","duration_min":3}
 ]'::jsonb, 'beginner', 'mixed', 'numeracy', 12, TRUE, ARRAY['TLM-001'], 'small', 'original'),

('INT-OP-006', 'Borrowing Re-teaching: Break the Ten', 'उधार पुनःशिक्षण: दहाई तोड़ो',
 'Addresses subtraction borrowing errors: smaller-from-larger reversal, forgetting to reduce tens.',
 ARRAY['N2.3.4-M1','N2.3.4-M2','N2.3.4-M3'], ARRAY['N2.3.4'],
 '[
   {"step":1,"type":"demonstrate","instruction_en":"Write 42 - 17. Build 42 with sticks: 4 bundles + 2 loose. Try to take away 7 from ones: you only have 2! Break open 1 bundle: now you have 3 bundles + 12 loose. Cross out 4, write 3. Cross out 2, write 12. Now subtract: 12-7=5, 3-1=2. Answer: 25.","instruction_hi":"42 - 17 लिखें। 42 छड़ियों से बनाएँ: 4 बंडल + 2 खुली। इकाई से 7 निकालो: सिर्फ़ 2 हैं! 1 बंडल तोड़ो: अब 3 बंडल + 12 खुली। 4 काटो, 3 लिखो। 2 काटो, 12 लिखो। अब घटाओ: 12-7=5, 3-1=2। उत्तर: 25।","duration_min":4},
   {"step":2,"type":"guided_practice","instruction_en":"CRITICAL CHECK before each problem: Look at ones. Top number bigger or smaller than bottom? Bigger = just subtract. Smaller = must borrow. Child states this check aloud before solving.","instruction_hi":"हर सवाल से पहले जाँच: इकाई देखो। ऊपर वाला बड़ा या छोटा? बड़ा = सीधे घटाओ। छोटा = उधार लो। बच्चा ज़ोर से बोलकर जाँच करे।","duration_min":5},
   {"step":3,"type":"check","instruction_en":"Mix: 2 problems needing borrow + 1 NOT needing borrow. Child must correctly decide which need borrowing.","instruction_hi":"मिश्रित: 2 उधार वाले + 1 बिना उधार। बच्चा सही पहचाने कि किसमें उधार चाहिए।","duration_min":3}
 ]'::jsonb, 'beginner', 'mixed', 'numeracy', 12, TRUE, ARRAY['TLM-001'], 'small', 'original'),

('INT-WP-001', 'Word Problem Operation Identifier', 'शाब्दिक प्रश्न संक्रिया पहचान',
 'Builds the skill of identifying which operation a word problem requires, before computing.',
 ARRAY['N2.3.5-M1'], ARRAY['N1.3.3','N2.3.5'],
 '[
   {"step":1,"type":"demonstrate","instruction_en":"Read a problem aloud. Do NOT solve yet. Ask: Did the person END UP WITH MORE or LESS? More = addition. Less = subtraction. Act it out with objects.","instruction_hi":"सवाल पढ़ें। अभी हल न करें। पूछें: अंत में ज़्यादा हुआ या कम? ज़्यादा = जोड़। कम = घटाव। वस्तुओं से करके दिखाएँ।","duration_min":3},
   {"step":2,"type":"guided_practice","instruction_en":"Give 4 word problems. For each, child ONLY writes + or - (no computation). Teacher checks operation choice before allowing computation.","instruction_hi":"4 शाब्दिक प्रश्न दें। हर एक के लिए बच्चा केवल + या - लिखे (गणना नहीं)। शिक्षक संक्रिया जाँचे, फिर गणना करने दें।","duration_min":5},
   {"step":3,"type":"check","instruction_en":"2 tricky problems where keywords mislead (e.g., how many MORE did he get = subtraction to find difference). Check operation, then answer.","instruction_hi":"2 पेचीदा सवाल जहाँ शब्द भ्रमित करें। संक्रिया जाँचें, फिर उत्तर।","duration_min":3}
 ]'::jsonb, 'any', 'mixed', 'numeracy', 11, FALSE, NULL, 'small', 'original'),

('INT-OP-008', 'Multi-digit Multiplication: Grid Method', 'बहु-अंकीय गुणा: ग्रिड विधि',
 'Uses the grid/box method to prevent digit-by-digit multiplication without carrying.',
 ARRAY['N3.3.4-M1','N3.3.4-M2'], ARRAY['N3.3.4'],
 '[
   {"step":1,"type":"demonstrate","instruction_en":"23 × 4. Draw a grid: split 23 into 20 and 3. Two boxes: 20×4=80 and 3×4=12. Add: 80+12=92. The grid shows WHY we carry.","instruction_hi":"23 × 4। ग्रिड बनाएँ: 23 को 20 और 3 में तोड़ें। दो खाने: 20×4=80 और 3×4=12। जोड़ें: 80+12=92। ग्रिड दिखाता है हासिल क्यों।","duration_min":4},
   {"step":2,"type":"guided_practice","instruction_en":"Child solves 3 problems using grid method first, then checks with column method. Both must match.","instruction_hi":"बच्चा 3 सवाल पहले ग्रिड से, फिर स्तम्भ विधि से हल करे। दोनों उत्तर मिलने चाहिए।","duration_min":5},
   {"step":3,"type":"check","instruction_en":"1 problem with column method only. Check: Did child multiply (not add) the tens digit? Is carry handled correctly?","instruction_hi":"1 सवाल केवल स्तम्भ विधि से। जाँचें: बच्चे ने दहाई का गुणा (जोड़ नहीं) किया? हासिल सही है?","duration_min":3}
 ]'::jsonb, 'any', 'mixed', 'numeracy', 12, FALSE, NULL, 'small', 'original'),


-- ============================================================================
-- LITERACY INTERVENTIONS
-- ============================================================================

('INT-LIT-001', 'Letter Confusion: Contrastive Pairs', 'अक्षर भ्रम: विपरीत जोड़े',
 'Fixes visual confusion between similar Hindi letters using side-by-side comparison and tactile tracing.',
 ARRAY['L0.3.1-M1','L0.3.1-M2'], ARRAY['L0.3.1','L1.3.1'],
 '[
   {"step":1,"type":"demonstrate","instruction_en":"Write confused pair side by side (e.g., ख and रव). Circle the distinguishing stroke in red. Say: LOOK at this part — this line goes THIS way for ख, THAT way for रव.","instruction_hi":"भ्रमित जोड़ा साथ-साथ लिखें (जैसे ख और रव)। अलग करने वाली रेखा लाल से घेरें। बोलें: यहाँ देखो — ख में यह रेखा ऐसे, रव में वैसे।","duration_min":3},
   {"step":2,"type":"guided_practice","instruction_en":"Child traces both letters with finger 5 times each, saying the sound. Then: flashcards of the pair, random order, 10 times.","instruction_hi":"बच्चा दोनों अक्षर उंगली से 5-5 बार ट्रेस करे, ध्वनि बोलते हुए। फिर: जोड़े के फ्लैश कार्ड, बेतरतीब, 10 बार।","duration_min":5},
   {"step":3,"type":"check","instruction_en":"Show 8 cards mixing both letters randomly. Child must name each within 2 seconds. Target: 7/8 correct.","instruction_hi":"दोनों अक्षरों के 8 कार्ड मिलाकर दिखाएँ। बच्चा 2 सेकंड में बताए। लक्ष्य: 7/8 सही।","duration_min":3}
 ]'::jsonb, 'beginner', 'hands_on', 'r1_literacy', 11, TRUE, ARRAY['TLM-008'], 'small', 'original'),

('INT-LIT-002', 'Matra Minimal Pairs', 'मात्रा न्यूनतम जोड़े',
 'Fixes matra confusions (ि/ी, ु/ू, े/ै, ो/ौ) using minimal pair words that change meaning with the matra.',
 ARRAY['L1.3.2-M1','L1.3.2-M2','L1.3.3-M1','L1.3.3-M2'], ARRAY['L1.3.2','L1.3.3'],
 '[
   {"step":1,"type":"demonstrate","instruction_en":"Write minimal pair on board: दिन (day) / दीन (poor). Read both. The ONLY difference is the matra. Short sound vs long sound. Repeat with 2 more pairs.","instruction_hi":"बोर्ड पर न्यूनतम जोड़ा लिखें: दिन / दीन। दोनों पढ़ें। फ़र्क सिर्फ़ मात्रा है। छोटी ध्वनि बनाम बड़ी ध्वनि। 2 और जोड़ों से दोहराएँ।","duration_min":3},
   {"step":2,"type":"guided_practice","instruction_en":"Give 6 word cards. Child sorts into two piles: short matra vs long matra. Read each aloud. For writing: child writes 4 words from dictation with the target matra pair.","instruction_hi":"6 शब्द कार्ड दें। बच्चा दो ढेरों में बाँटे: छोटी मात्रा बनाम बड़ी। हर एक पढ़े। लेखन: श्रुतलेख से 4 शब्द लक्ष्य मात्रा जोड़े से लिखे।","duration_min":5},
   {"step":3,"type":"check","instruction_en":"Teacher says 4 words. Child writes each. Check: correct matra used? For reading: 4 word cards, child reads within 2 sec each.","instruction_hi":"शिक्षक 4 शब्द बोलें। बच्चा लिखे। जाँच: सही मात्रा? पठन: 4 कार्ड, 2 सेकंड में पढ़े।","duration_min":3}
 ]'::jsonb, 'beginner', 'mixed', 'r1_literacy', 11, TRUE, ARRAY['TLM-004','TLM-008'], 'small', 'original'),

('INT-LIT-003', 'Successive Blending', 'क्रमिक संश्लेषण',
 'Fixes the decoding-but-not-blending problem: child reads letters individually but cannot form the word.',
 ARRAY['L1.3.4-M1','L1.3.4-M2'], ARRAY['L1.3.4'],
 '[
   {"step":1,"type":"demonstrate","instruction_en":"Write कमल. Point to क, say क. Slide finger to म, blend: कम. Slide to ल, blend: कमल. The finger SLIDES continuously — no lifting.","instruction_hi":"कमल लिखें। क पर उंगली, बोलें क। म तक सरकाएँ: कम। ल तक: कमल। उंगली लगातार सरकती है — उठती नहीं।","duration_min":3},
   {"step":2,"type":"guided_practice","instruction_en":"5 words. Child uses finger-slide method. Start with 2-letter words (जल, फल), build to 3-letter (कमल, नगर). Teacher does it with child if needed.","instruction_hi":"5 शब्द। बच्चा उंगली-सरकाव विधि से पढ़े। 2-अक्षर से शुरू (जल, फल), फिर 3-अक्षर (कमल, नगर)। ज़रूरत हो तो शिक्षक साथ करें।","duration_min":5},
   {"step":3,"type":"check","instruction_en":"3 NEW words child hasnt seen. Can they blend without finger? If not, finger is okay — speed will come.","instruction_hi":"3 नए शब्द। बच्चा बिना उंगली पढ़ सके? न पढ़ सके तो उंगली ठीक — गति आएगी।","duration_min":3}
 ]'::jsonb, 'beginner', 'oral', 'r1_literacy', 11, FALSE, NULL, 'small', 'original'),

('INT-LIT-004', 'Conjunct Consonant Explicit Teaching', 'संयुक्त अक्षर स्पष्ट शिक्षण',
 'Teaches common conjunct consonants as new letter units, not as two separate letters.',
 ARRAY['L2.3.1-M1','L2.3.1-M2'], ARRAY['L2.3.1'],
 '[
   {"step":1,"type":"demonstrate","instruction_en":"Write विद्यालय. Circle द्य. This is NOT द + य separately. When two consonants JOIN, the first loses its अ sound. द + य = द्य (one sound). Show 5 common conjuncts as flash cards.","instruction_hi":"विद्यालय लिखें। द्य पर गोला। यह द + य अलग-अलग नहीं। जब दो व्यंजन जुड़ते हैं, पहले की अ ध्वनि जाती है। द + य = द्य। 5 सामान्य संयुक्त अक्षर फ्लैश कार्ड से दिखाएँ।","duration_min":4},
   {"step":2,"type":"guided_practice","instruction_en":"10 words with conjuncts. Child reads each. If they break the conjunct apart, teacher covers the second consonant, reads the first WITHOUT schwa, then reveals: see, they join into one sound.","instruction_hi":"10 संयुक्त अक्षर वाले शब्द। बच्चा पढ़े। अगर तोड़कर पढ़े, शिक्षक दूसरा व्यंजन ढके, पहला बिना अ पढ़ें, फिर दिखाएँ: देखो, ये मिलकर एक ध्वनि बनते हैं।","duration_min":5},
   {"step":3,"type":"check","instruction_en":"5 new words with conjuncts. Child reads without help. Target: 4/5 with conjuncts read as joined sounds.","instruction_hi":"5 नए संयुक्त अक्षर वाले शब्द। बच्चा बिना मदद पढ़े। लक्ष्य: 4/5 सही।","duration_min":3}
 ]'::jsonb, 'beginner', 'oral', 'r1_literacy', 12, TRUE, ARRAY['TLM-008'], 'small', 'original'),

('INT-LIT-005', 'Fluency Builder: Repeated Reading', 'प्रवाह निर्माण: बार-बार पठन',
 'Builds reading fluency through repeated reading of the same passage. Targets word-by-word readers and slow-but-accurate readers.',
 ARRAY['L2.5.1-M1','L2.5.1-M2'], ARRAY['L2.5.1'],
 '[
   {"step":1,"type":"demonstrate","instruction_en":"Teacher reads a 4-sentence passage with natural phrasing. Mark phrase boundaries with slashes. Read again, pointing to phrases not words.","instruction_hi":"शिक्षक 4 वाक्यों का अनुच्छेद प्राकृतिक वाक्यांशों में पढ़ें। वाक्यांश सीमाएँ / से चिह्नित करें। फिर पढ़ें, शब्दों पर नहीं वाक्यांशों पर उंगली रखकर।","duration_min":2},
   {"step":2,"type":"guided_practice","instruction_en":"Child reads same passage 3 times. After each: teacher notes CWPM. By 3rd reading, speed should improve 10-20%. Focus on phrases, not individual words.","instruction_hi":"बच्चा वही अनुच्छेद 3 बार पढ़े। हर बार: शिक्षक CWPM नोट करें। तीसरी बार 10-20% सुधार होना चाहिए। शब्दों पर नहीं, वाक्यांशों पर ध्यान।","duration_min":6},
   {"step":3,"type":"check","instruction_en":"Child reads a NEW passage of similar difficulty once. Check: Is phrasing maintained? Is speed within 10% of their 3rd-read speed on the practice passage?","instruction_hi":"बच्चा समान कठिनाई का नया अनुच्छेद एक बार पढ़े। जाँच: वाक्यांश बनाए रखा? गति अभ्यास के तीसरे पठन के 10% के भीतर?","duration_min":3}
 ]'::jsonb, 'any', 'oral', 'r1_literacy', 11, FALSE, NULL, 'individual', 'original'),

('INT-LIT-006', 'Chhoti I Matra Placement Fix', 'छोटी इ मात्रा स्थान सुधार',
 'Fixes the most common Hindi writing error: placing ि on the wrong side of the consonant.',
 ARRAY['L1.7.2-M1','L1.7.2-M2'], ARRAY['L1.7.2'],
 '[
   {"step":1,"type":"demonstrate","instruction_en":"Write कि on board. Circle ि and draw an arrow showing it goes BEFORE (left of) क. Say: छोटी इ is the ONLY matra that goes BEFORE the letter. All others go after or above or below. Write 3 examples highlighting ि position in red.","instruction_hi":"बोर्ड पर कि लिखें। ि पर गोला, तीर से दिखाएँ कि यह क से पहले (बाईं ओर) जाती है। बोलें: छोटी इ एकमात्र मात्रा है जो अक्षर से पहले लगती है। 3 उदाहरण लाल से ि स्थान दर्शाएँ।","duration_min":3},
   {"step":2,"type":"guided_practice","instruction_en":"Dictate 6 words with ि matra. Child writes each. After each word, child self-checks: Is my ि on the LEFT side? If not, cross out and rewrite.","instruction_hi":"ि मात्रा के 6 शब्द श्रुतलेख से। बच्चा लिखे। हर शब्द के बाद स्वयं जाँचे: क्या मेरी ि बाईं ओर है? नहीं तो काटकर दोबारा लिखे।","duration_min":5},
   {"step":3,"type":"check","instruction_en":"Dictate a 3-word sentence with 2 ि-matra words. Check placement without prompting self-check.","instruction_hi":"2 ि-मात्रा शब्दों वाला 3-शब्द वाक्य श्रुतलेख। बिना याद दिलाए स्थान जाँचें।","duration_min":3}
 ]'::jsonb, 'beginner', 'worksheet', 'r1_literacy', 11, FALSE, NULL, 'small', 'original'),

('INT-LIT-007', 'Stop-and-Check Comprehension', 'रुको-और-जाँचो बोध',
 'Builds meaning-making habit during reading. For word-callers who decode but do not comprehend.',
 ARRAY['L2.6.1-M1','L2.6.2-M1'], ARRAY['L2.6.1','L2.6.2'],
 '[
   {"step":1,"type":"demonstrate","instruction_en":"Read 2 sentences aloud. Stop. Say: What just happened? WHO did WHAT? Model answering in 1 sentence. If I cant answer, I re-read.","instruction_hi":"2 वाक्य पढ़ें। रुकें। बोलें: अभी क्या हुआ? किसने क्या किया? 1 वाक्य में जवाब दें। अगर जवाब न आए, दोबारा पढ़ें।","duration_min":3},
   {"step":2,"type":"guided_practice","instruction_en":"Child reads a short passage (5-6 sentences). After every 2 sentences: STOP. Teacher asks: What happened? Child answers in own words. If stuck, re-read those 2 sentences.","instruction_hi":"बच्चा छोटा अनुच्छेद (5-6 वाक्य) पढ़े। हर 2 वाक्यों के बाद रुके। शिक्षक: क्या हुआ? बच्चा अपने शब्दों में। अटके तो वे 2 वाक्य फिर पढ़े।","duration_min":5},
   {"step":3,"type":"check","instruction_en":"Child reads a new 4-sentence passage and SELF-stops after every 2 sentences without teacher prompting. Can they answer: What was the passage about?","instruction_hi":"बच्चा नया 4-वाक्य अनुच्छेद पढ़े और बिना कहे हर 2 वाक्य पर स्वयं रुके। क्या बता सकता है: अनुच्छेद किस बारे में था?","duration_min":3}
 ]'::jsonb, 'any', 'oral', 'r1_literacy', 11, FALSE, NULL, 'individual', 'original'),

('INT-LIT-008', 'Text Evidence Habit', 'पाठ साक्ष्य आदत',
 'Teaches children to point to text evidence when making inferences, not just answer from personal knowledge.',
 ARRAY['L3.6.1-M1','L3.6.1-M2'], ARRAY['L3.6.1'],
 '[
   {"step":1,"type":"demonstrate","instruction_en":"Read a passage. Ask a WHY question. Model: My answer is ___. I think this because the text says ___ (point to the sentence). Text clue + my thinking = inference.","instruction_hi":"अनुच्छेद पढ़ें। क्यों प्रश्न पूछें। दिखाएँ: मेरा जवाब ___। मुझे ऐसा लगता है क्योंकि पाठ में लिखा है ___ (वाक्य दिखाएँ)। पाठ का सुराग + मेरी सोच = अनुमान।","duration_min":3},
   {"step":2,"type":"guided_practice","instruction_en":"2 WHY/HOW questions. For each, child MUST point to the sentence in the text that gave them the clue, THEN add their thinking. Format: The text says ___, so I think ___.","instruction_hi":"2 क्यों/कैसे प्रश्न। हर एक के लिए बच्चा पाठ में सुराग वाला वाक्य दिखाए, फिर अपनी सोच जोड़े। ढाँचा: पाठ में लिखा है ___, इसलिए मुझे लगता है ___।","duration_min":5},
   {"step":3,"type":"check","instruction_en":"1 new inference question. Child writes answer using the format. Check: Is text evidence cited? Is reasoning connected to the evidence?","instruction_hi":"1 नया अनुमान प्रश्न। बच्चा ढाँचे से लिखे। जाँच: पाठ साक्ष्य दिया? तर्क साक्ष्य से जुड़ा?","duration_min":3}
 ]'::jsonb, 'progressor', 'mixed', 'r1_literacy', 11, FALSE, NULL, 'small', 'original');


-- Populate search_text
UPDATE intervention_templates SET search_text = to_tsvector('simple',
    title_en || ' ' || description_en || ' ' ||
    array_to_string(misconception_ids, ' ') || ' ' ||
    array_to_string(competency_ids, ' ')
);
