# Check for understanding (CFU) in every lesson

Step 1 of the re-teach / CFU design (22 Oct 2026). The mock Vaishnavi reviews is the Claude Doc "Ankur Saathi: re-teach and check-for-understanding, a mock for review".

## What it is
Every teach block (Beginner, Progressor, Proficient) carries 2 to 3 **show-me** questions (4 at most). The teacher asks; **every child writes the answer on a slate or notebook page and hides it; on one signal all hold it up at the same moment**;
the teacher scans the room, then asks two children to explain. **No choral answering** (the teacher could not tell who was right). The routine is a fixed line written in the screen code, so it is identical in every plan.

Each question shows the **right answer** and what to **listen for**: a wrong answer a child with a recorded mistake would give, with the mistake's name from the knowledge base.

## Where the questions come from
- The knowledge base records mistakes for **27 of the 101 skills** (17 of 53 numeracy, 10 of 48 literacy). Each group's questions aim at the mistakes of **that group's own skill** (the Beginners' prerequisite, the selected skill, the Proficients' extension),
  most common and most serious first, and a mistake **detected at the last review comes first**.
- For a skill with **no recorded mistakes** the model writes questions that test the key idea, with a line saying what a right answer shows, and **the screen says so** ("इस कौशल की सामान्य गलतियाँ ज्ञान-आधार में दर्ज नहीं हैं...").

## Who decides what a teacher sees: the code
The model writes; `backend/app/services/cfu.py` decides. A teacher acts on a CFU in front of the class, so anything wrong is **dropped, never guessed at**:

| Check | Dropped when |
| --- | --- |
| Shape | no question or answer, an unknown kind, a question over 260 characters, an answer over 160 (it must fit on a slate) |
| compute | the expected answer is not the real result, or the question states its own answer |
| choose | the real result is not one of the two offered answers, or it is not the expected one |
| spot_error | the worked line is actually right (no mistake to find), or the expected answer is not the real result |
| any answer | a worked line in the expected answer is wrong |
| Mistake IDs | not an ID the knowledge base lists for that group's skill (removed; the mistake's name comes from the knowledge base, not the model) |
| No mistake and no "what a right answer shows" | dropped |
| No reuse | the same operation (58 + 27, in either order) appears in the group's own LESSON (I Do, We Do, You Do). A worksheet repeat is kept and noted |
| The skill's own rule | a carry in a skill "without regrouping", a borrow in one "without borrowing" |
| A word count | 'how many words' (in a quoted sentence, or before the first ` / ` of a split sentence) and 'the third word' do not match the words of the sentence in the question |
| A pause number | the answer `3 (words before / words after)` has a number that is not the count of the words before the slash |

What survives is stored on the teach block: `cfu` (list), `cfu_grounded`, and for ungrounded skills `cfu_note_hi` / `cfu_note_en`. `plan.cfu_stats` records written / kept per group. If the check itself fails, **every CFU is removed**: nothing unchecked reaches a teacher.

## How strict the checks are (rewritten after the first broad run, 22 Oct: 16 skills)
The first runs judged a question by the SKILL'S TYPE in the knowledge base. The broad run showed that was wrong: patterns and shapes are typed "computation" but contain no arithmetic, literacy skills are typed "computation" but contain no sums, and multiplication tables are
"observational" but are all arithmetic. The checks now judge what a question **actually asks**:
- **A real operation** (`58 + 27`, `6 × 7 = 42`): always checked, in every skill: the sum, the offered answers, a worked line, the carry and borrow rules.
- **Arithmetic written in words** (a word problem: "50 rupees, 20 spent, how many are left?") has no operation to verify. In NUMERACY it must at least be plausible: the answer must be a sum, difference or product of the numbers in the question
  (two numbers, or three for a two-step problem). With no digits at all it cannot be checked and is dropped. Literacy is never checked this way.
