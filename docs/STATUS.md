# Status: what is built, against the original proposal

The Ideate-stage proposal made a number of promises. This table says, for each, what the build does **today**. It is kept up to date as work ships, and it is deliberately candid: where the build differs from the proposal, or a promise is not built, it says so.

✅ built and checked · 🟡 partly built, or built differently · ❌ not built · ⏸ deferred in the proposal itself

*How to update: change the symbol and the note of the row when something ships, then run `python scripts/submission_check.py`.*

## 1. THE DAILY LOOP AND THE PLAN

| | Promise | Where it stands |
|---|---|---|
| ✅ | Teacher picks the subject and today's Lakshya (Numeracy, R1 Hindi, R2) | Numeracy 53 skills and R1 literacy 48 skills, Balvatika to Grade 3. R2 was never in the 3-week scope (the roadmap itself says numeracy + R1). |
| ✅ | Children auto-clustered into 3 groups from their Lakshya position | Per subject; the teacher can change a group's skill in the drawer (`GroupSkillsDrawer`). |
| 🟡 | AI generates the whole package in under 60 seconds | About 65 s typical (11k tokens). About 130 s when the model's first reply cannot be read and the app asks again: v29f repairs the cause found in the logs. |
| ✅ | Whole-class anchor activity from the content bank | L2 bank: 14 anchors. Exact / related / topic-area / loose match, stated to the model. Semantic fallback built (v29g), OFF until the Thursday gate. |
| ✅ | 3 teaching scripts: I Do / We Do / You Do with talking points per group | Every sum and answer key is also checked by code (added beyond the proposal). |
| 🟡 | 3 levelled printable worksheets with roll-number grid | Done and print-ready, but as HTML printed from the browser, not server-made PDFs. Place-value grid, carry tab, board-work line for schools without printers. |
| ✅ | Rotation schedule, transition scripts, peer monitors, warm-ups for independent groups | Rules in the prompt; checked with the real model on 27 of the 101 skills so far (`docs/batch/batch_results.csv`). |
| ✅ | Re-teaching built from yesterday's gaps (the loop closes) | Evidence-driven suggestion per group, the teacher's recorded decision drives it, re-teach is the group's main block. Check-for-understanding questions added (not in the proposal). |
| ✅ | Advance / Re-teach / Not sure BEFORE the AI analysis; the AI proposes, the teacher decides | `/review/decisions` comes first; Progressors cannot move on separately (anchor design). |

## 2. THE THREE-LAYER KNOWLEDGE ARCHITECTURE

| | Promise | Where it stands |
|---|---|---|
| ✅ | Layer 1: competency tree with prerequisite links, Balvatika to Grade 3 | 101 skills, 142 prerequisite links, all four grades. |
| ✅ | Layer 1: A/PA/NA criteria per skill and an assessment-modality tag | 101 of 101 have both. |
| ✅ | Layer 1: misconception taxonomy, each mapped to an intervention | 55 misconceptions (34 numeracy, 21 literacy); 15 intervention templates. |
| ✅ | Layer 1: one pilot state's weekly curriculum plan | Madhya Pradesh, 171 weeks (`/plan/curriculum-week`). |
| ✅ | Layer 2: anchors, reading passages, intervention templates, TLM references | 14 / 9 / 15 / 12 rows. Small: the larger gain is more content. |
| 🟡 | Layer 2: semantic retrieval on pgvector, embeddings in the database | Built in v29g: open-weights model (BGE-M3, 1024 dims) run offline, vectors loaded by the nightly job, no embedding call at runtime. Switch OFF until Thursday's gate; real-vector quality not yet measured. |
| ✅ | Layer 3: Claude generates only inside the L1 + L2 context | Plus deterministic validators: number ranges, the two-digit cap, answer keys, JSON repair, spend caps. |
| ✅ | Worksheets validated against the competency benchmarks before delivery | `skill_rules` and the worksheet number repair. |

## 3. EVIDENCE CAPTURE AND ASSESSMENT

