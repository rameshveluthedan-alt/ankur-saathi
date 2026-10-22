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
