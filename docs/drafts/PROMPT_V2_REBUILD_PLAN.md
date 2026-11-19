# Prompt v2: rebuild plan against today's v1 (19 Nov 2026, lab/prompt-v2 from main 112b953)

**Inputs:** `PROMPT_REVIEW_29OCT.md`, `PROMPT_DRAFT_V2.md`, `PROMPT_DRAFT_3N_WORKSHEET.md` (all 29 Oct); today's prompt as the server sends it:
`plan_service.generate_dainik_yojana` (plan_service.py:1033) → `build_system_prompt` (orchestrate.py:444) + `build_user_prompt` (orchestrate.py:750),
with `CFU_RULES` / `render_cfu_section` (cfu_prompt.py:28, :87), `STYLE_PROMPT` (hindi_style.py:31) and `writing_sheets.prompt_section` (writing_sheets.py:120).
**Nothing is changed by this document.** Line numbers are at 112b953.

**The rule for the rebuild:** the v2 draft was copied from the 29 Oct v1. Re-copy every unchanged rule from TODAY's modules (never from the draft), then apply each
v2 change below on top. Where a November rule and v2 disagree, keep November unless C says otherwise.

## A. Each v2 change against today's v1

| # | v2 change | Status | v1 code it touches |
|---|---|---|---|
| A1 | Session length: anchor 5/8/10, real block minutes in every rule, show-me count by block length, block < 10 min = I Do + We Do only (review 1; draft "TODAY'S SHAPE", C2) | **Still needed.** Partly: 27e7c6d added a pace rule for every teach block, but it is still written for 27 min; the screen hides the pace under 10 min (pwa/src/services/reteachInfo.js:19) | orchestrate.py:495 (pace rule), :525 (independent activity "22-29 minutes"), :708 (re-teach "27 minutes"), :875-883 (anchor fixed 10, timing), :961 PART A, :969-977 PART C; cfu_prompt.py:32 ("3 questions … first 2"); cfu.py:21 (`MIN_ITEMS, MAX_ITEMS = 2, 2`) |
| A2 | Problem-count contradiction ("8-10" vs "at most 8") (review 2a) | **Still needed** | orchestrate.py:964-966 (PART B "8-10"), :519 ("At most 8"), :530-544 numeracy sheet rules |
| A3 | "बोर्ड पर देखो" → "देखें" in the CFU model line (review 2b) | **Still needed** | cfu_prompt.py:46 |
| A4 | One mistake list per group, used for show-me AND worksheet diagnostics; drop MISCONCEPTION TAXONOMY (Progressors only) and the duplicate list (review 2c, 4b; draft C3) | **Still needed** | orchestrate.py:756-768 (taxonomy text), :944-945, :518 ("an ID from the misconception list"), :544, :888 + :966 (`top_misconception_ids`); cfu_prompt.py:87-107 (`render_cfu_section` prints the per-group list, keep its ranking) |
| A5 | Observation reminders name the activity, with A/PA/NA meanings (review 3; draft PART E rule) | **Mostly superseded** by 7c8f053: each observed group's worksheet carries `observe` (task, materials, `look_for` A/PA/NA) and the screens use it. `observation_reminders_hi` is now read only for "is anything observed today" (pwa/src/services/reviewWays.js:53) | orchestrate.py:827-831 (obs_text still sends roll numbers), :985 PART E |
| A6 | Fixed text in a cached system block (review 4; draft A, C1) | **Still needed.** SDK supports it at runtime (D2) | plan_service.py:1245-1262 (`system=system_prompt` string), orchestrate.py:444-460, :467-568, cfu_prompt.py:28, hindi_style.py:31 |
| A7 | Remove dead `generate_dainik_yojana` (hard-coded old model) and unused `prompts/templates/*.md` (review 5; draft C6) | **Still needed** | orchestrate.py:1000-1190; prompts/templates/dainik_yojana_system.md, dainik_yojana_user.md |
| A8 | Concrete "HOW TO WRITE THE PLAN" rules in place of the generic principles (review 6a) | **Still needed** | orchestrate.py:446-460 |
| A9 | Style rules into the cached part (review 6b) | **Still needed**, but the text to move is TODAY's (B2), not the draft's | orchestrate.py:836-844, hindi_style.py:31-39 |
| A10 | No roll numbers in the prompt; drop `peer_monitors` (review 6c; draft C5) | **Still needed.** Nothing outside orchestrate.py reads `peer_monitors` (searched 19 Nov) | orchestrate.py:930-936, :489 (schema), :982 PART D, :831 |
| A11 | Structured outputs instead of bare JSON + retry (review 6d) | **Defer** (needs a newer SDK; not part of this rebuild) | plan_service.py:1251-1307 |
| A12 | The fixed "representative plan" note added by code, not the model (review 6e; draft C5) | **Partly done:** 21e7fb8 builds the "resources" item in code (backend/app/services/resources_item.py); the model is still asked for the content item and the representative note | orchestrate.py:497 |
| A13 | 3 + N worksheet: 3 core (diagnostics only in 1-3), extras 1/2/3 by session length, `required_count` 3 (3N draft; draft B PART B, C4) | **Still needed for numeracy and reading sheets.** Writing, fluency, observed and dictation sheets now have their own November rules (C1-C3) | orchestrate.py:516 (required_count rule), :526-544, :546-566; plan_service.py:585-645 (`validate_plan_shape`: 5/6 rule at :634-637, max 8 at :628), :182-261 (`repair_worksheet_numbers` reads `required_count`), :379-415 (`apply_bank_questions`); writing_sheets.py rules per kind |
| A14 | The `signal` on each teach block computed from problems 1-3 (draft C5) | **Still needed** (new code; nothing computes it today) | plan_service.py post-processing after :1355 |
| A15 | Plan checks updated to the new shape (draft C4) | **Still needed** (with A1, A13) | plan_service.py:585-700; cfu.py:21, :673-675 |
| A16 | Anchor at 45 min = one whole-class task (draft PART A) | **Still needed** (open decision F2) | orchestrate.py:575-620 (`_anchor_prompt_section`), :961 |

