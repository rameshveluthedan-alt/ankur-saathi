# Roadmap: roles, onboarding and integration (a design sketch: only the school leader's part is built)

**Where the build is today.** Two roles exist: *teacher* and *school leader* (the head teacher, who teaches too; stored as `school_admin`). Everyone signs in with an employee code and a password; nobody registers themselves. The leader can list the school's accounts, reset a password, unlock an account and confirm the school's consent statement at her first sign-in. Each teacher enrols her own class by uploading a register. The operator makes the accounts. There is nothing above the school (`docs/STATUS.md`, `docs/AUTH.md`).

**Why this needs design, not patching.** A state rollout is not a set of independent schools. Who enrols a school, who may see which child's data, and who answers to whom are questions about the whole hierarchy. Adding admin screens one at a time would bake in answers we have not chosen. The sketch below mirrors how school education is administered, and keeps one rule: **the closer to the child, the more detail; the higher up, the more aggregate.**

## 1. Who does what (a starting point for discussion)
| Role | Does | Sees | Does not see or do |
|---|---|---|---|
| **State admin** (super admin) | Loads the state's school list (district, block, school code) in bulk; creates district admins; sets state-wide settings (the weekly curriculum plan, language, AI limits) | State-wide aggregates and trends: schools onboarded, teachers active, plans generated, the level mix and how it moves, skills taught, common mistakes by district | Any child's name, photo or answers |
| **Division officer** (only where the state has a division) | Oversees the districts of one division | The division's aggregates, as counts | Names, photos |
| **District admin** | Oversees the schools of one district; creates block coordinators; invites school admins | The district's aggregates and trends, compared block by block; schools that are inactive; children flagged "consider re-assessing" as counts | Names, photos |
| **Block / cluster coordinator** (the academic support role, often called BRC or CRC) | Supports the schools of one block or cluster; reads how each school is doing | Per-school aggregates and trends; read-only | Names, photos; no changes to a school |
| **School leader** (head teacher, who teaches too) | Claims the school; invites and approves teachers; assigns teachers to grades and classes; enrols or syncs the class registers; resets passwords; confirms the school's consent | Her school's reports (level mix per class, plan use, flags) and, if decided (below), the names of her own school's children | Other schools; photos of children's work |
| **Teacher** | Plans, teaches, reviews, records decisions for her own classes | Her own children, by name, and their evidence | Other teachers' classes (unless a school admin assigns her to them) |
| **Observer** (evaluator, auditor) | Read-only access to a defined scope | Aggregates for that scope | Everything else |

## 2. How a state rollout would start (top down)
1. The state admin uploads the school list (the school code from the national school database, name, block, district).
2. Each school and its leader (by employee code) come from the department's lists; the leader signs in with a temporary password, chooses her own and confirms the school's consent statement.
3. The school leader adds teachers (one by one or from a CSV file: the next step, not built; today the operator makes accounts) and assigns them to grades.
4. Class registers are uploaded by the teacher or by the school admin, or synced from the state's student register where one exists.
5. A baseline places the children; daily use starts.

## 3. Data rules that follow from "closer to the child, more detail"
- **Names and photos stay at the teacher (and, if decided, the school).** District, state and block roles see counts, percentages and trends, never a name. This is data minimisation under the DPDP Act, and it removes the strongest objection to an officer dashboard.
- **Every look at sensitive data is recorded** (`auth_events` already records sign-ins and class report exports; it needs a screen).
- **Scope is part of every permission:** a role is always "this role *for this part of the hierarchy*", checked in one place (today `require_auth`), never per screen.
- **Consent is recorded where it is given:** at the school, with a name and a date.

