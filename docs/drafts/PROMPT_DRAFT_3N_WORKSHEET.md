# Prompt draft: the 3 + N worksheet (less board work)

**Status:** first draft for Ramesh, 29 Oct (lab). **Nothing here is applied:** `prompts/orchestrate.py` is unchanged. Each block below is written as a drop-in
replacement for the current text, with the place it replaces. Hindi in the examples follows the reviewed wording (Vaishnavi, 29 Oct).

## Why

Today every group must do 5 (Beginners) or 6 (Progressors) problems before the extras, and the Proficients all 8. In board-copy mode (no printer) children copy
every required problem from the board, and the teacher writes them all ("📝 बोर्ड पर लिखें (सवाल 1–6)"). The spec's answer: **3 core problems per group**, chosen
to give the signal the review needs, then **1, 2 or 3 extras by session length** for children who finish early.

| Session length | Core (required) | Extras | At most on the sheet |
|---|---|---|---|
| 45 min | 3 | 1 | 4 |
| 60 min | 3 | 2 | 5 |
| 90 min | 3 | 3 | 6 |

The screen side is already built for this: the signal panel shows "तीन मुख्य प्रश्न" + "→ N और प्रश्न", the printed plan says "3 मुख्य + N", and the board line
copies problems 1 to `required_count`, so it shrinks to 3 by itself.

---

## 1. The worksheet rule (replaces the `"required_count"` rule in `_SCHEMA_COMMON`)

**Replaces:** the bullet beginning `- "required_count": children must do problems 1 to required_count; …` (orchestrate.py, about line 512).

```
- THE 3 + {extras} SHEET. Every worksheet has exactly 3 CORE problems (numbers 1, 2, 3), then exactly {extras} EXTRA problems for children who finish early: {total} problems in all, never more. "required_count" is 3 on every sheet, for every group.
- The 3 core problems are the SIGNAL: from them alone the teacher (and the photo analysis) must be able to tell who has the skill and which mistake the others make. Design them, in this order:
  • problem 1: the skill in its plainest form (a child who has the skill gets it right; a child who does not, does not);
  • problem 2: built to reveal the FIRST misconception listed for this group's skill (set its diagnostic_for_misconception);
  • problem 3: built to reveal the SECOND misconception, or, if the skill has only one, the hardest case the skill allows (for a carry sheet: a ones-column sum of exactly 10, or of 15 or more where the range allows).
  At least 2 of the 3 core problems carry a diagnostic_for_misconception, and NO extra problem does: every problem that reveals a mistake is a core problem.
- The extras practise the same skill with new numbers (no new difficulty, no new kind of problem); on the Progressor and Proficient sheets the last extra may be a word problem.
- The You Do talking point of every group says to copy and solve problems 1-3 first, and that the rest are extras for those who finish (for example 'पहले वर्कशीट के सवाल 1 से 3 हल करें; जो जल्दी ख़त्म करें, वे बाकी सवाल करें।'). Every statement about a sheet must match: 3 core, {extras} extra.
```

**Also change in the same list:**
- `- At most 8 problems per worksheet, so each sheet fits ONE A4 page. Fewer than 8 is fine.` → `- Exactly {total} problems per worksheet (3 core + {extras} extra).`
- In the `WORKSHEET PROBLEMS MUST BE NEW` bullet, keep everything; the "vary the ones-column sum" part now applies to the 3 core first.

## 2. The numeracy worksheet shapes (replaces the three level lines in `_SCHEMA_WORKSHEET_NUMERACY`)

**Replaces:** the `- beginner:`, `- progressor:` and `- proficient:` lines under "Numeracy worksheet rules", and `"required_count": 5` in the example becomes `"required_count": 3`.

```
- beginner: example_block REQUIRED (a worked example of the prerequisite skill). Core 1-3 and every extra: row_type "grid" with show_pv_grid true, pv_columns 2, pv_row2 true. problem_hi has NO "= ___" (the grid is the answer).
- progressor: example_block REQUIRED, and it must show the carry (e.g. 27 + 15 = 42). Core 1-2: row_type "grid" (same fields as above); core 3: row_type "plain" ("19 + 43 = ___"), so the group moves off the grid within the core. Extras: row_type "plain"; at 90 minutes the last extra may be a word problem (row_type null, "answer_type": "wide", "word_problem_text" repeating the text).
- proficient: example_block null. Core 1-3: row_type "plain" ("57 + 36 = ___"), each with a different carry pattern. Extras: at least one word problem (row_type null, "answer_type": "wide", "word_problem_text"); the rest "plain".
- Stay inside the number range given in the context. If a number has 3 digits, use pv_columns 3 and add row1_h, row2_h, answer_h to example_block.
```

**Remove:** `- Place at least 2 problems that reveal the top misconceptions, and set diagnostic_for_misconception on them.` (now said, more exactly, in section 1).

## 3. Literacy (replaces `"required_count": 5` in `_SCHEMA_WORKSHEET_LITERACY` and adds one rule)

