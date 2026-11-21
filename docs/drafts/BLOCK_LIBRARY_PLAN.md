# The recorded-block library: generation plan (for approval)

**Status:** a plan, 21 Nov 2026, lab. **Nothing has been generated.** It needs the user's approval (the cost cap and the pilot) before any paid
call. Why now: the Anthropic credits expire on **30 Nov 2026** and no new credits are known; generating the library is the one large job that
needs them. Everything after generation (the assembler, offline use, review) needs no credits.

## 1. What the library is for

A plan assembled by CODE from reviewed (or, until reviewed, AI-drafted) pieces, so Ankur Saathi can serve **any** plan a teacher's choices lead to
(any skill for any group, re-teach or move on, 45 / 60 / 90 minutes) **with the AI off, and, once the assembler runs in the app, with no network.**
Every piece is keyed by ONE group's own skill, never by a combination of three skills: a teacher's choices only change which pieces are taken.
Background: the discussion of 20-21 Nov (docs/HANDOVER.md, "The library and offline"), and the test that showed reviewed examples carry the
teaching approach and the Hindi style even to a small model (docs/drafts/prompt_v2_runs/README.md, the Haiku example test).

## 2. The pieces, and how many

Counts from the lab database (21 Nov): 101 skills; numeracy 33 written + 20 observed; literacy 4 reading, 5 fluency, 5 formation, 2 usage,
1 dictation, 3 composition, 28 observed; 64 recorded mistakes on 30 skills; 14 anchors.

| Piece | Key | What it holds | How many |
|---|---|---|---|
| **Teach block** | skill · mode · length | the block's talking points (I Do, We Do if the length has one, You Do), its show-me questions (3 written; code keeps 1 or 2), and the group's worksheet in the skill's own sheet kind (3 core + 3 extras for maths and reading; the November shapes for writing, fluency and observed) | 101 skills × 3 lengths = **303** |
| **Re-teach block** | skill · mistake · length | the same, as a re-teach of ONE recorded mistake (mistake first, find and fix, the worksheet aimed at that mistake) | 64 mistakes × 3 lengths = **192** |
| Re-teach, skill without recorded mistakes | skill · length | phase 1: **no generation**; code uses the teach block with a re-teach note (the general re-teach). Phase 2 if the pilot shows it is needed | 0 (phase 1) |
| **Independent activity** | skill · variant | what a group does on its own with an already-taught skill: the task (board, sheet or kit), a core and "if you finish early" extras, the materials. Code sizes it to the block (how many extras) | 101 × 2 = **202** |
| **Anchor setting** | domain · setting | the whole-class story: the setting, the board picture, the narration, the opening and closing questions | 25 per subject = **50** |
| **Anchor task** | setting · skill | one group's task inside a setting, with the numbers or words left as slots that code fills within the skill's range | each skill in 3-4 settings ≈ **350** |