## 4. Open design questions (to settle with the state before building)
1. May the **school admin see children's names**? (The head teacher usually knows them; the teacher is who the data was entrusted to.)
2. Who creates a teacher's account: the school leader alone, or with a block officer's **approval**?
3. Can **one person hold several roles** or schools (a teacher who also covers a second school)?
4. Which **national and state systems** can supply the school list and the student register, and how do we match them without storing more than needed?
5. How do people **sign in** at scale: an employee code with a password (today), a one-time code by SMS or WhatsApp, or the state's own identity system?
6. Should a child's **name live only on the teacher's phone**, as the original proposal said, or in a teacher-only table on the server, as built? Phone-only protects more, but the names are lost when the phone is lost or changed, and a teacher could not sign in on a second phone and see her class.
7. Who in the **state's curriculum cell** reviews and approves the skill ladder and its NIPUN mapping, and by when? (§9)

## 5. What changes in the build
- A hierarchy table (state, district, block, cluster, school) and a **membership table** (person, unit, role) replace the single `teachers.role` column.
- One permission function answers "may this person do this to that unit?"; aggregates are computed in the database, so upper roles never receive child-level rows.
- Bulk school import, invitations and approvals, an access-log screen, and a **per-role test matrix** in the style of `tests/test_auth_flow.py` (every role against every scope, including the refusals).

## 6. Assessment modes: daily and periodic
**Daily review (built): no audio.** A teacher records what she saw in one of three ways, and the screen offers only the one that fits the skill: a photo of the worksheet (the AI reads it), a quick tap of *achieved / partly / not yet* for each child (observation), or the **reading-aloud** form, where she listens to one child for a minute and enters the correct words and the errors. Nothing is recorded: in a class where several groups are at work at once, a recording is too noisy to be clear, so the daily review is by observation.

**Periodic assessments (planned): both modes.** Every few weeks a child is assessed on purpose, in a quiet moment and one to one. There the teacher should be able to choose **observation** (as above) or **voice**: a short recording of the child reading, scored by speech recognition for Hindi, which the teacher confirms or corrects. Voice needs decisions first: parental consent recorded at the school (section 3); audio scored in memory and **not stored**, as photos are today; recognition that is good enough for young children's Hindi (to be measured on real recordings before it is offered); and a recording that still works on a weak connection.

## 7. Phases
| Phase | What | Rough size |
|---|---|---|
| 1 | **School admin console:** a read-only school overview (class sizes, level mix, last active), a school report download, admin creates a teacher account | days |
| 2 | **The hierarchy:** state and district roles, bulk school onboarding, aggregate dashboards | one to two weeks |
| 3 | **Integration and voice:** the national school list, a one-time-code sign-in, importing state assessment results to place children (`docs/LEVELS.md`), voice assessment for the periodic rounds | depends on the state's systems |
| 4 | **Officer views and the second state:** trends, the block coordinator's mentoring view, another state's curriculum plan | follows 2 and 3 |

*Other roadmap items* (periodic assessment rounds with history, baseline screens (section 14), the monitoring dashboard (section 16), WhatsApp notifications (section 13), voice recording for the periodic assessments (section 6), second-language literacy (section 15), PDF export) are listed in `docs/STATUS.md`.