- **A question that asks for no arithmetic** (a pattern, a shape, "which has 4 corners?") is kept as it is, whatever the skill's type.
- **"Right or wrong?" with a line that IS right** is a fair decoy, but the key must say सही. With a line that is WRONG the key must say गलत (or सही नहीं: "not right"); it must also give the real result
  only when the question asks the child for the correct answer ("गलत है तो सही उत्तर लिखें"). If the child only writes सही or गलत, "गलत" is a complete key.
- **Answers written as Hindi number words** count (चार for 4).
- **A plain comparison** is verified in numeracy only, and only when the question asks WHICH (कौन) is bigger or smaller; never in literacy, where numbers are labels ("वाक्य 1 और वाक्य 2").
- **Word counts:** 'how many words' in a quoted sentence is checked only when the question asks for the TOTAL (कुल / में कितने शब्द), not the length of a phrase; the words before a ` / ` split and 'the third word' are checked too.
- **Repeats:** a question that repeats an example of the group's own LESSON (I Do, We Do, You Do) is dropped, because the answer was shown seconds earlier. A repeat of a WORKSHEET problem is KEPT and noted in the log: a skill with few possible examples
  (single-digit sums: 45 pairs; multiplication tables) cannot avoid it, and the broad run lost most of a block to it.
- Every dropped question is now logged WITH its text and its expected answer, so the reason can be judged: `progressor question 2 dropped: <reason> | «question» → «answer»`.

## The top-up call (22 Oct, after the second broad run)
The model **skips the questions altogether** in about 1 plan in 6 (N0.2.2, L3.6.1, N3.3.2 and L1.5.1 in the first real runs; sometimes the block has the `cfu` key with nothing in it), and in a skill with few possible examples (single-digit sums,
multiplication tables) most of a block can be rejected for repeating the lesson. No check can fix a question that was never written. So when a block ends with **fewer than 2 valid questions**, the app asks the model **once** for just the missing ones:
- the request names only the groups that need it, the recorded mistakes of each group's own skill, the questions already written (not to repeat), the lesson's examples (not to use) and the reasons earlier ones were rejected;
- the new questions go through **the same checks** (`clean_plan_cfu` runs again): the model's second attempt is judged exactly like the first;
- the call is checked against the AI limit before and metered after, like the repairs (`plan_repair`). If the limit is reached, the reply is unreadable or anything else fails, the plan keeps what it has: no retry, never more than one extra call;
- `plan.cfu_stats[group]` records `topped_up`, and the batch report has a `cfu_topup` column listing the groups that needed it.
Switch: `CFU_TOPUP=0` turns it off (default on). The tests switch it off (the shared helper `_scratch.py`), because they count calls exactly; `test_cfu.py` turns it on for its own tests.
Cost: about 2 to 5 cents, and only for the plans that need it.

