# Handover: where the work stands, and how to continue it

**Written 21 Nov 2026** at the end of a long working session (Claude Code with the project lead), so that a new session, or a person, can
continue exactly where the work stopped. **Read sections 1-3 first.** Section 6 is the work list: each item has a status, the next action,
and where its details are. Update this file (and its date) whenever an item moves.

---

## 1. Working rules (agreed with the project lead; follow them exactly)

1. **Build only in the lab worktree** `C:\dev\Ankur-Saathi-lab` (its own database `ankur_lab`, backend on port 8001, screens on 5174). `main`
   is checked out in `C:\dev\Ankur-Saathi` and is what is deployed. New work goes on a lab branch made from `main`.
2. **Ask before every commit**, showing the files and the message. Commit only if `scripts/precommit_check.py` itself exits 0 (never pipe it
   through `tail` before `&&`). End each commit message with the co-author line the session is given.
3. **Never print or repeat the Anthropic API key.** It is set in the shell environment and overrides `.env`, so a backend or script started
   from the lab makes REAL, billed calls. For tests and servers, start with the key replaced:
   `env -u ANTHROPIC_API_KEY ANTHROPIC_API_KEY=sk-dummy-never-used` (and `AI_ENABLED=false` for a server). **Real AI calls only with the
   lead's OK**, with a cost estimate first.
4. **The lead runs every merge, push and deploy** (`git merge --ff-only`, `git push`, `gcloud ...`). Prepare the steps; do not run them.
5. **Never use a bare `git stash`** (the stash is shared between worktrees).
6. Stop servers by Windows PID (`netstat -ano`, `taskkill //PID n //F //T`).
7. **Language with the education lead (Vaishnavi):** any new Hindi the teacher sees goes to her for review. Teacher lines are polite instructions
   (बोलें, लिखें), never a gendered first person, also inside quotes ('हम ... करते हैं'); "next class", never "tomorrow".
8. This machine has run low on memory several times (servers and long runs were stopped by Claude Code). Run plan batches in small groups.

## 2. Where things are

