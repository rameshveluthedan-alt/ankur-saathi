# Evaluator guide: Ankur Saathi (अंकुर साथी)

**Live app:** https://ankur-saathi-434145152242.asia-south1.run.app (open it on a phone, or a desktop browser narrowed to phone width; it installs like an app: "Add to Home Screen")
**Source code and README:** https://github.com/rameshveluthedan-alt/ankur-saathi · **Video (3 minutes):** https://youtu.be/fSvoh9tDXY4

**Updated for the finals (15 Nov 2026).** The app was revised from the Phase 2 evaluators' feedback: the screens follow the teacher's day, each group has one colour, levels are recorded during the lesson, and worksheets and reports open inside the app. What changed is listed in [docs/RELEASE_NOTES_15NOV.md](RELEASE_NOTES_15NOV.md).

## Sign-in (every role; the demo holds fictional data only, so the passwords are public)
Everyone signs in with a 6-character **employee code** and a password. On the login screen, tap a card and the code and password fill in. There is no registration and no join code: accounts are made by the school leader.

| Role | Code | Password | Use it to |
|---|---|---|---|
| **Teacher** (the main one) | MPT101 | 4826 | See the whole daily cycle. A shared account with a 30-child multi-grade class and a few days of fictional history. **One person at a time**: a plan you generate replaces today's plan for everyone |
| **Teacher** (your own copy) | MPT102 to MPT106 | 4826 | The same, with a class of your own, so you cannot disturb another evaluator |
| **School leader** (the head teacher, who teaches too) | MPA101 | 7351 | Profile: the school's accounts by employee code, resetting a password, unlocking an account |
| **Practice account** | MPT199 | 3917 | Try changing a password, or having the school leader reset it. Every other demo password is fixed on purpose |

## The four tabs: the teacher's cycle
**योजना बनाएँ (Plan) → पढ़ाएँ (Teach) → आकलन (Assess) → कक्षा प्रगति (Progress).** The **हिं / EN** switch at the top of every screen shows the labels in Hindi only or in Hindi with English. Each group has one colour and shape everywhere: ● शुरुआती (Beginner), ▲ प्रगतिशील (Progressor), ■ दक्ष (Proficient).