## 8. Next, designed on 27 Oct and not built: the school leader's screens and the officers' reports
Decided with the team after the first tests (the head teacher is the school's administrator; she also teaches and often coaches her teachers):
- **Adding teachers:** a form (employee code, grades) that makes a temporary password, shown once; and a CSV upload with a preview before it is confirmed, the same way the class register is uploaded. There is no bulk upload of schools: a school and its leader are loaded by the department, so each leader looks after one school.
- **Reports, for the leader and for a block or cluster officer (BAC or CRC):** counts only, never a name: teachers active this week, plans made, how many groups were re-taught and how many moved on, children by level, the skills taught most. The leader sees her own school; an officer sees the schools of her block or cluster.
- **The officer's role** is read-only and is stored with the account and its scope (a list of schools), never read from the letters of her employee code.
- **Demonstration data:** about three fictional schools with a few teachers each, so the reports are not empty.

## 9. Content expansion
The product's machinery is built and tested: a 101-skill ladder reviewed by the education lead, a four-corpus L2 content bank (anchors, passages, intervention templates, TLM references), semantic retrieval over pgvector, recorded sample plans as an AI-off fallback. The current corpora are small on purpose: enough to prove the mechanisms and the Hindi, not enough to serve a state at scale. **The next large increase in product quality comes from growing the content, not from new features.** Three content expansions, each sized honestly.

**First, the skill ladder; then the content that hangs off it.** The 101 skills are our own list, written and reviewed by the education lead (Vaishnavi) and mapped to NIPUN Bharat's coded outcomes. The mapping is AI-proposed and not yet confirmed by an educator (`docs/COVERAGE.md`: 32 exact, 7 finer than a NIPUN outcome, 58 related, 4 with no NIPUN counterpart). Mistakes, materials, activities and passages are attached to skills, so a ladder that changes after the content is grown means the content is redone. The order is therefore:
1. **Content experts from the state's curriculum cell review and approve the ladder and confirm the NIPUN mapping.** The aim is a ladder the state has signed off, not only one our team reviewed. A review workbook exists for the mapping (`python scripts/nipun_alignment.py workbook`).
2. **The gaps against NCF-FS (2022) are decided, and the alignment becomes data:** an `ncf_codes` column beside `nipun_codes`. The first candidates are skills for counting backwards and for equal sharing in Balvatika to Grade 2, informal weight and volume, and oral vocabulary and rhymes (`docs/NCF_FS_COMPARISON.md`, proposed by Claude and not yet confirmed).
3. **Newer frameworks and published learning progressions are explored,** and what fits is adopted. No framework is named here on purpose: the aim is to read them first, not to commit to one in advance.
4. **The links between skills are reviewed.** Of the 53 numeracy skills, 9 have a "before" pick in another strand and 9 have no predecessor above Balvatika (`docs/GRAPH_AUDIT.md`); the decisions become the curated skill bridges.

**Where the content is thin today** (counted in the database on 30 October 2026). Of the 101 skills: 74 have no recorded common mistake (the 55 recorded mistakes sit on 27 skills, and 21 of those 55 have no intervention template); 78 have no teaching material (TLM); 52 have no activity written for them (an exact anchor); about 7 have curated question signals; 27 have been run with the real model. For most skills the plan is written by the AI from the skill's name and the three levels alone.

The three content expansions below follow once the ladder is settled.

- **Curated question signal per skill (3+2 worksheet, inline on YojanaScreen).** Three core questions per skill chosen for a specific signal (the known mistake patterns a teacher most needs to see), plus two extras for early finishers. **Today curated for about 7 of 101 skills** (listed in `docs/CURATED_SKILLS.md`); for the rest the AI picks questions at the right level but not for a specific mistake pattern. Expanding to all 101 skills is **about two months of work by the education lead**, reviewing a sample draft per skill the AI produces. Each newly curated skill produces much better teacher-facing signal on the Review and Progress screens.
- **L2 content bank at 3× its current size.** Today: 14 anchor activities, 9 reading passages, 15 intervention templates, 12 TLM references. The semantic retrieval machinery is built but retrieves against a thin bank. Growing each corpus by about 3× (40 anchors, 30 passages across Grades 1 to 3, 50 interventions, 35 TLM references) is **about three months of content work**, reviewed sample by sample, feeding the same retrieval system without a code change.
- **Recorded sample plans for the AI-off fallback.** Today: 6 recorded plans: observation (N0.1.1), photo (N2.2.1, N2.3.2), reading-aloud (L2.5.1), and two Hindi examples (L2.3.1, L2.7.2). When the AI budget runs out or the service is slow, the teacher sees a known-good plan for one of these six skills; for the other 95 she sees a short note and no plan. Growing to the 20 most-taught skills in Mission Ankur is **about one month of work**, reviewed by the education lead.

- **Test and review every plan.** Run all 101 skills through the real model (27 so far, `docs/batch/batch_results.csv`), read the flagged plans with the education lead, fix the skills that come out experimental (the N0.1.1 worksheet is the known case, `docs/KNOWN_ISSUES.md`), and refresh the tested / not-yet-tested labels, which are out of date. About $10 to $30 of AI cost for the 74 skills not yet run (at about $0.14 a plan, more when a plan is redone); the review is the longer part.

These are content jobs, not code jobs. The code that reads them, retrieves against them and falls back on them is already in place. The sizing above assumes one full-time education lead at Vaishnavi's level with support for drafting and quality-checking.

## 10. Next, agreed on 29 Oct and not built: a photo of the paper tick sheet
The paper tick sheet (`/plan/ticks`, built in the lab) lets a teacher record A / PA / NA and reading-aloud scores on paper during You Do; today she copies them into the Review's step 2 by hand. The next step is to photograph the sheet instead:
- **On the sheet:** a small printed code (date, groups, rolls), so the server knows which children to expect and refuses a photo of another day's sheet. The sheet carries roll numbers only, never a name, so the photo carries none.
- **In step 2:** a new way, "📷 टिक शीट की फ़ोटो". The AI reads the ticks and the written numbers, and **nothing is saved directly**: the marks fill the step 2 list as unsaved taps, anything unclear (two boxes ticked, a crossing-out, an unreadable number) is left empty and flagged, and the teacher checks and taps "जमा करें" as today. The teacher's judgment stays the record.
- **Limits to expect:** ticks read reliably; handwritten reading-aloud numbers less so, and need closer checking. It saves most time on large groups; for 8 to 15 children, typing from the sheet takes under a minute.
- **What it needs:** a new AI call with its own prompt (for Ramesh to decide), a server route, the step 2 option and its tests. It can be tested in the lab only against the fake AI (the lab has no API key); a trial with real photos happens on main.

## 11. Next: the plan prompt v2 (drafted and reviewed, not applied)
The plan prompt was reviewed line by line and a second version drafted (`docs/drafts/PROMPT_REVIEW_29OCT.md`, `docs/drafts/PROMPT_DRAFT_V2.md`, `docs/drafts/PROMPT_DRAFT_3N_WORKSHEET.md`): each group's own mistakes for both the show-me questions and the worksheets, plans shaped by the session's length (45, 60 or 90 minutes), worksheets as 3 core problems plus 1 to 3 extras, and the fixed rules moved into a cached system prompt to cut cost. Applying it needs real-model runs for four skill shapes at three lengths, and the education lead's review of the new Hindi: a few days of work after the submission.

**A cheaper model for photo reading.** Haiku 5.5 was meant to be tried for reading worksheet photos and was not run before the freeze. The test is the one already built: the scored photo test (`scripts/eval_vision.py`, `docs/vision/`) run against the current model on the same sheets. Switch only if its answers, verdicts and mistake-naming score as well; otherwise keep Sonnet 5.5. A lower cost per photo is part of the cost goal above.

## 12. Next, not built: telling the teacher when the AI is not sure, and keeping a record
The photo analysis already gives each answer a confidence and shows "check in the notebook" for answers marked unclear. What is missing, and what the first scored run (`docs/vision/`, 40 answers) showed:
- **Show "medium" as "check this answer".** The one misread (715 read as 745) was "medium", and the screen flags only "unclear" and "low". Three of the six "medium" answers were errors; three of the 34 "high" answers were wrong (copying slips the AI did not notice), so confidence helps with legibility but not with every kind of error.
- **A photo-quality note with a reason in plain Hindi** (blurred, cropped, glare, a digit that could be two numbers, fewer problems than the sheet has) and "retake" when it is poor. Three levels with a reason, not a percentage: an AI's own numbers are poorly calibrated and look more exact than they are.
- **A flag log:** each flag and what the teacher did (confirmed, corrected, retook), by roll number only. It is the data to calibrate the levels and gives the override rate the original proposal wanted for an admin view. It needs one small new table.
- **The same idea for the plan, by code first:** the checks that repair or drop things today (sums, number ranges, show-me questions, the stick limit) become a visible, logged summary ("2 show-me questions replaced, 1 worksheet number fixed"). Rules a program cannot check (for example "a writing skill's worksheet tests writing") get a separate reviewer pass by a second, cheaper AI call against a rubric, whose flags go to a review queue for the team and the education lead, not to the teacher. Asking the same model whether it followed its own rules mostly gets "yes".

## 13. Next, not built: WhatsApp as the channel that reaches people
The original proposal had a one-way WhatsApp message each morning with a link to the day's plan. It is not built (`docs/STATUS.md`). The same channel can serve three audiences, so it is designed once.

**The rule that comes first: a message carries a link and counts only.** Never a name, never a roll number, never a file. WhatsApp passes through Meta and a provider, and the app promises that a child's name stays visible only to the teacher. The teacher's class report has names; the mentor summary has roll numbers. Both open in the app, behind sign-in, where each look can be logged (section 3).

| Who | The message | What it needs that does not exist yet |
|---|---|---|
| **Teacher: two nudges that close the daily loop** | In the morning, only if today's plan is not made: "today's plan is waiting". In the afternoon, only if a plan was made but the review is not recorded: "how did each group do? two minutes". Each carries a link. | A phone number per teacher, with consent; a provider; a scheduled job that checks the plan and the review first |
| **Teacher: a weekly progress count** | Counts only ("this week: 14 children moved up in Numeracy") and a link to the full report in the app | Same as above, and a rule for what counts as a move |
| **Block and cluster coordinators (BAC, CRC): a visit brief** | The evening before a visit: "tomorrow's school: summary ready" and a link to that school's read-only mentoring view | Block and cluster roles (section 7, phase 4); **a school visit schedule**; the coordinator's phone number and consent; the teacher knowing who can see her class |

*Why the reminders are about the loop, not only the plan.* Tomorrow's suggestion is built from today's review. A teacher who makes the plan but skips the review gives the next day nothing to adapt to, so the afternoon nudge matters as much as the morning one. Both are sent only when they are useful (no plan yet; taught but not reviewed), and not on non-school days (this needs a holiday calendar).

*Later, an overnight plan.* A plan made overnight from the suggested skill and the last review, for teachers who opt in, so the morning message can say "your plan is ready". It costs about $0.14 a plan (`docs/STATUS.md`), is wasted on holidays and absences, and may miss a review not yet recorded, so it stays opt-in.

**One design for all of it:** a notifications service where events (a reminder, the weekly count, a visit brief) go through templates, recipients (phone, language, consent, opt-out, quiet hours) and a delivery log; a provider adapter, so Meta's own API or a provider such as Gupshup can be swapped without touching the rest; a cap on messages per recipient and per day, like the AI limits; and Hindi templates written early, because Meta approves each template before it can be sent.

**What it costs and what it adds.** The proposal said "zero per-interaction platform cost" for the app, and that holds for the app, but a template message through the WhatsApp Business API has a small fee each and needs a provider. A phone number is new personal data for the teacher and the coordinator, so it needs consent and a line in `docs/PRIVACY.md`.

**Open question, to settle with the state (it belongs with section 4):** who owns the school visit schedule? The department's visit calendar, or the coordinator entering it, or the teacher? Without an owner there is nothing to send the brief from.

**Order:** the teacher's two nudges and the weekly count first (they need only a teacher's phone number); then the visit brief, once block roles and a schedule exist; then the overnight plan, as an opt-in. A cheap stand-in for a first version, with no provider, is a "send today's plan on WhatsApp" button that opens a pre-filled message through a `wa.me` link.