| What | Where |
|---|---|
| Deployed code | `main` = `112b953` (deployed 17 Nov). Live service on Google Cloud Run (Mumbai); the lead holds the project details and deploy steps (`docs/LAB_TO_MAIN.md`) |
| Prompt v2 (ready for review, not merged) | branch **`lab/prompt-v2`** in the lab worktree, 9 commits on `main` (section 4) |
| Roadmap §17 (EmbeddingGemma) | branch `lab/enhancements` = `main` + `32eaa59` (docs only; merge with the next release) |
| The 12 test plans of prompt v2 + check report + the test tools | `docs/drafts/prompt_v2_runs/` (README explains; tools in `tools/`) |
| Scratch outputs of all model tests (not in git) | `C:\dev\ankur-scratch\v2_run\` (`out/` Sonnet, `out_haiku/`, `out_haiku_think/`, `out_haiku_example/`) |
| The library generation plan (for approval) | `docs/drafts/BLOCK_LIBRARY_PLAN.md` |
| Placement spec (the next big feature) | the lead's "Placement slice_ spec.pdf"; text in `C:\dev\ankur-scratch\placement_spec\spec.txt` |
| Project state, honestly labelled | `docs/STATUS.md`, `docs/KNOWN_ISSUES.md`, `docs/ROADMAP.md` |

**API credits:** the Anthropic credits expire on **30 Nov 2026**; no new credits are known. Work that needs real AI calls goes first (section 6).
Real-AI spend 19-21 Nov on prompt v2 and model tests: about **$2.90** (Sonnet $2.65, Haiku $0.20, example test $0.02).

## 3. If you are a new session: do this first

1. `cd C:\dev\Ankur-Saathi-lab && git status && git branch --show-current` (expect `lab/prompt-v2`). Check for uncommitted work (section 5).
2. Read section 6 and ask the lead which item to continue; do not start paid runs without the OK.
3. Run the tests before and after any change: `env -u ANTHROPIC_API_KEY ANTHROPIC_API_KEY=sk-dummy-never-used backend/venv/Scripts/python.exe scripts/run_tests.py --env-file backend/.env --pwa`.
   Everything passes except `test_submission_check`, which only objects to commits after the hackathon's 1 Nov deadline (expected).

## 4. What was done (19-21 Nov), on `lab/prompt-v2`

**Prompt v2** (the plan prompt rebuilt; plan: `docs/drafts/PROMPT_V2_REBUILD_PLAN.md`):

| Commit | What |
|---|---|
| `dfaa0d2` | the rebuild plan against v1 (what to carry forward, conflicts, order) |
| `fd43614` | steps 1-2: one session-shape function (`prompts/session_shape.py`); the fixed rules in a **cached** system block; the AI meter counts cached tokens (two new `ai_usage` columns, added by the app itself on first use, or by `db/schema/10_ai_usage.sql`) |
| `9f9964d` | step 4: **each group's own mistakes** in one list, for show-me questions and worksheets; code clears a mistake ID from another group's skill |
| `7b97a09` | step 5: the **3 + N worksheet** (3 core problems = the signal, 1/2/3 extras at 45/60/90 minutes); writing, fluency and observed sheets keep their November rules |
| `6300754` | step 6: concrete plan rules; no roll numbers or peer monitors in the request; observation reminders and the weekly-plan note written by code; old unmetered code removed |
| `d78f074` | step 3: **the 45-minute session from the team's table** (anchor 5, Beginners 16, Progressors 14, Proficients 7, transitions 2+1; a re-taught group takes the longest block; one show-me question per block); every block's minutes and pace in PART C; no lost minute at 60 and 90; the screen shows a block's own pace |
| `7f89000` | from the 45-minute run: a short block needs no We Do; skills without recorded mistakes still write show-me questions |
| `057ba6e` | from the AI-assisted review of the 12 plans: no gendered 'मैं' even in quotes (rule + **code rewrite** to 'हम' + check), no self-corrections or English words, no length but PART C's, a short You Do only starts the task |
| `36f0711` | the 12 real-model test plans (4 skills × 45/60/90) and their check report |

**Results:** all 12 plans pass every check; the cache works (≈9,600 tokens read per plan after the first); Sonnet plans cost $0.11-0.14 each.
Remaining slips are one-off Hindi errors (e.g. 'मेला में' for 'मेले में') that need a person or the planned second AI pass (ROADMAP §12).

## 5. Uncommitted work (at the time of writing)

- `backend/app/services/model_options.py` (new) and its use in `plan_service.py` and `review_service.py`: each Claude model gets the thinking
  setting it accepts (Sonnet 5.5 `between_tools`, Haiku 5.5 `disabled`, Opus 5.5 effort `low`); `CLAUDE_THINKING_OVERRIDE` for test runs.
  Tests pass. **Waiting for the lead's OK to commit.**
- This file, `docs/drafts/BLOCK_LIBRARY_PLAN.md`, `docs/drafts/prompt_v2_runs/tools/` (the test tools copied from the scratch folder).

## 6. The work list (credit-dependent items first)

Status: ✅ done · 🔶 waiting on someone · ⏳ next · ⬜ not started.

| # | Item | Status | Next action | Details |
|---|---|---|---|---|
| 1 | **Generate the block library** (the only big job that needs the credits) | ⏳ | the lead approves `docs/drafts/BLOCK_LIBRARY_PLAN.md` §7 (caps $3 pilot / $40 total, Sonnet, 3 lengths); then build the generator and checks (~1.5-2 days, no AI), pilot, full run with Message Batches **by 29 Nov** | `docs/drafts/BLOCK_LIBRARY_PLAN.md` |
| 2 | Prompt v2: the lead's own review on screen | 🔶 lead | start the lab servers (AI off), run `docs/drafts/prompt_v2_runs/tools/load_for_review.py --env-file .env` from `backend/` to date the plans today; accounts V245NA ... V290NB, password 4826 | §4; folder README |
| 3 | Prompt v2: questions for Vaishnavi | 🔶 Vaishnavi | (a) the short You Do "start in the block, finish at your place next block"; (b) N0.1.1: Proficients' second sorting rule; (c) how much board writing is realistic before class; (d) new Hindi lines: the weekly-plan note "ऐप में अभी एक नमूना साप्ताहिक योजना है, राज्य की आधिकारिक योजना नहीं।" and the reminder "… समूह: स्वतंत्र अभ्यास (तुम करो) के दौरान …"; (e) extras 1/2/3 at 45/60/90 | §4 |
| 4 | Show the 45-minute option again | ⬜ | after #2/#3: `pwa/src/services/preferences.js` (`SESSION_MINUTES = [60, 90]` → add 45) | KNOWN_ISSUES "45-minute plans are hidden" |
| 5 | Merge `lab/prompt-v2` to `main` and deploy | 🔶 lead | after #2-#4; the lead runs the merge and deploy; the two meter columns appear by themselves | `docs/LAB_TO_MAIN.md` |
| 6 | Code sets every block's minutes from the layout (models add stray transitions) | ⬜ | ~1 hour: after the model writes, set teach/transition/anchor minutes from `group_layout` and drop extra transitions; protects any model | Haiku tests, section 7 |
| 7 | Model comparison: **Gemini** | 🔶 lead | needs a Gemini API key in `C:\dev\ankur-scratch\v2_run\.gemini.env` (`GEMINI_API_KEY=…`, never in chat) and the lead's OK to send the test prompts (no names) to Google; then a test-only adapter in the runner, same 12 settings | section 7 |
| 8 | Model switch by a setting (Sonnet / Opus / Haiku) | 🔶 | commit `model_options.py` (section 5); per-model prices in the meter are still one setting (`AI_PRICE_*`) and would need per-model values | section 5 |
| 9 | Batch test of the 74 skills never run through the model (§9), refresh coverage labels | ⬜ | ~$10-30 Sonnet; worth doing with v2 before 30 Nov if credits allow after #1 | ROADMAP §9 |
| 10 | Code-computed maths answer keys (+ photo marking compares with them) | ⬜ | built inside #1's checks first, then used by live plans (~half a day) | 18 Nov discussion: only show-me questions are fully recomputed today |
| 11 | Offline: record ticks/scores/decisions/photos offline and sync later (IndexedDB) | ⬜ | ~1 week, no AI | STATUS §5 (❌ items); section 8 |
| 12 | Offline: the assembler on the phone (library + rules), names kept only on the phone | ⬜ | after #1; ~1-1.5 weeks + 3-4 days | section 8 |
| 13 | Placement slice (ASER-style) incl. sub-levels for skewed groups and a peer-helper list | ⬜ | new lab branch from `main`; Vaishnavi's item bank and cut-offs pending | memory note "placement-slice"; spec PDF |
| 14 | EmbeddingGemma vs BGE-M3; embedding text fixes ("Grade 3" not "grade_3"; skills missing descriptions) | ⬜ | with the content expansion; the two fixes were asked for on 17 Nov and are not yet in ROADMAP §17 | ROADMAP §17 |
| 15 | Deck wording fixes (if the deck is used again) | ⬜ | "the last class's evidence"; notes "the next class's plan"; softer line about child apps; never "reviewed" for the content bank; "code verifies its maths and computes every score and level" instead of "recomputes every answer key" | section 9 |
| 16 | Content review by Vaishnavi: 9 passages, 15 re-teach templates, 12 TLMs (all `ai_drafted`) | 🔶 Vaishnavi | most-taught skills first | ROADMAP §9 |

## 7. Model tests (19-21 Nov): what was learned

| Model / setting | Result | Cost per plan |
|---|---|---|
| **Sonnet 5.5, thinking off** (`between_tools`) | all v2 rules kept; the reference | ~$0.12-0.14 |
| Haiku 5.5, thinking off | ~25× cheaper and faster; but often skipped show-me questions (sometimes none survived), broken observed sheets, beginners' fluency sheet without a passage, 45-minute sessions of 46-47 minutes | ~$0.005 |
| Haiku 5.5, thinking medium | all 4 plans spent the whole 24,000-token budget thinking: no plan | — |
| Haiku 5.5, thinking low | better observed sheets and show-me questions in some plans; one fluency plan with empty sheets; still extra minutes | ~$0.009 |
| Haiku 5.5 + a REVIEWED example in the prompt (N2.3.2) | the teaching approach and Hindi style followed the reviewed plan closely; structure (show-me questions, minutes) did not improve | ~$0.006 |

**Conclusions:** Sonnet stays the main model. Reviewed L2 content improves what a small model writes; structure needs code (#6); show-me
questions need a capable model or a reviewed question bank. Haiku is a possible cheap fallback for maths skills, behind the code checks.
Opus 5.5 cannot switch thinking off (effort `low` only), so it needs a larger output budget. Gemini: not tested yet (#7).

## 8. Design decided in discussion (20-21 Nov), not yet built

**The block library** (#1): every piece keyed by ONE group's own skill (teach and re-teach blocks, independent activities, anchor settings and
anchor tasks), so any teacher choice is served by assembly, not by a pre-made combination. Code fills numbers within each skill's range and
avoids repeating the last setting. What stays weaker than a live AI plan: a less tailored anchor story, generic connecting text, repetition.

**Offline-first, AI-optional:** (1) plans assembled on the phone from the library and the rules (no AI, no network); (2) ticks, scores,
decisions and photos stored on the phone and synced when there is a signal; (3) AI centrally and in bulk where it adds most (photo marking in
batches, refreshed plans overnight with Message Batches for classes that synced); (4) children's names only on the phone.
**Rough yearly cost per teacher** (2 subjects, 200 days, ₹85/$): Sonnet every plan ≈ ₹4,800; Haiku ≈ ₹320; library on the phone ≈ ₹0 plus
photo marking and refreshes.

**Stronger L2 lowers the model needed:** the more of a plan comes from reviewed pieces (examples per skill, curated core problems and show-me
questions, re-teach templates for all 64 mistakes, more passages), the more the model only fits pieces together, and a smaller model with no
thinking can do it. The bottleneck is the education lead's review time, so review most-taught skills first.

## 9. Other decisions and facts from 17-21 Nov

- **Finale (18 Nov): Ankur Saathi placed in the top three.** Only the video and the deck were used; the live app was not demonstrated and its
  `min-instances` was never raised (nothing to undo).
- **Claims to keep accurate:** "code recomputes every sum and answer key" overstates it: code fully recomputes the **show-me** questions, replaces
  worksheet sums it cannot trust, and computes every score and level; worksheet answer keys and Hindi answers are not yet checked by code (#10).
  The L2 content bank (passages, re-teach templates, TLMs) is `ai_drafted`, never "reviewed".
- **Semantic retrieval (BGE-M3 + pgvector):** built and evaluated on the anchors only (75% first vs 25% by chance); switched off; it cannot be
  shown live without pgvector on the database (not checked on live). Details: `docs/SEMANTIC_RETRIEVAL.md`.
- **Prompt caching** lasts about 5 minutes: a small saving in normal use, a large one in batch runs (#1, #9).
- **Sign-in log on 18 Nov:** a burst of wrong passwords locked one account for 15 minutes (5 wrong → locked, a 429); no AI-cap refusals.