**Counts:** 16 changes. 12 still needed (A1-A4, A6-A10, A14-A16; A1 has a start in 27e7c6d), 2 partly done (A12, A13), 1 mostly superseded (A5), 1 deferred (A11).

## B. Carry forward: v1 text added since 29 Oct that the v2 draft lacks (keep word for word)

1. **Pace of every teach block** (27e7c6d): orchestrate.py:495. Keep the idea and "The app shows these minutes on the plan"; its numbers move into TODAY'S SHAPE (C4).
2. **Teacher's lines as instructions** (f0335f7): orchestrate.py:839-843: instructions to the teacher ("बोर्ड पर लिखें", "बच्चों से पूछें"), never "मैं … लिखता/लिखती हूँ"; mark names (ै 'ऐ की मात्रा', े, ं, ँ, ः; never call ै or े a बिंदी). **Replaces** the draft's first HINDI STYLE bullet ("use 'पढ़ता/पढ़ती हूँ'"), which is now wrong.
3. **CFU lines rewritten** (f0335f7): cfu_prompt.py:47 ("written as an instruction ('बोर्ड पर ... लिखें', '... पढ़कर सुनाएँ') … Never the teacher's 'मैं ... लिखता/लिखती हूँ'") and cfu_prompt.py:54 ("'एक संख्या बोलें: 14'"). The draft still has the old "मैं ... पढ़ता/पढ़ती हूँ" and "मैं एक संख्या बोलूँगा/बोलूँगी".
4. **Literacy schema fields** (eb6d212): orchestrate.py:550-553 (`sheet_kind`, `writing_task`, `checklist`, `dictation_sentences`) and :562-566 ("(a READING skill)", "A group taught a WRITING skill follows the WRITING WORKSHEETS section").
5. **WRITING WORKSHEETS section** (eb6d212, 65fbbfb): writing_sheets.py:120-167 (composition, dictation, usage, formation), appended at orchestrate.py:872.
6. **READING-ALOUD WORKSHEETS section** (27e7c6d): writing_sheets.py:224-247, with `LISTEN_SENTENCE`, at most 3 questions, "प्रश्न 1 से 3", no extras.
7. **OBSERVED-SKILL TASKS section** (7c8f053, f0335f7): writing_sheets.py:170-221, with `WATCH_SENTENCE` (writing_sheets.py:59), the structured items and `"practice": true`.
8. **`ctx.writing_rules`** plumbing (orchestrate.py:149, plan_service.py:1224) and the post-processing that depends on these rules (`apply_writing_sheets`, `check_writing_sheets`, observed answers): code, unchanged by v2.
9. **Hindi post-processing** (f0335f7, hindi_style.py:150-302: `teacher_instructions`, `check_teacher_text`): code, unchanged.

Not in the plan prompt (no carry-forward needed): 4ae6d4f "next class" (screens), 65fd2c1 one-third rule and English names (screens), cd76154 / 02911ff (photo prompt in vision_analysis.py).

## C. Conflicts and recommended resolutions

1. **3 + N vs the writing sheets.** v2 makes every sheet 3 core + N; November composition sheets are "problem 1 = the task, problems 2-4 short items, required_count: all of these, optional second task" (writing_sheets.py:136-145); dictation sheets have no extras (:154).
   **Keep November** for writing/dictation/usage/formation sheets: they were built after real runs and the photo test (cd76154). Apply 3 + N only to numeracy and reading sheets. The draft's own writing-sheet line is marked "open" anyway.
