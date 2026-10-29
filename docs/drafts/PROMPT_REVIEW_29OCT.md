# Review of the plan prompt (29 Oct, lab)

**What was read:** the prompt the server sends today: `build_system_prompt()` and `build_user_prompt()` in `prompts/orchestrate.py` (with `_SCHEMA_COMMON`, the two
worksheet schemas, the anchor, independent-work, stick and re-teach sections), `STYLE_PROMPT` (`prompts/hindi_style.py`) and `CFU_RULES` / `render_cfu_section`
(`prompts/cfu_prompt.py`), as called by `plan_service.generate_dainik_yojana`. **Nothing is changed:** this is a list for Ramesh, most important first. Each point
says where it is and what could be done; the 3 + N worksheet itself is in `PROMPT_DRAFT_3N_WORKSHEET.md`.

## 1. Session length: the prompt still assumes 90 minutes (important now that 45 / 60 is offered)

At 45 minutes the code gives: anchor 10, setup 2, transitions 4, so 29 minutes of teaching: the first block 15 minutes (`max(…, 15)`), **the other two 7 minutes each**.
But the prompt still says:
- `_SCHEMA_COMMON`: "Size each independent activity to the length of the teach blocks (**22-29 minutes**)".
- `RETEACH_MAIN_RULES`: "Pace for a block of about **27 minutes**: recall 2, I Do 6, We Do 7, the show-me questions 4, You Do 8. Scale it…"
- `CFU_RULES`: 3 show-me questions per block (2 used), whatever the block's length.
- PART A: the anchor is always 10 minutes ("Anchor: {anchor_duration} min", fixed at 10).

**Could be done:** pass the real block lengths into those lines (they are computed in `build_user_prompt` already: `priority_duration`, `standard_duration`);
scale the anchor (for example 5 minutes at 45, 8 at 60, 10 at 90); one show-me question in a block under 10 minutes; and say what a 7-minute block can hold
(I Do and We Do only, the You Do is the worksheet at the station). **A teaching decision for Vaishnavi:** is a 7-minute block worth having, or should a 45-minute
session teach two groups and give the third an independent day?

## 2. Contradictions the model has to resolve on its own

- **Problem counts:** PART B asks for "**8-10 problems**" per sheet; `_SCHEMA_COMMON` says "**At most 8** problems"; the Proficient rule describes 6 + 2 = 8. The model
  usually follows the schema, but every contradiction costs consistency. (Fixed by the 3 + N draft, section 4.)
- **Polite forms:** `STYLE_PROMPT` says the teacher never uses 'तुम' commands ('देखें', not 'देखो'), but `CFU_RULES` gives as its model line
  'बोर्ड पर देखो: 34 + 28 = 52 लिखा है। क्या यह सही है?'. Examples weigh more than rules: change it to 'बोर्ड पर देखें: …'.
- **Whose mistakes the worksheets use:** the MISCONCEPTION TAXONOMY lists only the **Progressors'** skill's mistakes (`ctx.misconceptions` is fetched for the
  selected skill), but every sheet's `diagnostic_for_misconception` must be "an ID from the misconception list". The Beginner and Proficient sheets therefore
  either take the Progressors' IDs (wrong for their skill) or none. The CFU section already lists each group's own mistakes: use that one per-group list for both
  the show-me questions and the worksheets (it also removes the duplicate below).

## 3. The observation reminders can describe a task the plan does not contain (known, `docs/KNOWN_ISSUES.md`)

PART E asks for observation reminders with only the skill and the rolls, so the model invents what to watch (on 29 Oct, N0.1.1 asked the teacher to watch a
sorting task the You Do did not have). The screens now show a general line instead, so nothing wrong reaches the teacher, but the prompt rule drafted in
`KNOWN_ISSUES.md` is still to apply: *each reminder names the activity of that group's You Do (or its worksheet problem numbers) and what A / PA / NA look like
in it, in the reviewed words.* Then the screens could show the plan's own reminder again.

## 4. Cost and speed: the same few thousand words are sent and paid for on every plan

About two thirds of the user prompt never changes between plans: `_SCHEMA_COMMON` and the worksheet schema, `STYLE_PROMPT`, `CFU_RULES`, `RETEACH_MAIN_RULES`,
most of the stick policy. **Could be done:** move the fixed text into the system prompt (it is short and generic today) and mark it for **prompt caching**
(`cache_control` on the system block), so repeated plans read it from the cache at a fraction of the input price and a little faster. The per-plan facts stay
in the user prompt. Two things to check first: the pinned SDK is `anthropic==0.34.0` (prompt caching may need a newer SDK or the beta header), and the cached
part must be at least the model's minimum cacheable length (it is well above it).

**Also:** the MISCONCEPTION TAXONOMY and the CFU section print the Progressors' mistakes twice (pattern, how to detect, right and wrong examples). With the
per-group list of point 2, once is enough.

## 5. Dead code that could mislead

- `prompts/orchestrate.py` has its own `generate_dainik_yojana` (about line 987) with the model **hard-coded as "claude-sonnet-4-6"**, `max_tokens=8000`, no
  checks, no AI limit, no metering. The server never calls it (`routes.py` uses `plan_service.generate_dainik_yojana`, which uses `settings.claude_model` and
  24,000 tokens). Anyone running the orchestrator directly would get an old model and a cut-off plan. Remove it, or make it call the server's function.
- `prompts/templates/dainik_yojana_system.md` and `dainik_yojana_user.md` (330 lines) are not read by any code. If they are an older copy, remove them or mark them
  as history, so nobody edits the wrong prompt.

## 6. Smaller points

- **The system prompt's principles** are generic ("Noise-robust assessment. Use the competency's modality tag…", "Offline-friendly"): the model cannot act on
  them. Either make them concrete (what the modality means for the review prompts and the worksheet) or drop them; the real rules are in the user prompt.
- **"AI proposes, teacher decides. Tone is supportive, never prescriptive"** is good, and could carry the reviewed wording rules (gender-neutral teacher,
  polite forms) so they sit in the cached part.
- **Roll numbers** are sent for every group (used for peer monitors and the observation reminders). Fine for privacy (no names; the teacher is sent as "Teacher"),
  but the peer monitor could be chosen in code instead, and the rolls left out of the prompt.
- **The output format:** the model is asked for bare JSON and the server strips code fences and retries once on bad JSON. With a newer SDK, structured outputs
  (a JSON schema the API enforces) would remove the parse failures and the retry's cost.
- **Explainability** asks for "5-6 items" including "assumptions and limitations (the curriculum plan is a representative plan…)": the same sentence on every
  plan. It could be added by the code, and the model's items kept for what is specific to the plan.

## Suggested order

1. Point 2 (contradictions) and the 3 + N draft together: they touch the same lines.
2. Point 1 (session length): needed before 45 / 60 minutes is used for real.
3. Point 3 (observation reminders).
4. Point 4 (caching) and point 5 (dead code): no change to what teachers see; cost and safety.
5. Point 6 as time allows.

Each needs a real-model run per skill shape (maths, writing, reading aloud, observation) and the plan checks updated with it; the lab has no API key, so that
run happens on main.