## What the teachers' review changed (Vaishnavi, 23 Oct)
- **Two show-me questions per group, not four** (`MAX_ITEMS = 2`): eight in a lesson block cost 5 to 7 minutes of 27. The model writes **3, most important first**, and the first 2 that pass the checks are used; fewer than 2 valid triggers the top-up.
- **No story about a child.** "एक बच्चे ने ... लिखा" adds reading and listening load for Class 1 and 2. The question is written as what is ON THE BOARD: "बोर्ड पर देखो: 34 + 28 = 52 लिखा है। क्या यह सही है?". The code drops a story (text inside quotes is exempt: it may be a sentence the children read; the
  teacher's own "मैं ... पढ़ती हूँ" is fine). **Python's `\b` does not work for Devanagari (a vowel sign is not a word character): the check uses explicit boundaries.**
- **No object is handed out for a show-me** (pebbles, buttons and counters cause distraction): slates, fingers, or the board. Objects belong to the I Do and the We Do.
- **Beginners: a choice (1 or 2 on fingers) is better than writing.**
- **No abstract paragraph questions** (the purpose of an introduction, a sentence out of topic): too abstract for Class 2 and 3. Punctuation, what happened first or next, or a missing full stop. The code drops them.
- **Real-word matra pairs:** दिन / दीन, कुल / कूल, कल / काल, सिल / सील, पुल / पूल (not a non-word such as कामल).
- **Plain Hindi:** "इसके बाद" (not "इसके तुरंत बाद"); "मैं एक संख्या बोलूँगा/बोलूँगी: 14"; "अगले दो निशान".
- **The routine on the screen** now says: wait about 20 seconds, then "तीन, दो, एक — दिखाएँ!", then two children explain (one who made the mistake before, chosen quietly and never named, and one at random, not only hands up); if more than a quarter of the group is wrong,
  re-teach that step at once, with sticks, before You Do.
- **Kept as they are, she said so:** the "listen for" mapping of wrong answers to recorded mistakes ("outstanding"), the Beginners' prerequisite-level questions, the teacher-modelled reading (judging expression), the matra minimal pairs.
- **Still to decide with her:** the register of the spoken prompts (तुम forms such as लिखो, दिखाओ, लगाओ, or the respectful ones); the child's word for the part of a pattern that repeats; pauses (the NUMBER of a word, or a slash on a short sentence); the "more than a quarter" rule in a group of 3 or 4.

## The first real re-teach run (23 Oct, N2.3.2, Progressors re-taught)
Every sum in the block was checked by hand and is right, and the block follows the teachers' sequence (recall, the wrong working first and then the right way, erased at the end of the I Do, find-and-fix, a try with new numbers, a quiet visit with no names). It also showed three things the checks had not seen:
- **A wrong answer that is a right answer elsewhere in the lesson.** The Proficients' first show-me put `176 + 349 = 425` on the board, while the I Do's right answer to `267 + 158` was 425: a child who remembers 425 as right would call the wrong line right.
  The checks only caught repeated SUMS. Now `_lesson_results` collects the right answers the lesson works out (every operation in its I Do, We Do and You Do), and a spot_error whose WRONG answer (10 or more) is one of them is dropped, with the reason in the log.
- **A garbled sentence in a Beginners' script:** the model explained the 49-stick pair-kit limit inside the talking points (although 25 + 14 fits). The stick rules now say never to explain the kit size or a limit there.
- **A vague "listen for":** "तीन-चार जैसा बेतरतीब उत्तर, जैसे 99 या 79" is not an answer a teacher can recognise. The rule now says it is the EXACT wrong answer a child with that mistake gives for THIS question, never a description. (Untested with the real model.)
Seen and not changed: both Progressor show-me questions are find-the-mistake (a design question for the teachers: should one be a fresh sum?); the screen, not the talking points, carries the "more than a quarter wrong" rule; "बाकी अतिरिक्त हैं" (the extras) is still in the You Do (the board-work simplification); the other groups' text during a re-teach is clumsy; the older "repeats a number" warnings (63 and 425).

## The second real batch run (23 Oct: N0.2.2, N2.3.2, L2.5.1, L2.7.3, with the teachers' rules)
**Worked:** two questions per group in all four skills; the board format ("बोर्ड पर देखें: 45 + 38 = 73 लिखा है"); finger choices for the Beginners; no loose counters; "इसके बाद"; the teacher's own first person ("मैं ... पढ़ता/पढ़ती हूँ"); every sum and every word count checked and right
(7 words in 'एक छत्ते में हज़ारों मधुमक्खियाँ होती हैं', 4 in 'माँ पानी लाती है'); the exact wrong answers for the Progressors (64, 614, 84 for 45 + 29; 223 for 184 + 139).
**Slipped through, now caught:**
- **A story about someone who is not "a child":** 'एक पाठक ने इसे ... पढ़ा', 'किसी ने ... पढ़ दिया'. The story check now covers any person (बच्चा, पाठक, विद्यार्थी, छात्र, लड़का ... and 'किसी ने').
- **"Which sentence is different from the topic?"** (L2.7.3 Proficients): the very question the teachers ruled out, but it said "विषय से अलग", not "अनुच्छेद". The abstract-paragraph check now needs one of the abstract phrases together with "अनुच्छेद", "पैराग्राफ" or "वाक्य".
- **A 210-character verbal description of a table** (N2.3.2 Beginners: "पहली पंक्ति 4 दहाई और 3 इकाई, दूसरी पंक्ति में 2 इकाई और 5 दहाई ..."), which gave its answer away ("यानी अंक उलटे स्तंभ में हैं") and whose KEY WAS WRONG: it said to write 2 in the ones and 5 in the tens, exactly the places the question called wrong.
  The limit on a question is now 170 characters (the longest good one seen is 134) and on a key 100: a key is a verdict and a number, because explanations are where mistakes hide. The prompt says never to describe a drawing or a table in words.
- **A "listen for" that only describes** ("जैसे 7 + 8 जैसा बेमेल जोड़"): for a numeric computation question an entry that begins with words and contains जैसे / जैसा / बेतरतीब / बेमेल is removed BEFORE the checks; a question left with no valid mistake and no explanation is dropped, and the top-up asks again.
  A behaviour ("उत्तर नहीं लिखा या अंदाज़ से कोई संख्या लिखी") stays.
- **Punctuation choices** are written '1) । 2) ?' (the old "लगेगा या ??" read badly).
**Idea, not built:** for the commonest carry and borrow mistakes the exact wrong answer can be COMPUTED by the code (dropped carry, the whole ones sum written, the smaller digit taken from the larger), instead of trusting the model: reliable and testable.

## What the code cannot check: the first literacy run (22 Oct) and the rules added after it
The code checks arithmetic, comparisons, mistake IDs and reuse. It cannot tell whether a question is **good teaching**. The first run on three literacy skills (24 questions, see the review document) showed questions that broke rules the prompt already had, so the prompt now says them firmly:
- **Self-contained:** a question may not refer to a paragraph or text it does not contain (L2.7.3: "the first sentence of the paragraph", with no paragraph).
- **No answer inside the question** (L1.3.2: "'की' चाहिए" stated in the question) and **one task per question** (write कि AND say which side).
- **Quick answers only:** one letter, matra, short word, number, mark, a choice or a drawing. Never copy or write a sentence; to show a pause, give the NUMBER of the word after which to pause (L2.5.1 asked children to copy a sentence to mark slashes).
- **Say exactly what the teacher writes on the board**, including any deliberate mistake: the children cannot see it in the text (L1.3.2 asked whether a shirorekha was right without saying whether it was there). **Children are 6 to 9**: no percentages (L2.5.1 asked them to compare accuracy with 95%).
  **Every child answers from their own place at the same moment**: never "put a finger on the letter on the board".
- **Different shapes for the three groups** and no two questions in a block testing the same thing the same way.
Whether the rest is pitched right (how much a Class 1 Beginner can write, which matra pairs to use) is for the teachers' review: the questions to Vaishnavi are in the review document.

## The style safety net
Only the teacher's **question** (and `shows_hi`) is softened to the respectful forms, and quote-safe. `expected_hi` and `wrong_answer_hi` are material (a right or a wrong answer) and are **never changed**: a literacy answer can itself be a word like "जाओ".

## The switch
`CFU_ENABLED` (default true; `CFU_TOPUP=0` switches only the extra top-up call off). **Run `python scripts\add_cfu_setting.py` once** (it adds the one line to your `backend/app/core/config.py`, which is never shipped whole; it is safe to run twice; without it the feature still works but cannot be switched off). False: no CFU section in the prompt, nothing the model writes is kept, plans are exactly as before. In the cloud:
`gcloud run services update ankur-saathi --region=asia-south1 --update-env-vars=CFU_ENABLED=false`.

## Seeing real output (needs the real key: run on a machine that has it)
```powershell
cd C:\dev\Ankur-Saathi
python scripts\batch_generate.py --limit 3 --show-cfu --yes
```
It prints each plan's questions and writes `cfu_written`, `cfu_kept` and `cfu_dropped` (the reasons) to `docs/batch/batch_results.csv` (the last three columns, so older report files stay aligned).
An older report file is brought up to date automatically the next time the tool runs, with the original kept as `batch_results.csv.bak`; `python scripts\batch_generate.py --upgrade-csv` does only that, for free.
(v27i put these columns in the middle, which shifted every column after them in a file that already existed; v27j repairs those rows.) If many questions are dropped, the reasons say what the model keeps getting wrong, and the prompt in `prompts/cfu_prompt.py` is where to fix it.

## Not built yet (decided, in the mock)
The teacher's decision card with the recent record, the one-tap tally after a show-me, the focused re-teach block, naming children for the explain step. The wording "आज की जाँच में:" is done on the Review screen.

Tests: `backend/tests/test_cfu.py`.


## The listen-for answers are checked by code (24 Oct)
**Found on the first real re-teach block:** for **54 + 29** the model listed **613** as the answer of a child who "writes the whole ones sum"; that child writes **713** (5 + 2 = 7, then 13). The 613 had been copied from the I Do's 46 + 27. The validator checked the RIGHT answer, the worked lines, the carry rule and reused examples, but not what a child with a recorded mistake would write, so a teacher listening for 613 would never have heard it.

**Now** `cfu.verified_listen` runs on every numeracy question BEFORE the validity checks (like the vague-entry cleaner: a question left with no valid mistake and no "shows" line is dropped, and the top-up asks again). For a **`compute`** question with **exactly one operation** (a chain, two sums, a `choose` or `spot_error` question is not checked), each listen-for entry whose mistake the code can compute is compared with what that mistake really gives:
- **a different number is corrected** (`613` becomes `713`; `613 लिखेगा` becomes `713 लिखेगा`; when the text holds several numbers and none is right, the entry becomes the right number alone; when the right number is among them, it is left alone);
- **an entry for a mistake that cannot happen on these numbers is removed** (dropping a carry on 23 + 14, where there is none; or where the mistake happens to give the right answer);
- **everything else is left exactly as the model wrote it**: a behaviour in words, a mistake the code has no pattern for, other sizes of numbers, a literacy skill.
Every change is a line in the plan's log (`progressor question 1: listen-for N2.3.2-M2: listed '613' but that mistake gives 713 on 54 + 29: corrected to '713'`).

**The eight patterns** (`cfu.LISTEN_PATTERNS`) are exactly the mistakes the knowledge base records with a worked example, and each reproduces that example: N2.3.2-M1 drops the carry (34 + 28 = 52), -M2 writes the whole ones sum (512), -M3 carries the ones digit (72); N3.3.1-M1 forgets the second carry (167 + 245 = 312); N2.3.4-M1 subtracts smaller from larger (42 - 17 = 35), -M2 forgets to reduce the tens (35: a different number in general, 61 - 29 is 48 or 42); N3.3.4-M1 multiplies digit by digit (23 x 4 = 812); N3.3.5-M1 divides by subtracting (24 / 6 = 18). **Not computable, so never touched:** N2.3.2-M4 (left to right: "stuck"), N2.3.4-M3, N2.3.1-M1 (misalignment: the knowledge base gives one convention only), N3.3.3 (table facts), N1.3.x (counting).
**To add a mistake:** write its function in `cfu.py`, add it to `LISTEN_PATTERNS`, and add its recorded example to `test_cfu_listen_for.py` (the test checks that the knowledge base's own example text contains the answer the code computes).
Tests: `backend/tests/test_cfu_listen_for.py` (42 checks, including a child doing the sum column by column, written separately from the code's formulas, compared over every pair of two-digit numbers).


## Two questions of one group never share a right answer (24 Oct)
**Found on the second real re-teach block:** the two show-me questions were 56 + 28 and "49 + 35 = 74: right or wrong?": both have the right answer **84**. A child who solved the first knew the second ("wrong, 84") without computing it, so the second tested nothing.
**Now** `cfu.right_answer(item)` works out a numeric question's right answer from the question itself (for a worked line to judge, the REAL result of `a op b`, not the wrong one shown; otherwise the value of the last expression), and `clean_plan_cfu` drops a later question of a NUMERACY group whose right answer repeats an earlier kept one (`progressor question 2 dropped: its right answer 84 is the same as question 1's ...`). A question dropped for another reason (a wrong answer key) claims nothing. The **top-up** is told the answers already taken (`taken` in `needs`, built by `plan_service.topup_cfu`) and asks for a DIFFERENT one, and the CFU rules ask for it in the first request too (`cfu_prompt.CFU_RULES`). Literacy skills and questions with no arithmetic are not affected. Tests: `backend/tests/test_cfu_answers.py` (17 checks). One fixture of `test_cfu.py` had two "valid" Progressor questions with the same answer (85): the second now has its own (39 + 47 = 86).


## A two-digit addition skill never reaches 100 (24 Oct)
**Found on the third real block:** worksheet problem 6 was **79 + 21 = 100**. The knowledge base records `number_range max 99` for N2.3.2, and the model read it as a limit on the numbers ADDED, not on the TOTAL. Three-digit numbers are the Proficients' skill (N3.3.1), so a Progressors' sheet and show-me must stay two-digit.
**In the show-me:** `cfu.skill_rules` gives a TWO-DIGIT ADDITION skill (a name starting "Add", containing "2-digit" or "two-digit") `max_result: 99`, and `check_item` drops a question whose REAL result is over it (`its result 100 is over 99: three-digit numbers belong to a later skill`). Only real results count: a worked line to judge may deliberately show a wrong result over 99 (56 + 28 = 714). Other skills (3-digit addition, subtraction, multiplication, counting) have no cap.
**A warning, not a drop, for the lesson's own results:** a show-me whose right answer, or a listed wrong answer, is a result the lesson has already put on the board (its I Do, We Do or You Do: e.g. the I Do's 57 + 26 = 83, and then a show-me with the answer 83) can be copied rather than worked out. `clean_plan_cfu` logs `question 2: warning: its right answer 83 is already a result in the lesson (on the board)` and KEEPS the question (a drop would cost an extra model call, about 14 cents, in perhaps one plan in four); the CFU rules ask the model to avoid it. If the log shows it often in real runs, make it a drop.
Tests: `backend/tests/test_two_digit_limit.py` (32 checks).


## A show-me must not be passable by guessing (24 Oct)
**Found on the fourth real block:** BOTH show-me questions were 'right or wrong?' lines with a WRONG line: `37 + 46 = 73` (answer 'गलत, 83') and `28 + 35 = 513` (answer 'गलत, 63'). After a lesson about mistakes, 'wrong' is the safe guess: a child can say it twice without working anything out, and neither question makes the child produce an answer. The first three real blocks each had one question where the child computes.
**Now** `clean_plan_cfu` refuses to let a numeracy block's questions all be wrong lines: when the questions kept so far are all `spot_error` questions whose answer starts with `गलत` (`cfu._is_wrong_line`), a further wrong line is dropped (`progressor question 2 dropped: both show-me questions would be wrong 'right or wrong?' lines, so a child can guess 'wrong'. Write a question where the child WORKS OUT an answer (compute or choose)`). A later `compute` question then takes the place; if there is none, the block has one question and the top-up (which quotes that reason, and the answers already taken) asks for another. **Still allowed:** a compute question with a wrong line (the shape of the first three blocks), and a wrong line with a CORRECT line (a fair decoy: the answer says सही). Literacy skills are not affected. The CFU rules ask for it in the first request too. A question dropped here claims no right answer (the order of the checks matters: tested by putting the old order back, which makes the test fail).
Tests: `backend/tests/test_cfu_guessable.py` (14 checks).