2. **3 + N vs fluency sheets.** Fluency sheets have at most 3 questions and no extras (writing_sheets.py:233, :245). **Keep November** (the sheet is practice; nothing is marked from a photo).
3. **Observation reminders vs observed tasks.** v2 asks the model for reminder lines; 7c8f053 gives each observed group an `observe` object the screens use. **Keep November**; drop the v2 reminder rule. Either stop asking for `observation_reminders_hi` and set "is anything observed" in code from the groups' modality (change reviewWays.js:53 to read it), or ask for one short line per group with no roll numbers. Recommend the code route (one fewer thing for the model).
4. **Per-block pace vs TODAY'S SHAPE.** Both proportional; v1 says "for a block of about 27 minutes … scale it", v2 gives percentages and a < 10 min rule. **Take v2's percentages** and put the computed minutes per block in TODAY'S SHAPE, using the same rounding as the screen's `pacePlan` (reteachInfo.js:17-27) so the prompt and the screen show the same numbers. Keep "The app shows these minutes on the plan".
5. **Hindi first person.** Draft HINDI STYLE / CFU say "मैं … पढ़ता/पढ़ती हूँ"; November forbids it. **Keep November** (B2, B3).
6. **"देखो" in the anchor.** Today's style block allows 'देखो' in the anchor (orchestrate.py:841) while STYLE_PROMPT forbids abrupt तुम commands. **Change to 'देखें'** in the rebuild (one line; tell Vaishnavi).
7. **Re-teach You Do numbers.** v1: "using the worksheet's own required count" (orchestrate.py:704); v2: "1 से 3". With 3 + N both say the same for numeracy; **keep v1's wording** (it stays right for writing sheets whose required count is not 3).
8. **Photo rule "no level from under half the sheet's points"** (02911ff, vision_analysis.py:588-597). With 3 core problems a child needs 2 marked answers for a level. **Keep**; note it in the test matrix (a sheet with one readable core answer gives no level).

## D. Code changes outside the prompt text