**Lengths:** three nominal lengths cover every session: **short 7** (45 minutes' Proficient slot), **medium 14** (45's 14 and 16, 60's 13),
**long 22** (60's 18, 90's 22 and 30). Code scales the pace to the actual minutes (prompts/session_shape.py) and, for a longer slot, adds extras.

**Total: about 1,100 pieces.** Repetition is reduced by code (numbers varied within the skill's range, a different setting from last time); a
second variant of the teach blocks for the most-taught skills is a phase-2 option.

## 3. The model, and the cost cap

- **Model: Claude Sonnet 5.5, thinking off** (`between_tools`, app/services/model_options.py). Reason: the library is reused for years, so
  quality matters more than the cost per piece, and Haiku 5.5 skipped show-me questions and broke observed and fluency sheets in the 20-21 Nov
  tests (docs/HANDOVER.md, "Model tests").
- **The fixed rules are the app's own cached system prompt** (prompt v2): the same Hindi style, show-me rules, sheet rules. A new, short
  per-piece prompt asks for ONE piece in a fixed JSON shape.
- **Message Batches** (half price) for the full run; the pilot runs as normal calls so problems show at once.
- **Estimate** (Sonnet $2 in / $10 out per million, cache reads $0.10; a teach block about 3,000 output tokens):

| Piece | Each | All |
|---|---|---|
| Teach and re-teach blocks (495) | ≈ $0.035 | ≈ $17 |
| Independent activities (202) | ≈ $0.006 | ≈ $1.2 |
| Anchor settings (50) | ≈ $0.012 | ≈ $0.6 |
| Anchor tasks (350) | ≈ $0.005 | ≈ $1.8 |
| Re-generations of pieces that fail a check (assume 20%) | | ≈ $4 |
| **Total, normal calls** | | **≈ $25** |
| **With Message Batches (half price)** | | **≈ $13** |

- **Hard cap: $40** for the whole job (the generator stops and reports); **pilot cap: $3.** The meter records every call (kind `library`).

## 4. Where each piece is stored

- **Files first** (version-controlled, reviewable, safe if anything stops): `db/seeds/library/<kind>/<key>.json`, one file per piece, e.g.
  `teach/N2.3.2__normal__medium.json`, `reteach/N2.3.2-M1__long.json`, `independent/N2.3.1__1.json`, `anchor_setting/numeracy__market.json`,
  `anchor_task/numeracy__market__N3.3.1.json`.
- **Every file carries:** `piece`, `key`, `skill_id`, `mode`, `length`, `content` (the piece), `checks` (what passed, any warning), `model`,
  `prompt_version` (a hash of the system rules and the piece prompt), `created`, `cost_usd`, `review_status` (`ai_drafted` → `reviewed` /
  `rejected`), `reviewed_by`, `review_notes`.
- **A manifest** `db/seeds/library/MANIFEST.json`: every planned key with its status (`todo`, `ok`, `failed_checks`, `rejected`) and cost.
  The generator reads it and **skips what is done**, so a stopped run continues where it left off.
- **Into the database** (later, by a loader like scripts/load_embeddings.py): new L2 tables (`library_teach_blocks`, `library_independent`,
  `library_anchor_settings`, `library_anchor_tasks`). **For the phone:** one compressed bundle (text only, estimated 2-4 MB).

## 5. The checks every piece must pass (code, no AI)

The app's own checks, run on each piece as on a plan:
1. **Shape:** the JSON fields; a short block has no We Do; the You Do of a short block only starts the task.
2. **Hindi:** the style softening, the neutral-quote rewrite ('मैं ... छाँटूँगी' → 'हम ... छाँटेंगे'), and check_teacher_text (no gendered first
   person, mark names right); no English words in Devanagari; no 'यानी' self-corrections.
3. **Show-me questions:** clean_plan_cfu (arithmetic recomputed, own mistake IDs, nothing copied from the lesson); at least 2 must survive.
4. **Worksheets:** 3 core + 3 extras for maths and reading, `required_count` 3, diagnostics only in the core and only the skill's own mistake
   IDs; the number range and carry / no-carry rules; nothing copied from the lesson; and **every plain + / − / × answer recomputed by code**
   (this is the "code-computed answer keys" roadmap item: it is built here first and reused by the live plans). Writing, fluency and observed
   sheets: writing_sheets' own checks.
5. **Independent activities and anchor tasks:** only the skill's own operations and range; every number slot fillable inside the range.
6. A piece that fails is generated again **once**, with the reasons; if it fails again it is marked `failed_checks` for a person.

## 6. The order of work

1. **Generator and checks** (code, no AI, tested with the fake model): about 1.5-2 days.
2. **Pilot (paid, cap $3):** 10 skills, all piece kinds: the six recorded-plan skills (N0.1.1, N2.2.1, N2.3.2, L2.3.1, L2.5.1, L2.7.2) + N2.3.1,
   N3.3.1, L1.7.3, L3.5.1. The user (and, if possible, the education lead) reads a sample; the prompts are adjusted.
3. **Full run (paid, cap $40, Message Batches):** the remaining pieces; failures re-generated once. Must finish by **29 Nov** (batches can take
   up to 24 hours).
4. **After 30 Nov, no credits needed:** the loader; the assembler (server first, then in the app for offline); the screen label "AI-drafted,
   not yet reviewed"; the review tool for the education lead (most-taught skills first).

## 7. Decisions for the user (before step 2)

1. Approve the **cost caps** ($3 pilot, $40 total) and **Sonnet 5.5** as the model.
2. Approve **three nominal lengths** (7 / 14 / 22) instead of every exact length.
3. Approve **phase 1 without** generated general re-teach blocks (skills with no recorded mistakes use the teach block + a re-teach note).
4. Whether the education lead can review the pilot sample before the full run (it would improve the prompts; it can also come later).