| | Promise | Where it stands |
|---|---|---|
| ✅ | Photo channel: Claude Vision reads the answers by roll number and classifies misconceptions against the taxonomy | `/review/analyse-photos`, the taxonomy comes from Layer 1. |
| 🟡 | Photo analysis validated on real children's handwriting (the proposal named this a risk to test in the Build stage) | **Not validated; a smoke test only** (`docs/vision/`): 5 worksheets, one skill (N2.3.2), handwriting by an adult, not children. It read the roll number 5 of 5 and 39 of 40 answers correctly (30 of 30 sums, judged right or wrong exactly as the teacher did), found 5 of 8 copying slips, and named the mistake pattern correctly on 1 of 3 sheets. A test on children's handwriting, more skills and Hindi sheets is still to do (protocol: `docs/VISION_PHOTO_TEST.md`). |
| ✅ | Sampling: all of the taught group, a rotating system-chosen sample of the others | `docs/SAMPLING.md`. |
| ✅ | Observed channel: the teacher taps Achieved / Partial / Not achieved per child | `/review/observed`. |
| ✅ | Reading fluency: stopwatch + manual entry (CWPM + errors) | `/review/orf`. The teacher times one child and types the result; **no audio is recorded** (a class of groups at work is too noisy for a clear recording). A code check keeps the app unable to record sound. |
| ✅ | Photos discarded after analysis; no audio is ever recorded | Photos are read and compressed in memory; nothing is written to disk or the database (checked). The app has no microphone access (checked in the code). |
| ❌ | Guided camera with an alignment frame overlay | It is the phone's own camera (a file input with `capture`). No frame overlay. |
| ✅ | Memory-safe capture: compress to 1600 px / 80% before upload | Photos shrink on the phone: 1600 px at quality 0.8, and 1200 px at 0.7 on phones that report 2 GB of memory or less (Chrome and Edge on Android report it), then again on the server. |
| ❌ | Tier 3: on-demand deep assessment for one child | Not built. |
| 🟡 | Photo analysis flags unclear handwriting for the teacher to verify | **Partly built.** The AI gives each answer a confidence (high, medium, needs verification, unclear) and the Review screen shows "👀 check in the notebook: problem N" under a child when an answer is marked needs-verification or low; an unreadable roll number says "retake the photo". Not built: the screen does not flag "medium" (in the first scored run the one misread answer was "medium", so no warning showed), there is no photo-quality note, no log of flags and what the teacher did, and the photo is not kept to show the unclear patch. The AI was also confidently wrong on copying slips (`docs/vision/`). Roadmap: section 12. |

## 4. LEVELS, PROGRESS AND REPORTING

| | Promise | Where it stands |
|---|---|---|
| 🟡 | Path A: ingest existing assessment data (Mission Ankur, ASER, MLO records) to place children on Day 1 | A class register upload (CSV or Excel, template + preview + confirm) places children by the teacher's OWN level per subject, or Progressor if left empty (`docs/REGISTER.md`). Nothing maps state assessment data to Lakshya positions. |
| 🟡 | Path B: the system's own graded baseline diagnostic, run in the app | The backend exists (`/baseline/generate`, `/baseline/submit`) but there are NO screens for it (`docs/LEVELS.md`): a teacher cannot run it in the app today. |
| ✅ | NIPUN's own B/P/P thresholds (at least 75% Achieved = Proficient; at least 50% = Progressor) | In `compute_placement` (`prompts/baseline_assessment.py`). It feeds only the baseline, which has no screens. |
| ❌ | Periodic full-class reassessment that re-clusters the groups, with a history of rounds | Not built (`docs/LEVELS.md`): no screens for rounds and only each child's latest level is kept. What exists: 'consider re-assessing' flags when daily work no longer matches a level. |
| 🟡 | Daily level-change recommendations (3+ days of evidence) that the teacher approves or defers | Built differently, on purpose: a flag changes NOTHING; a child's level changes only through an assessment. Daily evidence changes the PLAN (re-teach, a group's skill), not the level. |
| ✅ | Per-child Lakshya tracker and Progress dashboard (B/P/P view) | Per-child list with level and 'as of' date. Not built: tapping a child to see a competency map. |
| 🟡 | Teacher can override any AI decision | Yes for each group's skill and the re-teach choice. No tap-to-override of a child's level. |
| 🟡 | MLO-exportable progress report (CSV or PDF) | CSV only (a class version and an officer version). |