## 14. Next, not built: the baseline screens and the periodic rounds
The original proposal had three assessment moments around the daily loop: a baseline, a full-class round twice a year (mid-year and end of year), and a one-child check on demand. Today (`docs/STATUS.md`, `docs/LEVELS.md`) the backend routes for the baseline diagnostic exist (`/baseline/generate`, `/baseline/submit`), and NIPUN's own B/P/P thresholds are in `compute_placement`. There are **no screens**, and only each child's latest level is kept, so there is no history of rounds. A class starts from the register the teacher uploads, with her own level per subject.

**Build order**
1. **Baseline screens,** with a per-child evidence card ("Beginner in Numeracy. Basis: 2 of 5 place-value items"), for classes whose register has no levels.
2. **A table of rounds,** so each round's levels are kept. It is a schema change, so it comes before the next step.
3. **The periodic round:** the same tool, run on every child through the three channels (section 6), regrouping from fresh evidence and showing the history.
4. **The one-child check on demand.** Today the app only says "consider re-assessing".

Size: about one to two weeks for the first three. The voice option for the periodic round is in section 6.

## 15. Next, not built: more languages
Today the app covers Numeracy and Hindi (R1) literacy, with a Hindi-first screen and an English line under each text. Second-language (R2) literacy was never in the 3-week scope (`docs/STATUS.md`). The code is the small part; **the content is the bottleneck.**
- **R2 literacy needs its own skills, mistakes, passages and activities,** written and reviewed by the education lead. NCF-FS has a Language 2 set of competencies that the ladder does not cover (`docs/NCF_FS_COMPARISON.md`).
- **Another state language** keeps the national skill ladder, but the state's weekly plan is per state, the screen needs a translation layer (today every text has a Hindi and an English form), and the Hindi style rules (polite forms, a gender-neutral teacher, "कौशल" for skill) are specific to Hindi. Each language needs its own rules, written by someone who teaches in it.
- **Order:** the ladder first (section 9); then one more language end to end before any further one.

