-- ============================================================================
-- ANKUR SAATHI — Layer 2 Seed: Graded Hindi Reading Passages
-- Vocabulary-controlled, culturally relevant, with comprehension questions
-- ============================================================================

INSERT INTO reading_passages (id, title_hi, passage_hi, word_count, target_grade, difficulty, decoding_features, sight_word_percentage, expected_cwpm, comprehension_questions, fluency_competency_id, comprehension_competency_ids, theme, setting, genre, source) VALUES

-- Grade 1: Simple sentences, basic matras only
('RP-001', 'मेरा घर',
 'मेरा घर गाँव में है। घर के पास एक पेड़ है। पेड़ पर चिड़िया बैठी है। चिड़िया गाना गाती है। मुझे चिड़िया का गाना अच्छा लगता है।',
 30, 'grade_1', 'easy',
 ARRAY['basic_matras'], 75,
 '{"achieved":{"min":25},"partially_achieved":{"min":15,"max":24},"not_achieved":{"max":14}}'::jsonb,
 '[{"type":"literal","question_hi":"घर कहाँ है?","answer_hi":"गाँव में"},{"type":"literal","question_hi":"पेड़ पर कौन बैठी है?","answer_hi":"चिड़िया"},{"type":"literal","question_hi":"चिड़िया क्या करती है?","answer_hi":"गाना गाती है"}]'::jsonb,
 'L1.5.1', ARRAY['L1.6.1'], 'family', 'rural', 'narrative', 'original'),

('RP-002', 'बिल्ली और दूध',
 'एक बिल्ली थी। उसका नाम मोती था। मोती को दूध बहुत पसंद था। एक दिन मोती ने दूध का कटोरा देखा। मोती ने सारा दूध पी लिया। मोती बहुत खुश हुई।',
 36, 'grade_1', 'medium',
 ARRAY['basic_matras','all_matras'], 65,
 '{"achieved":{"min":25},"partially_achieved":{"min":15,"max":24},"not_achieved":{"max":14}}'::jsonb,
 '[{"type":"literal","question_hi":"बिल्ली का नाम क्या था?","answer_hi":"मोती"},{"type":"literal","question_hi":"मोती को क्या पसंद था?","answer_hi":"दूध"},{"type":"inferential","question_hi":"मोती खुश क्यों हुई?","answer_hi":"क्योंकि उसने दूध पी लिया"}]'::jsonb,
 'L1.5.1', ARRAY['L1.6.1'], 'animals', 'universal', 'narrative', 'original'),

('RP-003', 'मेरा स्कूल',
 'मेरा स्कूल घर से पास है। मैं रोज़ पैदल जाता हूँ। स्कूल में मेरे बहुत दोस्त हैं। हम साथ में खेलते हैं। हम साथ में पढ़ते हैं। मुझे स्कूल जाना अच्छा लगता है।',
 38, 'grade_1', 'medium',
 ARRAY['basic_matras','all_matras'], 70,
 '{"achieved":{"min":25},"partially_achieved":{"min":15,"max":24},"not_achieved":{"max":14}}'::jsonb,
 '[{"type":"literal","question_hi":"स्कूल कहाँ है?","answer_hi":"घर से पास"},{"type":"literal","question_hi":"बच्चा स्कूल कैसे जाता है?","answer_hi":"पैदल"},{"type":"literal","question_hi":"स्कूल में क्या करते हैं?","answer_hi":"खेलते और पढ़ते हैं"}]'::jsonb,
 'L1.5.1', ARRAY['L1.6.1'], 'school', 'universal', 'narrative', 'original'),

-- Grade 2: Longer passages, conjuncts, more complex vocabulary
('RP-004', 'किसान और बारिश',
 'रामू एक किसान है। वह रोज़ सुबह खेत में जाता है। इस साल बारिश बहुत कम हुई। रामू की फ़सल सूखने लगी। रामू बहुत चिंतित था। एक दिन आसमान में काले बादल आए। ज़ोर की बारिश हुई। रामू ने ख़ुशी से नाचना शुरू किया। अब उसकी फ़सल बच जाएगी।',
 55, 'grade_2', 'easy',
 ARRAY['basic_matras','all_matras','conjuncts'], 55,
 '{"achieved":{"min":40},"partially_achieved":{"min":25,"max":39},"not_achieved":{"max":24}}'::jsonb,
 '[{"type":"literal","question_hi":"रामू क्या काम करता है?","answer_hi":"किसानी / खेती"},{"type":"literal","question_hi":"बारिश कैसी हुई इस साल?","answer_hi":"बहुत कम"},{"type":"inferential","question_hi":"रामू ने नाचना क्यों शुरू किया?","answer_hi":"क्योंकि बारिश हुई और अब फ़सल बच जाएगी"},{"type":"main_idea","question_hi":"इस कहानी का मुख्य विचार क्या है?","answer_hi":"किसान के लिए बारिश कितनी ज़रूरी है"}]'::jsonb,
 'L2.5.1', ARRAY['L2.6.1','L2.6.2'], 'farm', 'rural', 'narrative', 'original'),