## 5. OFFLINE, LOW DATA, LOW-COST DEVICES

| | Promise | Where it stands |
|---|---|---|
| ✅ | PWA: installs from a shared link, no app store | Service worker, manifest, no external hosts. |
| ✅ | TEACH works fully offline once the plan is loaded | Measured in a real browser with the server stopped: the app opens, the skill list shows, and today's plan reopens with all its blocks, also after a fresh Generate and after the app is closed and reopened (the copy is kept for 24 hours). `docs/OFFLINE.md`. |
| 🟡 | Worksheets work offline | A plan's worksheets are prepared automatically while it is on screen and then open and print with no network for 24 hours. A worksheet that was never prepared (a plan made on another phone) still needs the internet. |
| ✅ | Clear behaviour when there is no network | An offline notice (it appears and clears by itself), Generate and photo sending switched off with the reason, one clear sentence in Hindi and English instead of 'Failed to fetch', no blank tab left behind. Checked in a real browser with the server stopped. |
| ❌ | REVIEW capture and the Advance/Re-teach decision work offline, queued and synced later (IndexedDB) | Recording a decision, observations and reading scores, and sending photos, still need the internet; the app says so. Nothing is queued for later yet. |
| ✅ | Light on data | The whole app is 336 KB raw; the server now compresses what it sends, so the first load travels 88 KB (measured in a real browser). Plan and worksheet reads fall back to the saved copy after 6 seconds on a slow connection. |
| ❌ | Tested on budget Android phones (2-3 GB RAM) | Not yet tested on budget Android phones with 2 to 3 GB of RAM. |

## 6. PRIVACY (DPDP) AS PROMISED

| | Promise | Where it stands |
|---|---|---|
| ✅ | Only roll numbers reach the AI; no child's name does | A static guard test fails the build if anything that builds an AI request reads the names table (`docs/PRIVACY.md`). |
| ❌ | The name-to-roll mapping lives ONLY on the teacher's device (IndexedDB); the server holds no mapping | Different in the build: names are stored in a separate teacher-only table on the server and shown only on the teacher's own screens. They are never sent to the AI (a test fails the build if code that builds an AI request reads that table: `docs/PRIVACY.md`). |
| ❌ | Local-first storage; the server holds only anonymised aggregates | The server holds per-child positions and evidence keyed by roll number (and the names table above). |
| ✅ | Hosted in India | Cloud Run and Cloud SQL in asia-south1 (Mumbai). Worksheet photos (roll numbers and handwritten answers) are sent to the AI provider for analysis: `docs/PRIVACY.md`. |
| 🟡 | Verifiable parental consent recorded at onboarding | The school confirms, when it is created, that parents have been told and have given permission; the exact wording, its version, the date and who confirmed are kept, and an older school's admin can confirm later. It is the SCHOOL's confirmation, not a record from each parent (`docs/PRIVACY.md`, "Consent"). |
| ✅ | No tracking, profiling or behavioural monitoring | No analytics, ads, trackers or third-party hosts. |
| ✅ | Sign-in, school leader tools, rate limits, spend caps | Beyond the proposal: employee code + password, lockouts, the school leader's password reset and unlock, daily spend caps. |

## 7. EXPLAINABILITY AND OBSERVABILITY

| | Promise | Where it stands |
|---|---|---|
| ✅ | 'Why this plan?' panel on the plan | In the Yojana screen; the anchor match is stated to the model and explained. |
| ❌ | Evidence card per child for the baseline level | Not built: there is no per-child evidence card for the baseline level. |
| 🟡 | Evidence chain per roll number with confidence | Analyses are stored per roll number with a confidence; see the 'unclear handwriting' point above. |
| ❌ | Level-change evidence trail the teacher approves | Not applicable as built (levels change only through an assessment). |
| 🟡 | A school administrator sets up the school: enrols teachers and students, assigns classes, resets passwords, views reports | The school leader (the head teacher, who teaches too) can list the school's accounts by employee code, reset a teacher's password to a temporary one, unlock an account and confirm the school's consent statement. Nobody registers themselves: the operator makes the accounts today; each teacher enrols her own class by uploading a register and her leader sets her grades. There are no screens yet for adding teachers (one by one or from a CSV file), assigning classes or viewing reports; the block and cluster officers' role is designed in `docs/ROADMAP.md`. |
| ❌ | Admin dashboard: B/P/P across schools, misconception patterns, override rate, vision confidence, latency | Not built. What exists: a school leader (teacher list, password reset and unlock), AI spend limits, a usage job and the nightly job log. |