1. **Shape function (new):** one function `session_shape(minutes, reteach)` returning anchor, setup, transitions, the three block minutes, the pace per block, show-me count per block and extras. Used by `build_user_prompt` (replaces orchestrate.py:875-883), by `validate_plan_shape`, by the CFU keep-count, and returned to the screen if useful.
2. **Prompt caching. SDK finding:** `anthropic==0.34.0` is pinned (backend/requirements.txt:17) and installed in backend/venv. Its typed `TextBlockParam` has no `cache_control`, but tested offline on 19 Nov with a mock transport: `messages.create(system=[{"type": "text", "text": ..., "cache_control": {"type": "ephemeral"}}])` sends the field unchanged, and `response.usage.cache_read_input_tokens` / `cache_creation_input_tokens` are readable as attributes (the model allows extra fields). **So no SDK upgrade is needed for caching.** (0.34.0 also has `client.beta.prompt_caching`; not needed.) Confirm with the first real run that the second plan shows a cache read.
3. **AI meter:** `ai_budget.record` stores only input and output tokens (ai_budget.py:171). With caching, `input_tokens` excludes cached tokens, so the meter would under-count cache writes and over-state savings. Add the two cache counts (cache read at the model's cache-read price, cache write at the input price, as calibrated on 12 Nov) with `getattr(usage, ..., 0)` so the test fakes keep working.
4. **`validate_plan_shape`** (plan_service.py:585-700): replace the 5/6 rule (:634-637) with `required_count == 3` for numeracy and reading sheets, `3 + extras` problems, diagnostics only among 1-3 and only from that group's own IDs; leave writing/fluency/observed sheets to `check_writing_sheets`.
5. **CFU keep-count:** cfu.py:21 `MAX_ITEMS = 2` becomes per block (2, or 1 in a block under 10 minutes), passed in from the shape; `MIN_ITEMS` likewise (the top-up asks only for what is missing).
6. **`repair_worksheet_numbers` / `apply_bank_questions`** read `required_count` (plan_service.py:200, :394): check they keep working with 3; bank questions become the core (draft literacy rule).
7. **Per-group mistakes for the worksheet:** reuse `ctx.cfu_kb` (already fetched per group) for the worksheet diagnostics; remove `ctx.misconceptions` from the prompt (keep it for the intervention pre-teach lookup, plan_service.py:1144).
8. **45-minute option:** pwa/src/services/preferences.js:6 hides 45 (`SESSION_MINUTES = [60, 90]`); show it again only after the test matrix passes.
9. **Dead code:** delete orchestrate.py:1000-1190 and prompts/templates/*.md (check `preview_prompt`, orchestrate.py:1193, is not used by the dead function only).

**Tests that assert today's prompt text or counts (to update with the change):**
- backend/tests/test_plan_service.py:55-60 `minutes_in` parses "**Available teaching time:** N minutes" and "PART C: ROTATION SCHEDULE (N min total)" and "(N min)" lines: keep those phrasings in v2's TODAY'S SHAPE / PART C, or update the regexes. Its checks at :80-95 (45/60/90 give different layouts) stay valid.
- backend/tests/test_cfu.py:182 asserts `MAX_ITEMS == 2 and MIN_ITEMS == 2`; :204-213 expect 2 kept; :134, :161, :173, :179 use "बोर्ड पर देखो" as question text (input data: fine, but :179 checks the board form is kept).
- backend/tests/test_cfu_answers.py:94 and test_cfu_guessable.py:96-97 assert phrases in `CFU_RULES` ("DIFFERENT right answers", "WORK OUT", "already written on the board", "Use NEW nu…"): keep those phrases.
- backend/tests/test_hindi_style.py:180-181: STYLE_PROMPT phrases, and "from hindi_style import STYLE_PROMPT" in orchestrate.py: keep the import.
- backend/tests/test_two_digit_limit.py:65-90 (`repair_worksheet_numbers`), test_sample_plans.py:47-63 and test_photo_retake_16nov.py:141 use `required_count` 6 in fixtures (data: fine).
- backend/tests/test_semantic_retrieval.py:247-253 checks `_anchor_prompt_section` wording per tier: keep the tier sentences.
- backend/tests/test_names_never_reach_ai.py captures the outgoing request: must still pass with `system` as a list of blocks.
- pwa/tests/reteach_note.test.mjs:32 asserts the 2+6+7+4+8 = 27 pace for a 27-minute block (screen pace): unchanged if C4 uses the same rounding.
- New tests: the shape function (45/60/90, with and without a re-teach); the prompt contains each group's own mistake IDs and no MISCONCEPTION TAXONOMY; no "Roll" in the prompt; `validate_plan_shape` on a 3 + N plan; the system block carries `cache_control`; the meter counts cache tokens.

## E. Implementation sequence (each step separately testable; lab, fake AI)

1. **Shape function** + tests (D1). No prompt change yet.
2. **Prompt split:** fixed text into a system block (today's text, unchanged in substance), `cache_control`, meter fields (D2, D3). Tests: names guard, `minutes_in`, cache field present.
3. **Session length** in the prompt from the shape (A1, A16, C4): anchor, PART C, pace, independent-activity sizing, re-teach pace, show-me count. Update cfu keep-count (D5).
4. **Per-group mistakes** (A4, D7) and remove the Progressor-only taxonomy.
5. **3 + N** for numeracy and reading sheets (A2, A13, D4, D6); November sheet kinds untouched (C1, C2).
6. **Clean-ups:** देखें (A3, C6), roll numbers and `peer_monitors` out (A10), observation reminders by code (A5, C3), concrete principles (A8), representative note in code (A12), dead code (A7, D9).
7. **Real-model matrix** (needs the user's OK; about 12 plans, ~$2-5):

| Skill (shape) | 45 | 60 | 90 |
|---|---|---|---|
| N2.3.2 maths (written) | ✓ | ✓ | ✓ |
| L2.7.2 writing (composition) | ✓ | ✓ | ✓ |
| L2.5.1 reading aloud (fluency) | ✓ | ✓ | ✓ |
| N0.1.1 observation | ✓ | ✓ | ✓ |

   Check per plan: blocks and anchor match the shape; pace fits each block; show-me count per block (1 under 10 min); numeracy/reading sheets 3 + 1/2/3 with diagnostics only in 1-3 and from that group's own IDs; writing/fluency/observed sheets as in November; a 7-minute block teaches the group's own skill (the 29 Oct bug: N2.3.2 Beginner block drifted to "without regrouping"); no "मैं … लिखता/लिखती हूँ", no "देखो"; no roll numbers in the request; the second plan of the run shows `cache_read_input_tokens` > 0; validation warnings empty or explained.
8. **Unhide 45 minutes** (D8) only if the 45-minute column passes.

## F. Open decisions

1. **(Vaishnavi, first)** At 45 minutes two blocks are about 7 minutes. Is a 7-minute block worth teaching (I Do + We Do, one show-me, You Do at the station), or should a 45-minute session teach two groups and give the third an independent day?
2. **(Vaishnavi)** The anchor at 45 minutes: 5 minutes with one whole-class task, instead of three group tasks?
3. **(Vaishnavi)** Extras by length: 1 / 2 / 3 extra problems at 45 / 60 / 90 minutes.
4. **(Ramesh)** Observation reminders: compute "observed today" in code and stop asking the model (C3), or keep one short model line per group?
5. **(Vaishnavi)** The anchor's 'देखो' becomes 'देखें' (C6).
6. **(Ramesh)** Real-model budget for the matrix (step 7) and any re-runs.