('RP-005', 'चिड़ियाघर की सैर',
 'कल हम स्कूल से चिड़ियाघर गए। वहाँ बहुत सारे जानवर थे। हमने शेर देखा। शेर बहुत बड़ा था। उसकी दहाड़ सुनकर सब डर गए। फिर हमने हाथी देखा। हाथी सूँड से पानी फेंक रहा था। बंदर पेड़ पर कूद रहे थे। सबसे अच्छा मुझे तोता लगा। तोता हरे रंग का था और बोलता भी था। चिड़ियाघर में बहुत मज़ा आया।',
 72, 'grade_2', 'medium',
 ARRAY['basic_matras','all_matras','conjuncts'], 50,
 '{"achieved":{"min":40},"partially_achieved":{"min":25,"max":39},"not_achieved":{"max":24}}'::jsonb,
 '[{"type":"literal","question_hi":"बच्चे कहाँ गए?","answer_hi":"चिड़ियाघर"},{"type":"literal","question_hi":"हाथी क्या कर रहा था?","answer_hi":"सूँड से पानी फेंक रहा था"},{"type":"literal","question_hi":"बच्चे को सबसे अच्छा कौन सा जानवर लगा?","answer_hi":"तोता"},{"type":"inferential","question_hi":"सब डर क्यों गए?","answer_hi":"शेर की दहाड़ सुनकर"}]'::jsonb,
 'L2.5.1', ARRAY['L2.6.1','L2.6.3'], 'animals', 'universal', 'narrative', 'original'),

('RP-006', 'पानी बचाओ',
 'पानी हमारे जीवन के लिए बहुत ज़रूरी है। हम पानी पीते हैं, खाना बनाते हैं और नहाते हैं। किसान खेती के लिए पानी का उपयोग करते हैं। लेकिन धरती पर साफ़ पानी सीमित है। हमें पानी बचाना चाहिए। नल को खुला मत छोड़ो। बारिश का पानी इकट्ठा करो। अगर हम पानी नहीं बचाएँगे तो आने वाले समय में पानी की बहुत कमी होगी।',
 72, 'grade_2', 'hard',
 ARRAY['basic_matras','all_matras','conjuncts','chandrabindu'], 40,
 '{"achieved":{"min":40},"partially_achieved":{"min":25,"max":39},"not_achieved":{"max":24}}'::jsonb,
 '[{"type":"literal","question_hi":"पानी किन-किन कामों में लगता है?","answer_hi":"पीने, खाना बनाने, नहाने और खेती में"},{"type":"main_idea","question_hi":"इस अनुच्छेद का मुख्य संदेश क्या है?","answer_hi":"पानी बचाना ज़रूरी है"},{"type":"inferential","question_hi":"लेखक ने बारिश का पानी इकट्ठा करने को क्यों कहा?","answer_hi":"क्योंकि साफ़ पानी सीमित है और बारिश का पानी काम आ सकता है"}]'::jsonb,
 'L2.5.1', ARRAY['L2.6.1','L2.6.2'], 'nature', 'universal', 'informational', 'original'),

-- Grade 3: Complex text, inferential comprehension, varied genres
('RP-007', 'अकबर और बीरबल',
 'एक दिन बादशाह अकबर ने दरबार में पूछा — इस दुनिया में सबसे ताकतवर चीज़ क्या है? किसी ने कहा तलवार, किसी ने कहा हाथी। बीरबल चुप थे। अकबर ने पूछा — बीरबल, तुम क्या कहते हो? बीरबल ने कहा — जहाँपनाह, सबसे ताकतवर चीज़ ज़रूरत है। जब इंसान को ज़रूरत होती है तो वह पहाड़ भी तोड़ सकता है, नदी भी पार कर सकता है। अकबर मुस्कुराए और बोले — बीरबल, तुम सही कहते हो।',
 85, 'grade_3', 'easy',
 ARRAY['basic_matras','all_matras','conjuncts','chandrabindu','halant'], 45,
 '{"achieved":{"min":60},"partially_achieved":{"min":40,"max":59},"not_achieved":{"max":39}}'::jsonb,
 '[{"type":"literal","question_hi":"अकबर ने क्या पूछा?","answer_hi":"दुनिया में सबसे ताकतवर चीज़ क्या है"},{"type":"literal","question_hi":"बीरबल का जवाब क्या था?","answer_hi":"ज़रूरत"},{"type":"inferential","question_hi":"बीरबल ने ज़रूरत को सबसे ताकतवर क्यों कहा?","answer_hi":"क्योंकि ज़रूरत इंसान को कुछ भी करने की ताकत देती है"},{"type":"inferential","question_hi":"अकबर मुस्कुराए — इसका क्या मतलब है?","answer_hi":"वे बीरबल के जवाब से खुश और सहमत थे"}]'::jsonb,
 'L3.5.1', ARRAY['L3.6.1','L3.6.3'], 'school', 'universal', 'narrative', 'original'),