## 8. DELIVERY AND OTHER PROMISES

| | Promise | Where it stands |
|---|---|---|
| ❌ | A WhatsApp notification each morning with a link to the plan | Not built (needs a WhatsApp Business provider). A cheap stand-in is a 'send today's plan on WhatsApp' button using a deep link. |
| ⏸ | Voice input (Bhashini) | Deferred in the proposal itself, and by design **not for the daily review** (too noisy with several groups at work). Planned for the periodic assessments, in a quiet one-to-one moment, next to observation (`docs/ROADMAP.md`, section 6). |
| ✅ | Hindi-first, minimal text, simple login | Hindi style reviewed by the domain lead; employee code + password, with tap-to-fill role cards for reviewers. |
| ❌ | Cost: $0.03 to $0.08 per complete daily cycle | Measured: about $0.14 for a plan (about $0.28 when the model's first reply has to be redone), plus photo analysis. The proposal estimated less. |
| ❌ | Field test with 2 to 3 real or proxy teachers | Not yet done with real or proxy teachers; an internal test by the team is planned. |
| 🟡 | Modular design so open-weights models can replace parts at scale | Now demonstrated for embeddings (BGE-M3 run on a laptop, MIT licence). Generation and vision still use Claude only. |

## Built beyond the proposal

- **Code verifies the AI's work:** every sum, answer key, number range and worksheet is checked by code; wrong check-for-understanding questions are dropped; unreadable model output is repaired or asked for again.
- **A per-group skill drawer** where the teacher can override each group's skill, and **curated skill bridges** reviewed by the education lead.
- **Check-for-understanding** show-me questions in every lesson, aimed at the last review's mistakes (`docs/CFU.md`).
- **Sign-in and school administration**, rate limits and lockouts, daily **AI spending caps** per teacher, school and overall (`docs/AI_BUDGET.md`), and a nightly demo reset.
- **An open-weights embedding route** for the L2 semantic retrieval: BGE-M3 run offline, vectors loaded from a file, no embedding call at runtime (`docs/SEMANTIC_RETRIEVAL.md`).
- **Automated tests:** backend test suites, front-end tests, and a generation test with the real model (27 of the 101 skills so far; the run over all 101 is still to do, `docs/BATCH_AND_COVERAGE.md`).

## Where the build differs from the proposal

1. **Names** are stored on the server in a separate teacher-only table (never sent to the AI), not only on the teacher's phone.
2. **Storage** is server-side (per-child positions and evidence by roll number), not local-first with IndexedDB.
3. **Level changes** happen only through an assessment; daily evidence changes the plan and raises a 'consider re-assessing' flag.
4. **Cost** is about $0.14 per plan, not $0.03 to $0.08 per daily cycle.
5. **Speed** is about 65 seconds per plan (up to about 2 minutes when a retry is needed), not under 60.
6. **Offline:** reading what was loaded works offline; capture and decisions are not queued for later.
7. **Worksheets** are print-ready HTML printed from the browser, not server-made PDFs.
8. **Consent from each parent:** the school's confirmation is recorded; consent from each parent, and the lawful basis, are not (`docs/PRIVACY.md`).

## Roadmap (not built)

**Roles above the school:** state, district and block roles, bulk school onboarding and aggregate dashboards for officers (a design sketch: `docs/ROADMAP.md`); periodic assessment rounds with a history; screens for the baseline diagnostic; WhatsApp Business notifications; voice assessment for the periodic rounds (not the daily review: `docs/ROADMAP.md`); R2 (second-language) literacy; local-first storage; tap-to-override of a child's level; mapping state assessment data to positions; an officer dashboard; PDF export; more states; open-weights models for high volume; on-demand deep assessment.
