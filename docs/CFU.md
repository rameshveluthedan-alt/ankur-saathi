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
| No reuse | the same operation (58 + 27, in either order) appears in the group's talking points or worksheet |
| The skill's own rule | a carry in a skill "without regrouping", a borrow in one "without borrowing" |

What survives is stored on the teach block: `cfu` (list), `cfu_grounded`, and for ungrounded skills `cfu_note_hi` / `cfu_note_en`. `plan.cfu_stats` records written / kept per group. If the check itself fails, **every CFU is removed**: nothing unchecked reaches a teacher.

## The style safety net
Only the teacher's **question** (and `shows_hi`) is softened to the respectful forms, and quote-safe. `expected_hi` and `wrong_answer_hi` are material (a right or a wrong answer) and are **never changed**: a literacy answer can itself be a word like "जाओ".

## The switch
`CFU_ENABLED` (default true). **Run `python scripts\add_cfu_setting.py` once** (it adds the one line to your `backend/app/core/config.py`, which is never shipped whole; it is safe to run twice; without it the feature still works but cannot be switched off). False: no CFU section in the prompt, nothing the model writes is kept, plans are exactly as before. In the cloud:
`gcloud run services update ankur-saathi --region=asia-south1 --update-env-vars=CFU_ENABLED=false`.

## Seeing real output (needs the real key: run on a machine that has it)
```powershell
cd C:\dev\Ankur-Saathi
python scripts\batch_generate.py --limit 3 --show-cfu --yes
```
It prints each plan's questions and writes `cfu_written`, `cfu_kept` and `cfu_dropped` (the reasons) to `docs/batch/batch_results.csv`. If many questions are dropped, the reasons say what the model keeps getting wrong, and the prompt in `prompts/cfu_prompt.py` is where to fix it.

## Not built yet (decided, in the mock)
The teacher's decision card with the recent record, the one-tap tally after a show-me, the focused re-teach block, naming children for the explain step. The wording "आज की जाँच में:" is done on the Review screen.

Tests: `backend/tests/test_cfu.py`.