('RP-008', 'मधुमक्खियों का संसार',
 'मधुमक्खियाँ बहुत मेहनती कीड़े हैं। वे छत्ते में रहती हैं। एक छत्ते में हज़ारों मधुमक्खियाँ होती हैं। हर मधुमक्खी का अपना काम होता है। रानी मधुमक्खी अंडे देती है। श्रमिक मधुमक्खियाँ फूलों से रस इकट्ठा करती हैं और शहद बनाती हैं। सैनिक मधुमक्खियाँ छत्ते की रक्षा करती हैं। मधुमक्खियाँ फूलों का परागण भी करती हैं जिससे नई फ़सलें और फल उगते हैं। बिना मधुमक्खियों के हमारा खाना बहुत कम हो जाएगा।',
 90, 'grade_3', 'medium',
 ARRAY['basic_matras','all_matras','conjuncts','chandrabindu','halant'], 35,
 '{"achieved":{"min":60},"partially_achieved":{"min":40,"max":59},"not_achieved":{"max":39}}'::jsonb,
 '[{"type":"literal","question_hi":"मधुमक्खियाँ कहाँ रहती हैं?","answer_hi":"छत्ते में"},{"type":"literal","question_hi":"श्रमिक मधुमक्खियाँ क्या करती हैं?","answer_hi":"फूलों से रस इकट्ठा करती हैं और शहद बनाती हैं"},{"type":"cause_effect","question_hi":"मधुमक्खियाँ न हों तो क्या होगा?","answer_hi":"परागण नहीं होगा, फ़सलें और फल कम उगेंगे, खाना कम होगा"},{"type":"main_idea","question_hi":"इस अनुच्छेद का मुख्य विषय क्या है?","answer_hi":"मधुमक्खियों का जीवन और उनका महत्व"},{"type":"fact_opinion","question_hi":"क्या यह तथ्य है या राय: मधुमक्खियाँ मेहनती कीड़े हैं?","answer_hi":"राय — मेहनती एक गुण/विशेषण है जो लेखक ने दिया"}]'::jsonb,
 'L3.5.1', ARRAY['L3.6.1','L3.6.2','L3.6.3','L3.6.4'], 'nature', 'universal', 'informational', 'original'),

('RP-009', 'दादी की बगिया',
 'मेरी दादी के घर में एक छोटी सी बगिया है। दादी रोज़ सुबह बगिया में जाती हैं। वे पौधों को पानी देती हैं। गुलाब, गेंदा और चमेली के फूल खिलते हैं। दादी कहती हैं कि पौधे भी हमारी तरह जीवित हैं। उन्हें भी पानी, धूप और प्यार चाहिए। जब मैं दादी के पास जाता हूँ तो हम दोनों मिलकर बगिया में काम करते हैं। दादी मुझे बीज बोना सिखाती हैं। मुझे बगिया में काम करना बहुत अच्छा लगता है।',
 82, 'grade_3', 'easy',
 ARRAY['basic_matras','all_matras','conjuncts'], 50,
 '{"achieved":{"min":60},"partially_achieved":{"min":40,"max":59},"not_achieved":{"max":39}}'::jsonb,
 '[{"type":"literal","question_hi":"दादी के घर में क्या है?","answer_hi":"एक छोटी बगिया"},{"type":"literal","question_hi":"बगिया में कौन-कौन से फूल हैं?","answer_hi":"गुलाब, गेंदा और चमेली"},{"type":"inferential","question_hi":"दादी पौधों को प्यार क्यों देती हैं?","answer_hi":"क्योंकि वे मानती हैं कि पौधे भी जीवित हैं और उन्हें प्यार चाहिए"},{"type":"main_idea","question_hi":"इस अनुच्छेद से क्या सीख मिलती है?","answer_hi":"पौधों की देखभाल ज़रूरी है, वे भी जीवित हैं"}]'::jsonb,
 'L3.5.1', ARRAY['L3.6.1','L3.6.3'], 'nature', 'rural', 'narrative', 'original');


-- Populate search_text
UPDATE reading_passages SET search_text = to_tsvector('simple',
    title_hi || ' ' || passage_hi || ' ' ||
    coalesce(theme,'') || ' ' || target_grade || ' ' || difficulty
);
