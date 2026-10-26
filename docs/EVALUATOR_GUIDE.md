# Evaluator guide: Ankur Saathi (अंकुर साथी)

**Live app:** https://ankur-saathi-434145152242.asia-south1.run.app (open it on a phone, or a desktop browser narrowed to phone width; it installs like an app: "Add to Home Screen")
**Source code and README:** https://github.com/rameshveluthedan-alt/ankur-saathi · **Video (3 minutes):** [FILL ON FREEZE: YouTube link]

## Sign-in (every role; the demo holds fictional data only, so the PINs are public)
| Role | Phone | PIN | Use it to |
|---|---|---|---|
| **Teacher** (the main one) | 9876543210 | 4826 | See the whole daily loop. A shared account with a 30-child multi-grade class and a few days of fictional history. **One person at a time**: a plan you generate replaces today's plan for everyone |
| **Teacher** (your own copy) | 9000000101 to 9000000105 | 4826 | The same, with a class of your own, so you cannot disturb another evaluator |
| **School admin** | 9876500000 | 7351 | Profile: the school's join code, its accounts, resetting a PIN |
| **School admin** (test school) | 9000000100 | 7351 | The same for the school the five test teachers belong to |
| **"Change PIN" account** | 9000000199 | 3917 | Try changing a PIN, or having the admin reset it. Every other demo PIN is fixed on purpose |
| *New teacher* | any new number | your own | "Register": join the demo school with the join code **DEMO26**, or leave the join code empty to create a new school and become its admin (you confirm a short consent statement shown on the form) |

## Five sample inputs that show it at its best
1. **The daily loop, with a re-teach (about 3 minutes).** Sign in as 9876543210. On **Plan**, choose the skill **N2.3.2 (adds two 2-digit numbers with regrouping)**. The group panel shows the three groups: the Beginners moved on to this skill, the Progressors are marked **re-teach** because 6 of 14 children made a mistake yesterday, and the Proficients continue with N3.3.1. Press **Generate**. *It takes 1 to 2.5 minutes: leave the screen open.* Then open **Yojana** (the plan): read the Progressors' re-teach block, the rotation with transition scripts and the "show me" questions. At the bottom open the Progressors' **worksheet** and use the browser's print preview: the roll-number answer grid, the carry tab above the tens column, and the one-line version to copy on the board where there is no printer.
2. **A curated skill bridge.** On Plan choose **N3.3.1 (adds 3-digit numbers with regrouping)**. The panel sends the Beginners back to **N2.3.2** and the Proficients on to **N3.3.6** (word problems), chosen by the education lead rather than by a formula. Change any group's skill with its drop-down.
3. **Hindi plans.** Choose **L2.3.1 (reads words with conjunct consonants)** and Generate: a reading plan in Hindi. Then choose **L2.7.2 (writes 3-5 connected sentences)**: a writing plan whose worksheet is reviewed from a photo (input 5).
4. **Recording a review with no photo and no AI.** The Review screen offers only the way of recording that fits the skill.
   - **By observation:** choose **N0.1.1 (sorts objects by colour, shape or size)**, Generate, open **Review**, record a decision for each group, then **Observation**: for each child tap **A** (achieved), **PA** (partly) or **NA** (not yet), and save.
   - **Reading aloud:** choose **L2.5.1 (reads grade-level passages at 40 words a minute)**, Generate, open **Review**, then **Reading aloud**: pick a roll number, type the correct words per minute and the errors, and save: the app says where that child stands. **No audio is recorded**: with several groups at work a recording would be too noisy to be clear, so the daily review is by observation and the teacher times the reading herself. Voice is planned for the periodic assessments (`docs/ROADMAP.md`).
5. **Photo review.** On **Review**, record "Advance" or "Re-teach" for a group first (the AI never goes first), then photograph or upload a worksheet. [FILL ON FREEZE: link to 2 or 3 fictional sample worksheet photos to upload]

## What to expect
- **A plan is written by an AI model, so two runs differ.** Code checks every sum, answer key and number range afterwards, and drops "show me" questions that are wrong or guessable.
- **Limits protect the credits.** If a daily limit is reached, these skills still show a recorded sample plan (labelled "sample plan"): **N0.1.1, N2.2.1, N2.3.2, L2.3.1, L2.5.1, L2.7.2**; other skills say the limit was reached and that it resets the next day. Observation and reading aloud (input 4) need no AI at all.
- **The demo resets every night at 01:30 India time** (the shared teacher's history is restored; accounts keep their PINs).
- **Slow or no network:** the whole first load is under 90 KB. To try it: generate a plan (step 1 above), switch on airplane mode (or DevTools → Network → Offline) and reload. The app opens, a notice says you are offline, today's plan and its worksheets still open and print, and Generate and photo sending are switched off with the reason. Recording decisions, observations and reading scores need the internet (nothing is queued yet). Details: [docs/OFFLINE.md](OFFLINE.md). [FILL ON FREEZE: repeat this on the frozen version and confirm]
- **What is not built** is listed openly in [docs/STATUS.md](STATUS.md); the plan for roles (state, district, school) is in [docs/ROADMAP.md](ROADMAP.md).

## Frozen version (what you are evaluating)
| | |
|---|---|
| Git commit | [FILL ON FREEZE: commit hash] |
| Git tag | [FILL ON FREEZE: tag, for example `submission-stage2`] |
| Cloud Run revision | [FILL ON FREEZE: revision name] |
| Frozen on | [FILL ON FREEZE: date and time, India time] |

Where the AI is used, every external service and model, and where keys are needed: the README, section "How AI is used". Questions: [FILL ON FREEZE: a contact].