```
- The first 3 questions are the CORE (required_count 3), then {extras} extra. When BANK QUESTIONS are given, they ARE the core: the system places them first, word for word; do not write other core questions.
- A writing sheet (a skill whose task is to write sentences): the core is ONE writing task (problem 1, answer_type "lines") plus two short items that check its parts (for example a sentence to complete with a joining word); the extras are a second, shorter writing task.
```
*Open for Ramesh:* whether a writing sheet should be "1 task + extras" instead (then `required_count` 1 and the signal panel's `writing_prompt` is that task).

## 4. PART B in the user prompt (replaces the three lines under `### PART B: THREE WORKSHEETS`)

**Replaces:** `— 8-10 problems with visual scaffolding` / `— 8-10 problems, scaffolding faded, …` / `— 8-10 extension problems + word problems` (these already contradict "at most 8").

```
### PART B: THREE WORKSHEETS (3 core + {extras} extra each: the session is {ctx.available_minutes} minutes)
- शुरुआती: {ctx.beginner.target_competency.name_hi} — 3 core + {extras} extra, all on the place-value grid
- प्रगतिशील: {ctx.selected_competency.name_hi} — 3 core (2 and 3 reveal {', '.join(top_misconception_ids[:2])}) + {extras} extra, scaffolding faded
- दक्ष: {ctx.proficient.target_competency.name_hi} — 3 core + {extras} extra, including a word problem
Include answer keys and the misconception each core problem reveals.
```

## 5. The re-teach rule (one example in `RETEACH_MAIN_RULES`)

**Replaces:** `(for example 'वर्कशीट के सवाल 1 से 6 पहले हल करें', using the worksheet's own required count)` → `(for example 'वर्कशीट के सवाल 1 से 3 पहले हल करें')`.

## 6. Where `{extras}` and `{total}` come from (code, in `build_user_prompt` and the schema text)

```python
# the extras by session length (spec: 45 → 3 + 1, 60 → 3 + 2, 90 → 3 + 3); any other length takes the nearest
EXTRAS_BY_MINUTES = {45: 1, 60: 2, 90: 3}
def worksheet_shape(minutes: int) -> tuple[int, int]:
    m = min(EXTRAS_BY_MINUTES, key=lambda k: abs(k - minutes))
    return EXTRAS_BY_MINUTES[m], 3 + EXTRAS_BY_MINUTES[m]          # (extras, total)
```
`_SCHEMA_COMMON` and the worksheet schemas are plain strings today; they would need `{extras}` / `{total}` filled in (a `.format(...)` or `.replace(...)`
where `schema_for(domain_id)` builds them), since the length is per plan.

## 7. Curated skills (optional, a small addition)

For the skills in `docs/CURATED_SKILLS.md` with a maths worksheet (N2.2.1, N2.3.2, N3.3.1 today), the reviewed core questions could be given the way BANK
QUESTIONS are for passages, with the system placing them as problems 1-3:
```
### CORE QUESTIONS (reviewed: the system places them as problems 1-3, word for word, with these answers; write only the extras)
- 1. 34 + 25 = ___ (answer 59)
- 2. ... (reveals N2.3.2-M1)
- 3. ... (reveals N2.3.2-M2)
```
That needs the curated questions stored somewhere the prompt builder can read (today they are only described in the document).

---

## What must change in code with it (not prompt text)

1. **The plan checks** (`backend/app/services/plan_service.py`, about lines 623-634): today they require `required_count` 5 (Beginners) and 6 (Progressors) and
   the diagnostic problems among the required ones. New: `required_count == 3` on every sheet; `len(problems) == 3 + extras` for the plan's length; at least 2
   diagnostics among problems 1-3 and none after. The other two `required_count` reads (about lines 198 and 392) need a look too.
2. **The signal on each teach block** (the screen's contract, already built): the server can build it from the worksheet itself, so the model writes nothing
   new: `{"shape": "maths_questions", "signal_curated": <skill in CURATED_SKILLS>, "maths_questions": {"core": [problems 1-3's problem_hi], "extra_count": extras}}`
   for numeracy; `writing_prompt` from a writing sheet's problem 1; `null` otherwise. Deterministic, and the panel and the sheet can never disagree.
3. **The photo analysis**: reads the 3 core problems as the signal (A/PA/NA and the mistake from them); extras are counted as practice, not evidence.
4. **The recorded sample plans** (the AI-off fallback, 90 minutes today): either re-recorded in the 3 + 3 shape, or left as they are with the time chip saying
   "90 मिनट" (it already does); the checks must then accept a recorded plan's older shape.
5. **The few-shot examples**: one per length (45 / 60 / 90) and per shape (maths, writing), with the Hindi of the six reviewed, as the spec asks.

## How to check it (before main)

- Generate for N2.3.2 at 45, 60 and 90 minutes: each sheet has 3 + 1 / 3 + 2 / 3 + 3 problems, `required_count` 3, problems 2 and 3 carry diagnostics, no extra does.
- The You Do of each group says "सवाल 1 से 3"; the board line shows 3 problems; the signal panel shows the same 3 (from the server, no mock).
- A re-teach day: the re-teach You Do says "1 से 3".
- Photograph a sheet with mistakes only in the extras: the review reports the core result, not a mistake.
- The tests that read `required_count` are updated with the new rule, not deleted: `test_sample_plans.py`, `test_scoring.py`, `test_two_digit_limit.py`, `test_ai_budget_flow.py`, `test_hindi_numbers_reference.py`, `test_names_never_reach_ai.py` (backend) and `board_work.test.mjs` (front end); check each for a 5 or 6 it relies on.