- **योजना बनाएँ (Plan):** the app suggests today's skill first (one tap); the full skill list is below it. The group panel shows each group's skill and why.
- **पढ़ाएँ: आज की योजना (Teach: today's plan)**, in the order of the teacher's day:
  - **कक्षा से पहले (Before class):** the group table, the things to prepare, and how to assess today.
  - **पढ़ाते समय (While teaching):** one tab per part of the session (the anchor activity, then each group). Inside a group's tab: **मैं करूँ · हम करें · तुम करो (I do · We do · You do)**, the "show me" questions, and the group's worksheet. The teacher's lines read as short instructions ("बोर्ड पर लिखें", "बच्चों से पूछें").
  - **पढ़ाने के बाद (After teaching):** the button to Assess, and "यह योजना क्यों? (Why this plan?)".
- **आकलन (Assess):** two steps, below.
- **कक्षा प्रगति (Progress):** each child's progress, and the reports.

## How much time do you have?
- **5 minutes to see the daily cycle:** sign in as the demo teacher (**MPT101**, password 4826) and follow "Five sample inputs" below, starting with input 1. Everything you need is pre-recorded on this class: yesterday's work, the re-teach suggestion, a worked example. One person at a time: if two of you are on MPT101, the newer plan replaces the older one.
- **Two sessions to build the story yourself:** sign in as a **test teacher** (**MPT102 to MPT106**, 4826), use one each. Follow "A two-day evaluation" below. The nightly reset does not touch these classes, so what you record stays until you change it.

## Five sample inputs that show it at its best
1. **The daily cycle, with a re-teach (about 3 minutes).** Sign in as MPT101 (password 4826). On **योजना बनाएँ (Plan)**, choose the skill **N2.3.2 (adds two 2-digit numbers with regrouping)**. The group panel shows the three groups: the Beginners moved on to this skill, the Progressors are marked **re-teach** because several children made a mistake yesterday, and the Proficients continue with N3.3.1. Press **📋 आज की योजना बनाएँ (Create today's plan)**. *It takes 1 to 2.5 minutes: leave the screen open.* Then, on **पढ़ाएँ (Teach)**, open the Progressors' tab: the re-teach, the "show me" questions, and the **worksheet**, which opens inside the app with its own **🖨️ प्रिंट (Print)** button. Where there is no printer, the board line under "तुम करो" gives the problems to copy.
2. **A curated skill bridge.** On **योजना बनाएँ** choose **N3.3.1 (adds 3-digit numbers with regrouping)**. The panel sends the Beginners back to **N2.3.2** and the Proficients on to **N3.3.6** (word problems), chosen by the education lead rather than by a formula. Change any group's skill with its drop-down.
3. **Hindi plans.** Choose **L2.3.1 (reads words with conjunct consonants)** and make today's plan: a reading plan in Hindi. Then choose **L2.7.2 (writes 3-5 connected sentences)**: a writing plan whose worksheet is marked from a photo (input 5).
4. **Recording levels during the lesson, with no AI.** Choose **N0.1.1 (sorts objects by colour, shape or size)** and make today's plan. On **पढ़ाएँ**, open a group's tab and, inside **तुम करो (You do)**, tap **✓ देखते हुए A / PA / NA दर्ज करें (Mark A / PA / NA)**. The task, the materials and "क्या देखें" (what A, PA and NA look like) are on the same page. Tap A, PA or NA for each child shown and press **अवलोकन जमा करें (Submit)**. The back button returns to the same tab.
5. **Photo marking.** Make a plan for **N2.3.2** or **L2.7.2**, then photograph a worksheet filled in by hand (from **तुम करो**: **📸 वर्कशीट की फ़ोटो लें**, or later on **आकलन**). There are no ready-made photos to download, on purpose: the AI marks a photo against the answer key of **your own** plan's worksheet. The steps are in "Test the photo marking with a sheet of your own" below.

## Assess: record today's performance, then one decision
The teacher can record **during the lesson** (inside each group's "तुम करो") or **after teaching** on **आकलन (Assess)**. Assess has two steps:

- **1/2 · आज का प्रदर्शन दर्ज करें (Record today's performance).** One card per group, each showing the way that fits its skill: **✓ देखकर जाँच (Observation)**, **📸 वर्कशीट जाँच (Worksheet check)** or **⏱️ पठन जाँच (Reading check)**. "ⓘ यही तरीका क्यों? (Why this way?)" says why. What was recorded during the lesson is already there; what is left can be entered from the paper **टिक शीट (tick sheet)** or done now.
- **2/2 · अंतिम निर्णय: अगली कक्षा में क्या पढ़ाएँ? (Next class: what to teach?)** For each group: **⬆ आगे बढ़ें (Move on)**, **🔄 दोहराएँ (Teach again)** or **❓ पक्का नहीं (Not sure)**, with today's evidence in front of the teacher. **निर्णय दर्ज करें (Save decisions).** The next plan is suggested from these decisions.

**The teacher decides; the AI only informs.** For observation and reading, the teacher records each child's level herself: no AI is involved. For a worksheet, the AI marks the photos and suggests Move on or Teach again; the decision for the next class is always the teacher's, in step 2/2. The letters are explained on every screen that shows them: **A** = did it without help · **PA** = with help, or partly correct · **NA** = not yet.

Three ways to record, in detail:
- **✓ देखकर जाँच / Observation: no photo, no AI, no network call beyond saving.** For hands-on and spoken skills (for example N0.1.1). The teacher watches the children named in the app during "तुम करो" and taps A, PA or NA for each. A child already recorded today shows what was recorded, and a change is shown as "PA → A". The materials are the kit's TLM or everyday objects (pebbles, leaves, buttons), because most schools cannot print; a back-up worksheet can be drawn on the board.
- **📸 वर्कशीट जाँच / Worksheet check: the AI reads a worksheet photo and marks it.** For written skills (for example N2.3.2, L2.7.2). The app names the children whose sheets to photograph. The result shows each answer ticked or crossed, the mistakes found (by name, for example "वाक्य अलग-अलग लिखना, जोड़ने वाले शब्द नहीं"), and each child's level. For a writing task the checklist on the sheet decides the level. A photo taken under the wrong group is refused, with the group it belongs to.
- **⏱️ पठन जाँच / Reading check: a reading-fluency count, no audio.** For reading-aloud skills (for example L2.5.1). The app picks **up to 4 children a day**, rotating, so a group is fully heard within a few days. The teacher listens, types the **सही शब्द/मिनट (correct words per minute)** and the mistakes, and presses **पठन दर्ज करें (Save reading score)**. **No audio is recorded**: with several groups at work a recording would be too noisy.

## Test the photo marking with a sheet of your own (about 5 minutes, no printer needed)
The AI marks a photo against the answer key of the plan you generated, so a photo made elsewhere would be marked against the wrong questions. Make the photo from your own plan:
1. **Sign in as a test teacher (MPT102 to MPT106)**, not MPT101: on the shared MPT101 another evaluator's new plan would replace yours. On **योजना बनाएँ** choose **N2.3.2** and make today's plan.
2. On **पढ़ाएँ**, open the **Progressors'** tab and their worksheet. **Print it** and fill it in by hand, or, with no printer, copy the numbered problems into a notebook page. Write **a roll number the app names** at the top (the roll number only: no name).
3. **Fill it in like a child**, with some mistakes on purpose. For 34 + 28: the right answer **62**; the carry forgotten, **52**; the whole ones sum written, **512**; the wrong digit carried, **72**; one number copied differently from the sheet (say 24 + 28); and one left blank. A crooked or dim photo is itself a fair test.
4. In the Progressors' **तुम करो**, tap **📸 वर्कशीट की फ़ोटो लें** (or on **आकलन**, choose the Progressors' card), take or choose the photo, and press **🔍 फ़ोटो का विश्लेषण करें (Analyse)**.
5. **What to expect.** The roll number and each answer are read, and each sum is ticked or crossed against the key. The numbers are read almost perfectly, but **the mistake is named roughly** (it can name two carry mistakes together, and may miss "wrong digit carried"), and a copied-differently problem may be missed. The teacher then makes the decision for the next class.
6. If the day's **AI limit** has been reached, the app says so in plain words (a photo cannot be faked with a recorded plan); try again the next day.

## Reports and printouts
All open **inside the app**, on a phone or a desktop.
- **📋 कक्षा सारांश / Class summary** (कक्षा प्रगति → **📄 रिपोर्ट**): the teacher's own page for planning next week. The last 4 weeks, per subject: how the groups stand; **पढ़ाए गए कौशल** (the skills taught, with the decisions: ⬆ आगे बढ़ें · 🔄 दोहराएँ · ❓ पक्का नहीं); **हर बच्चा कहाँ है** (a table of every child's newest A / PA / NA on each skill taught, "–" where not checked yet); the children to look at; and the most common mistakes with a matching activity. Printable. Each opening is logged, because the page shows names.
- **💬 मेंटर रिपोर्ट / Mentor report** (कक्षा प्रगति → **📄 रिपोर्ट**): a one-page report for a visiting block or cluster officer, **roll numbers only, never a name**. Talking points (one strength, up to two things to work on, a question for the teacher), how the teacher works (plans made, assessments completed), **कौशल के नतीजे** (A / PA / NA counts per skill) and the common mistakes. The points come from fixed rules printed on the page, **not from AI**. On a class with few days of use it shows little.
- **Printed plan and tick sheet** (on **पढ़ाएँ**): **🖨️ प्रिंट** offers **📄 सारांश (एक पेज)** (a one-page summary to carry) or **पूरी योजना** (the full plan). **टिक शीट** is a paper table (roll number, A / PA / NA, or the words read correctly) to fill in during the lesson.
- **Data tables (CSV)** (कक्षा प्रगति → **📄 रिपोर्ट**): the class report with names, and the officer data with roll numbers only. They open as a table in the app, with a download button. Columns are readable: report date, grade, group, and each subject's latest skill checked with its result (A / PA / NA) and date.

## A two-day evaluation (optional, about 15 minutes across two sessions)
Ankur Saathi's point is that **the next class builds on the last one**. On MPT101 this is pre-recorded. To see it built from your own actions, use a test teacher (MPT102 to MPT106), one each: if two of you share one, Day 1's state is whoever acted last.

- **Day 1 (about 10 minutes).** Sign in with your test teacher. On **योजना बनाएँ**, pick a skill no one else is using: **N2.2.1** for MPT102, **N2.2.2** for MPT103, **N2.2.4** for MPT104, **L2.5.1** for MPT105, **L2.3.2** for MPT106. Make today's plan. On **पढ़ाएँ**, open a group's tab and look through its I do / We do / You do and worksheet. Record a few children, either inside **तुम करो** or on **आकलन** step 1/2 (observation is fastest). Then, on **आकलन** step 2/2, choose Move on / Teach again / Not sure for each group and press **निर्णय दर्ज करें**.
- **Day 2 (about 5 minutes), the next working day between 02:00 India time and midnight.** Sign in with the same test teacher. On **योजना बनाएँ**, the **"yesterday" line and the suggested skill come from your own Day 1** (for instance a re-teach for the group you chose "Teach again" for). Accept the suggestion, make today's plan, and you have seen the full cycle that makes this product different.

## What to expect
- **A plan is written by an AI model, so two runs differ.** Code checks every sum, answer key and number range afterwards, drops "show me" questions that are wrong or guessable, and rewrites the teacher's lines as instructions where needed. The Plan screen says so in one line: plans are a **🧪 pilot**, and the team has reviewed the plans of six skills.
- **The decision in step 2/2 can be saved without any evidence, by design.** The teacher decides and the evidence only informs her: a group nobody has checked shows "अभी किसी का आकलन नहीं" (nobody assessed yet), the app makes no suggestion for it, and her decision still shapes the next plan. Some children are absent, a phone may have no signal (photos need the internet), and some skills have no photo at all.
- **Each skill on योजना बनाएँ shows how it is checked**, with the same icons as Assess: **📸 फ़ोटो** (a worksheet photo), **✓ देखकर** (observation), **⏱️ पढ़कर** (reading aloud).
- **The state weekly plan is a representative one.** The week's topic, and the "State plan note" in "यह योजना क्यों?", come from a Madhya Pradesh plan we drafted for Grades 1 to 3, not from the SCERT's own calendar, which has not been loaded (`docs/KNOWN_ISSUES.md`).
- **Limits protect the credits, and what you see when one is reached.** Every AI call is capped per teacher (roughly 10 to 20 plans a day, photo reads included), per school, for the shared MPT101 account (higher, because all evaluators share it) and for the whole app, each per India day; the credit itself ends on 30 November. When a limit is reached, or the team has switched the AI off:
  - **For six skills** (N0.1.1, N2.2.1, N2.3.2, L2.3.1, L2.5.1, L2.7.2) you still get a plan: a recorded sample plan for the same skill, reviewed by our education lead and put through the same checks, under a banner "📄 नमूना योजना" (Sample plan). It is always the 90-minute version, whatever time you picked.
  - **For any other skill** the app says in Hindi and English which limit was reached, and lists the skills that have a sample plan. A daily limit resets the next day.
  - **A worksheet photo** cannot be faked: the analysis says the limit was reached.
  - **Observation and reading aloud** need no AI and always work.

  You cannot force a limit from the app. If you meet one, that is the expected behaviour, not a fault.
- **MPT101 is a single, shared class.** If more than one of you is on MPT101 at the same time, the plan and the decisions you see are the last ones saved. MPT102 to MPT106 are separate classes, one per evaluator, that stay yours between sessions.
- **The demo resets every night at 01:30 India time** (MPT101's history is restored to the recorded N2.3.2 story, ending the day before; the test teachers MPT102 to MPT106 are not touched; accounts keep their passwords).
- **Slow or no network:** the whole first load is about 120 KB (compressed). Make a plan, then switch on airplane mode (or DevTools → Network → Offline) and reload. The app opens, a notice says you are offline, today's plan and its worksheets still open and print, and making a plan and sending photos are switched off with the reason. Recording levels and decisions needs the internet (nothing is queued yet). Details: [docs/OFFLINE.md](OFFLINE.md). Last checked on the Phase 2 version (`rc7`) on 31 October 2026.
- **What is not built** is listed openly in [docs/STATUS.md](STATUS.md); the plan for roles (state, district, school) is in [docs/ROADMAP.md](ROADMAP.md).

## Frozen version (Phase 2) and the finals version (live now)
| | |
|---|---|
| **Finals version (live now)** | the `main` branch on GitHub, deployed on 15 November 2026; what changed: [docs/RELEASE_NOTES_15NOV.md](RELEASE_NOTES_15NOV.md) |
| Phase 2 version (evaluated until 10 November) | Git tag `rc7`, commit `4ad1dce`, Cloud Run revision `ankur-saathi-00013-bdr`, frozen on 30 October 2026 |

Where the AI is used, every external service and model, and where keys are needed: the README, section "How AI is used".
