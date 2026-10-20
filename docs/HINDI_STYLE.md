# Hindi style for the teacher's words

Vaishnavi reviewed the N2.3.2 plan (Oct 2026). Her verdict: the vocabulary is generally accurate and suits early grades, but some words and
commands should be softened to be more respectful, positive and child-friendly. The PDF itself renders correctly (the Devanagari is shaped
properly); this is about **wording and tone**, and the same wording is in the app's plans, because the PDF was made from the same plan data.

## What was decided, and how it is applied
| Was | Now | Why | How |
| --- | --- | --- | --- |
| फालतू बंडल | अतिरिक्त बंडल | "फालतू" reads as useless or wasted | prompt + safety net |
| चुपचाप शुरू करें | शांति से शुरू करें | "चुपचाप" sounds like a reprimand | prompt + safety net |
| मेरे पास आओ / अपना काम बंद करो / छड़ियाँ मॉनिटर को दो | आएँ / अपना काम रोक दें / दें | modelling respectful language is a goal of foundational learning | prompt + safety net (about 40 common classroom verbs) |
| दहाई \| इकाई का खाना | दहाई-इकाई का बॉक्स | "खाना" is ambiguous for a 6-year-old; "बॉक्स" matches the place-value grids the app prints | prompt + safety net (only in place-value sentences; a bare "खाने में" becomes "दहाई-इकाई के बॉक्स में") |
| कितने दहाई, कितने इकाई | कितनी दहाई, कितनी इकाई | not in her review: both words are feminine | prompt + safety net |

**Kept, by her review:** हासिल, खुली छड़ियाँ, शब्द-सवाल, "गलती दिखे तो मेरे पास आकर छड़ियों से दिखाएँ" (the idea she praised, now in the respectful form),
and the collective praise "आज बहुत अच्छा काम हुआ".

## Two layers
1. **The prompt** (`STYLE_PROMPT` in `prompts/hindi_style.py`, added to the Hindi style block in `orchestrate.py`) tells the model to write this way. This is the real fix.
2. **A safety net** (`soften_plan` in the same file, called in `plan_service.py` right after the reply) makes whole-word swaps for the cases that are unambiguous. It only touches
   what the teacher says or reads (scripts, transitions, anchor tasks, I/We/You Do, independent-work lines, preparation notes) and the printed worksheet instructions. It never
   touches a word problem, an answer, a reading passage, a title or an explanation. It is idempotent, and it also runs on a recorded plan that is replayed when the AI limit is reached.

A swap is deliberately narrow: "दो" is changed only as the verb "give" at the end of a clause ("मॉनिटर को दो।"), never the number ("दो अंकों के जोड़"); "खाना" is changed only as a
whole word in a sentence about place value, never inside "सिखाना" or in a story about eating.

## Measuring whether the model follows the prompt
Each plan logs `Hindi style: N wording changes (...)`, and `scripts/batch_generate.py` writes it to the report as `style_changes`. **Near 0 means the model is writing the new
style itself; a high number means the prompt is not being followed** and should be tightened. Check this after the first real batch run.

## Decisions: one constant each, in `prompts/hindi_style.py`
1. ~~`FRAME_WORD`~~ **Decided (20 Oct): "बॉक्स".** Vaishnavi offered "बॉक्स" or "घर"; "घर" only works if children were taught the frame that way, and the printed place-value grids make "बॉक्स" the clearer word. It is still one constant (`FRAME_WORD`), and the tests follow it.
2. **`POLITE_IN_WORKSHEETS`** (now `False`): should the printed worksheet instructions to children also use the respectful forms (जोड़ें, लिखें), or keep the textbook second-person
   style (जोड़ो, लिखो)? Textbooks usually use the second person with children, so this is her call. If she says yes, set it to `True`; no other change is needed.
3. The safety net does not rewrite a command it is unsure of. A verb that is not in its list stays as the model wrote it. Add it to `POLITE_VERBS` when a review finds one.

## Tests
`backend/tests/test_hindi_style.py` (the exact sentences from the review, what must NOT change, idempotence, and the two recorded plans) and
`backend/tests/test_hindi_style_pipeline.py` (a plan generated with the old wording, and a replayed plan, both come out in the new style through the real pipeline).