## 16. Next, not built: the monitoring dashboard
The proposal promised an admin dashboard (usage, level mix, misconception patterns, override rate). The roles table (§1), the officers' reports (§8) and the AI-quality log (§12) each describe a part of it. They are one product: **a monitoring dashboard, with one set of screens filtered by the viewer's place in the hierarchy.** Each level sees the roll-up of the levels below it. What falls as you go up is **identity** (names, photos, answer sheets), **not the depth of analysis**: every level can analyse its own scope with trends, comparisons and drill-down (§3).

**Levels:** state, division (only where the state has one), district, block, cluster, school. The teacher keeps her own screens. Today the `schools` table holds only free-text `block_name` and `district_name`. The hierarchy needs to be a configurable tree (each level has a parent), because states differ in the levels they use.

**What it shows**
- **Usage:** teachers active this week, plans made, reviews recorded, schools not using the app, AI spend against its limit.
- **Assessment:** how many children have a baseline, the result of each periodic round, and how the level mix moved between rounds (this needs the history of rounds, §14).
- **Teaching progress:** plans made against the state's weekly plan (the pace), skills taught and still due, the re-teach rate, skills repeated most (this needs the skill taught to be compared with the week's topic).
- **Progress:** children by level (Beginner, Progressor, Proficient) by subject and grade; groups re-taught versus moved on; the skills taught most; the "consider re-assessing" flags as counts per school.
- **AI quality, for the team and the state's academic cell only:** the override rate, photo-reading confidence and the flag log (§12).

**How it analyses:** trends over time and movement between rounds; comparisons between districts, blocks, clusters and schools; drill-down from state to school; filters by subject, grade and period; export to CSV for the department's own tools.

**Five rules**
1. **Aggregates only above the school: no name, photo or answer sheet.** Depth comes from analysis (trends, comparisons, drill-down), not from identity. The school leader sees her own school; the block coordinator's mentoring view may show roll numbers for a visit (as today's mentor summary does), never names.
2. Small counts are hidden. A school with three Beginners must not show "3" at a higher level: anything under a small threshold (for example 5 children) is folded into the level above.
3. Teachers' usage rolls up by school, and only the school leader sees individual teachers. The proposal's own words: "not surveillance of teachers".
4. Every look is logged (§3), with a screen to read the log.
5. Scope is checked in one place (`require_auth`), never per screen (§3).

**Order:** the school leader's report (§8); then the hierarchy tree and the block, cluster and district roll-ups; then the history of rounds (§14), which unlocks progress over time; then the state view, with the AI-quality panel.
