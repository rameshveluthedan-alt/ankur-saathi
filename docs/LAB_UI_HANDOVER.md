# Lab handover: teacher UI review (27 Oct)

**Branch:** `lab/experiments` (lab worktree, not pushed) · **Base:** `main` at `4e17b06` (Release candidate 3)
**Status:** done in the lab and tested; **not** in `main`. To be reviewed, then packaged for `main` by the release owner.
**Updated (27 Oct, later):** five Progress and Review additions, plus two fixes found on the way. See "Additions after the first handover" below.

## How this was done (lab rules)

The work was done under the lab rules for this release, and they were followed throughout:

- **A separate lab.** Its own worktree (`C:\dev\Ankur-Saathi-lab`), branch (`lab/experiments`), database (`ankur_lab`) and port (8001). Main was only looked at, never changed: the `ankur_saathi` database was read once, read-only, to compare the group suggestions, and main ran on port 8000 for side-by-side comparison.
- **`main` untouched.** It is still at `4e17b06` (Release candidate 3). Nothing was merged, cherry-picked or committed to it.
- **Nothing pushed.** `lab/experiments` has no upstream and no copy on GitHub.
- **No deploys and no `gcloud` commands** from the lab folder. Deploying, the gate and applying packages happen only in `C:\dev\Ankur-Saathi`, on `main`, with the two guard lines before every deploy.
- **The Friday cut-off.** Nothing from the lab goes into `main` after Friday's last deploy. If this work is wanted, the release owner packages it properly; this note is the hand-off for that.
- **Every lab commit followed the same steps:** check `git branch --show-current` prints `lab/experiments`, then `git add -A`, then `python scripts\precommit_check.py` (no secret staged, every time), then a `lab: …` message. The first commits (`dce44f3`, `95b34bb`, `fc21d28`) were made on the go-ahead for the work; from then on each commit was approved before it was made.
- **The demo data was reseeded in the lab only.** `python scripts\demo_progress.py seed --yes --env-file backend\.env` ran on `ankur_lab` to match the deployed demo.

## What and why

A UI review of the PWA for teachers in multi-grade classrooms (Beginner / Progressor / Proficient), on budget phones, often in a hurry during a 90-minute session. Four goals: easy to scan, clean Hindi with English, comfortable tap targets, and groups that can never be mixed up.

## What changed, by goal

### 1. The three groups can never be mixed up
- **One file names the groups** (`pwa/src/tiers.js`). Before, the same list was copied in four screens.
- **Every group badge has a shape as well as a colour:** ● Beginner, ▲ Progressor, ■ Proficient. This works on washed-out screens, in sunlight, for colour-blind teachers and on black-and-white printouts.
- **Group cards, the group panel rows, teach blocks in the rotation schedule and the Review group selectors** take their group's colour. Before, the Review "which group's sheet?" selector used brand green for every group, and choosing the wrong group there sends the wrong worksheet to the AI.
- **Re-teach has its own colour (violet).** Before, it used Beginner orange, so "re-teach" and "Beginner" looked the same. Re-teach blocks no longer look like grey transition blocks (a bug: they got the `transition` style).
- **A child's A / PA / NA result** uses a neutral badge with ✓ / ~ / ✗. Before, it used the group colours, so "NA" looked like "Beginner".

### 2. Hindi with English, and a "Hindi only" setting
- **One bilingual pattern** (`components/Bi.jsx`): Hindi first, then the English translation, smaller and grey. The English is marked `lang="en"`, so screen readers switch voice.
- **"सिर्फ़ हिंदी दिखाएँ (Hindi only)"** on the Profile screen hides every English translation and nothing else. Skill codes, roll numbers and English-only text stay. The setting is kept on the device (`services/language.js`). Pop-ups and messages follow it through `bi()`.
- **Every screen is converted.** A test (`bilingual.test.mjs`) fails if a screen writes "हिंदी (English)" in brackets again, because bracketed English would stay visible with "Hindi only" on.
- **Kept in both languages on purpose:** the school consent statement (the leader confirms its exact wording), and messages the server writes in both languages.
- **Devanagari fix:** labels no longer use letter-spacing, which split the headline bar (शिरोरेखा) between letters.
- **Minimum text size** for converted text is 11 px for English and 12–13 px for Hindi. Before, some text was 8–10 px.
- **"Yesterday" → "last plan".** The group panel said "कल: N2.3.2" even when the last plan was days old (a weekend, or a plan made while testing). It now says "पिछली योजना (24 अक्टू॰): N2.3.2", "पिछली जाँच में…", "पिछली समीक्षा में आपके निर्णय से". The re-teach note is updated the same way, and the docs quote the new wording.

### 3. Tap targets
- **44 px minimum** for buttons, inputs, selects, roll chips, ticks and the bottom nav. The A/PA/NA observation buttons are 44 × 52 px (they were about 28 px tall). The small buttons in the group panel ("↺ सुझाव पर लौटें", "🔄 दोहराएँ") are now normal size.
- **Number pad** for roll numbers and reading scores (`inputMode="numeric"`).
- **The login demo cards look tappable:** pointer and lift on hover, a "भरें ›" cue for phones (which have no hover), and "✓ भर गया" on the chosen card.

### 4. Less clutter
- **Check for understanding** (Yojana screen): the title is "समझ की जाँच" and the block's questions come first. The method paragraph (the same in every block) folds under "▸ कैसे करें?". The title names the purpose, not one technique (show-me).
- **On-screen messages instead of `alert()` pop-ups** (`services/notify.js`, `components/Notices.jsx`). A success goes away after 5 seconds; an error stays until tapped away. The leader's "reset this password?" stays a confirm box.
- **Plan screen:**
  - the coverage card folds to one line
  - the duplicate 👤 button is gone (Profile is in the bottom bar)
  - there's space under the skill list for the fixed Generate bar, which used to cover the last skills
- **Login screen: the demo accounts are arranged by the reviewer's time,** following the rule of thumb in `docs/DEMO_ACCESS.md`. Before, the screen listed accounts but never said which one to pick. Top to bottom:
  1. **"⏱ 5 मिनट: तैयार कहानी देखें"** (5 minutes: see the recorded story): MPT101. It's first and biggest, and it says the class is shared and reset every night.
  2. **"🧪 30 मिनट: खुद आज़माएँ"** (30 minutes: try it yourself): the test teachers MPT102–MPT106 as five chips in one card, with "हर समीक्षक अलग कोड चुनें" (each reviewer picks a different code). Each has their own class of 24, never reset.
  3. **"🏫 स्कूल लीडर: खाते सँभालें"** (School leader: manage the accounts): MPA101.
  4. **"🔑 पासवर्ड बदलकर देखें"** (Try changing a password): MPT199, a small link.

## Additions after the first handover (Progress and Review)

Five small changes from a conversation about the Progress and Review screens, on top of the work above. The Hindi below was revised before building and is **awaiting an expert's review**: decision words reuse the Review's own (आगे बढ़ें / दोहराएँ / पक्का नहीं), "आकलन" for assessment, "जाँच" for evidence, gender-neutral "सकते हैं", "दर्ज" for recorded, "प्रगति टैब" for the Progress tab.

1. **Progress: one "आज के नमूने में" (In today's sample) card** above the child list, following the subject tab. It has a row per group, with its colour edge and shape:
   - today's skill, then "✓ A · ~ PA · ✗ NA" and "N में से M का आकलन"
   - "आपका निर्णय: ⬆ आगे बढ़ें / 🔄 दोहराएँ / ❓ पक्का नहीं" (violet for re-teach), or a grey "आज कोई निर्णय दर्ज नहीं" under the counts
   - two rare lines: the amber "⚠ आपका निर्णय और आज की जाँच मेल नहीं खाते" and the grey "⬆ आगे बढ़ाया; अगला कौशल अभी नहीं है, इसलिए यही कौशल फिर सिखाया जाएगा"
   - a group nobody was assessed in shows only "आज किसी का आकलन नहीं हुआ"
   - The spec suggested three cards; **one card with three rows** was chosen to keep the child list near the top of a phone.
2. **Progress: each child's result today:** one line under the child, "आज N2.3.1 पर: ✓ A", and nothing when nothing was recorded. The level pill doesn't change.
3. **Progress: "🔎 इन बच्चों पर एक नज़र" (Children to look at)** replaces "Consider re-assessing", which promised a re-assessment screen that doesn't exist. It has one honest line, then two short lists: "⬆ अच्छा प्रदर्शन कर रहे हैं — एक छोटा दोबारा आकलन?" and "⬇ कठिनाई में हैं — थोड़ी मदद की ज़रूरत?". The flag logic is unchanged.
4. **Review, Observed:** after Submit, a block above the children list shows "✓ N अवलोकन दर्ज हुए", A/PA/NA, the NA rolls, and a pointer to the Progress tab.
5. **Review, Reading aloud:** after Save, a block above the empty form shows "✓ रोल 12: 42 सही · 3 गलतियाँ · रफ़्तार कक्षा-स्तर पर" (the two numbers as entered; many errors turn the errors amber with ⚠), "इस समूह में N और बच्चे बाकी" (from the server's coverage), and the same pointer.
6. **Reading aloud says pace, not "reader".** The daily label is **रफ़्तार कक्षा-स्तर पर / विकसित हो रही / धीमी** (Pace at grade level / developing / slow). One mapping (`services/pace.js`) turns the server's code into these words, and the same line (`components/FluencyLine.jsx`) is used on the Review block and on the Progress child row. For a speed skill (L1.5.1, L2.5.1, L3.5.1) the Progress row reads "आज L2.5.1 पर: 42 सही · 3 गलतियाँ · रफ़्तार …", with no amber there; other skills keep the A/PA/NA badge. The "reader" words are kept for the periodic round (Phase 3) and are shown nowhere.
   - **About the codes:** the spec says the server returns `grade_level / developing / early_reader`. It actually returns `achieved / partially_achieved / not_achieved` (the same three bands, from the skill's CWPM thresholds). The mapping accepts both forms, so nothing changes on screen if the server's codes are renamed later. The server's thresholds are unchanged.

For both Review blocks, a failed save shows its error in place and no block.

**Backend (no new route, no database change):**
- `/progress/dashboard/{id}?on=YYYY-MM-DD` now also returns `today.numeracy` / `today.r1_literacy` (`has_plan`, and per group `skill_id, a, pa, na, assessed, group_size, decision, conflict, advance_no_next`) and `numeracy_today` / `literacy_today` on each child (`progress_service.get_today`); a reading-aloud result also carries `cwpm` and `errors`.
- **Only that day counts.** A child counts once, by the newest result of the day on the group's skill. "Conflict" and "no next skill" use the Plan panel's own rules.
- **Per subject.** The spec had no subject, but the screen has subject tabs.

**Two fixes found on the way:**
- **"Today" is the phone's local date.** The screens used the UTC date, which in India is still yesterday until 05:30 (`services/today.js`).
- **Reading aloud:**
  - It's now scored on today's skill. The phone never sent the skill, so every score was read against L2.5.1.
  - An unknown roll number is a failed save (HTTP 404). Before, it returned a "success" containing an error.

**Also:** the advance icon is **⬆** everywhere, including the Review buttons, because ▲ is the Progressor shape.

## Follow-up spec: session length, 3 + 2 worksheet, Familiar mode

The second spec repeats items 1–5 above with some different Hindi wording. **The built wording was kept** (it is with the expert). Its new items:

**Item 6, today's time (built).**
- On the Plan screen, just above the skill list: "आज का समय" with three big radio buttons (45 / 60 / 90 मिनट), each a 44 px tap target, and the grey hint "कम समय हो तो कम गतिविधियाँ और छोटी वर्कशीट". The chosen one fills with the brand green.
- The last choice stays on the phone (`localStorage` `session_minutes`, in `services/preferences.js`) and is preselected next time; 90 on first use.
- It is sent only with each plan request: `POST /plan/generate` takes `session_minutes` (45, 60 or 90; anything else is HTTP 422 before any paid call).
- On the server it becomes the plan's teaching time (`available_minutes`), which the prompt already used: the request says "Available teaching time: 45 minutes" and PART C splits 45 minutes into the blocks. Without the field, the teacher's stored time is used, which is 90 unless changed, so an older app is unchanged.
- **Not done here (prompt side):** the few-shot examples per length, and the worksheet and review shape per length (3 + 1 / 3 + 2 / 3 + 3). Two things to know for that work:
  - Today's worksheet rules require 5 (Beginners) or 6 (Progressors) problems before the extras, with the mistake-finding problems among them. The plan checks in `plan_service.py` enforce this, and the photo analysis reads it. A 3 + N shape needs those changed too.
  - When the AI limit is reached, the recorded sample plan is served. It was made for 90 minutes, whatever time was chosen.

**Item 7, the signal panel (built; the server part is separate).**
- Inside each teach block on the plan screen (`YojanaScreen.jsx`), under the one-line script and above the closed talking points, visible without a tap: what the group's children will do. It reads the block's `signal`, as in the spec's contract (`components/SignalPanel.jsx`).
  - `maths_questions`: "तीन मुख्य प्रश्न" and the three core questions, numbered, in the server's order. Under them, in small grey inside the panel: "→ 2 और प्रश्न (जो जल्दी ख़त्म करें उनके लिए)", from `extra_count`; hidden at 0.
  - `writing_prompt`: "लेखन कार्य" and the prompt at 1rem (the questions are 0.875rem: the teacher reads it aloud), cut at two lines with "…".
  - Any other shape (`passage_questions`, `word_list`: later), `null`, an empty payload, or no `signal` at all (plans made before this): no panel; the block is exactly as before.
  - `signal_curated` is not shown: a curated and an uncurated skill look the same (`docs/CURATED_SKILLS.md`).
- The block title now also names the group's skill today: "प्रगतिशील पढ़ाएँ — N2.3.2". The "बाकी समूह" line is unchanged. The worksheet buttons are unchanged; the panel is not a link.

**Item 8, "छोटी स्क्रीन" (Shorter screen) (built).**
- On Profile, under "सिर्फ़ हिंदी दिखाएँ", with the line "योजना की स्क्रीन छोटी हो जाती है; एक टैप पर सब कुछ खुलता है।". Off by default; kept on the phone as `familiar_mode` = `true` / `false` (`services/preferences.js`).
- When on, the plan screen folds each teach block's one-line script under "▸ आज की गतिविधि" (tapping it does not open or close the block) and the anchor card to its title row. The block title, the re-teach note, the signal panel and the "बाकी समूह" line never fold. The talking points and the understanding check are closed as before.
- It is read every time the plan screen is drawn, so a change on Profile shows at once.

**The lab mock for the phone test (lab only).** Until the server sends `signal`, a build made with `VITE_MOCK_SIGNAL=1` fills one in for every teach block that has none, in the same contract (`services/devMockSignal.js`, used by the fetch wrapper in `api.js`): maths plans get three placeholder sums per group with `extra_count: 2`; literacy plans get a writing prompt for the Beginners and no panel for the others. A block that already has a `signal` (the server's, even `shape: null`) is never touched, so it stops mattering once the server work lands. A normal build leaves the mock out entirely (checked: built with and without the setting, the placeholder text is only in the first).

**The printed plan (built).** One A4 page the teacher carries, at `/plan/print` (`screens/PlanPrint.jsx`), opened by "🖨️ प्रिंट" in the plan screen's title row (on a narrow phone the groups' skill codes move to their own line). It prints the plan already on the phone, so it works offline; the browser's Print or "Save as PDF" does the rest, and "🖨️ प्रिंट करें" on the page calls it.
- **Content:** teacher code, class, date, main skill; "योजना समय: लगभग N मिनट" (the blocks added up; the exact value once the plan records `session_minutes`); the anchor's title; for each teach block its group, skill and minutes, a one-line re-teach note (rolls and the first mistake), the script (two lines), the signal panel, the first understanding-check question and "बाकी" (the plan's own `other_groups_hi`, one line); the observation reminders, "फ़ोटो: समीक्षा स्क्रीन पर चुने जाएँगे" and, for a reading-speed skill, "पढ़कर सुनाना"; one worksheet line ("● शुरुआती 3 मुख्य + 2 · …"); the footer.
- **Left out:** I do / We do / You do, the understanding-check method and the other questions, worksheet content, and child names (roll numbers only).
- **The same page for every teacher:** Hindi only, whatever "सिर्फ़ हिंदी" says, and the same with "छोटी स्क्रीन" on or off.
- **The signal panel is the screen's own component** in a `compact` form (title, then the questions on one line; the prompt with its title, two lines), so the server's `signal` reaches both at once.
- **One page:** every line declares an allowance (one line, or two for the script and the panel) that CSS enforces by cutting with "…"; a block takes at most 8 lines and the page at most 36 (`PRINT_LINE_BUDGET`). The real fit on paper is a manual check.

## How to see it

```powershell
# in the lab worktree (C:\dev\Ankur-Saathi-lab), with its own database ankur_lab
backend\venv\Scripts\Activate.ps1
cd pwa; npm run build; cd ..\backend
uvicorn app.production:app --port 8001      # http://localhost:8001 ; main can run on 8000 at the same time
```

Sign in with a demo card. Try:
- Profile → "सिर्फ़ हिंदी दिखाएँ"
- योजना → choose N2.3.2 → open the group panel
- दैनिक योजना → tap a teach block
- समीक्षा

Check at phone width (F12, then Ctrl+Shift+M, 360 px).

For the phone test of the signal panel before the server sends it, build with the lab mock, and build again without it afterwards:

```powershell
cd pwa; $env:VITE_MOCK_SIGNAL='1'; npm run build; Remove-Item Env:VITE_MOCK_SIGNAL; cd ..ackend
```

Then: दैनिक योजना → each teach block shows its panel; Profile → "छोटी स्क्रीन" → the plan screen again.

## Tests

`python scripts\run_tests.py --env-file backend\.env --pwa`, run on the lab database:
- **40 backend suites:** all OK (new: `test_plan_service.py`, 11 checks: 45 / 60 / 90 minutes reach the prompt and PART C, 90 without the field, other values refused; and `test_progress_today.py`, 29 checks: today vs yesterday fixtures, counts once per child, A + PA + NA = assessed, the rare lines, reading aloud scored on its own skill, "still to score" per day, group and skill)
- **22 front-end suites:** all OK, 418 checks

New suites:
- `bilingual.test.mjs` (13 checks)
- `cfu_fold.test.mjs` (6)
- `notices.test.mjs` (6)
- `today.test.mjs` (5)
- `progress_cards.test.mjs` (21)
- `review_confirmation.test.mjs` (21)
- `plan_signal_panel.test.mjs` (15): the real plan screen with fixture plans: 3 questions in order and equal to `core`, the extras count, curated and uncurated identical, the prompt larger than a question and cut at two lines, no panel (and an unchanged block) for null and later shapes, its place in the block, the skill in the title
- `plan_familiar_mode.test.mjs` (16): the real Profile and plan screens in a simulated browser: the toggle's label and place, off by default, flipping it changes the plan screen, the folds closed, and the title, re-teach note and panel never folded
- `plan_print.test.mjs` (21): the printed plan from fixture plans: the three blocks, the same SignalPanel (compact) as the screen, no talking points, no names although the app holds them, the one-line note, the first question only, "बाकी" from the plan, a worst case within 8 lines a block and 36 a page with no text outside an allowance, identical with "छोटी स्क्रीन" on and off
- `dev_mock_signal.test.mjs` (9): the lab mock fills only plans, only with the setting, never over the server's own signal
- `plan_session_length.test.mjs` (13): the real Plan screen in a simulated browser: 90 on first use, a stored 60 preselected, the 44 px targets, and the chosen time in the request

Updated to the new wording or format:
- `plan_screen.dom`: the Generate request now also carries today's time.
- `consent.dom`, `login.dom`, `group_skills`, `reteach_note`, `no_audio`. These now check that both the Hindi and the English are present, instead of requiring "Hindi (English)" in brackets.
- `login.dom` also checks the new login layout: the card order, the five test-teacher chips and their tap targets.
- `demo_accounts` now reads the guide's range row ("MPT102 to MPT106") and checks each of those codes is on the login screen with its password.

Not checked yet: by eye on a real phone.

## The commits

The UI work is the commits after `dce44f3`:

```
95b34bb group colours, readable badges, larger tap targets
fc21d28 group panel names the last plan and its date
925865a group panel: "last plan / last review" everywhere
1d4f8b2 re-teach note: "last review"
a283d29 docs quote the new wording
067d12c one Hindi/English pattern (Bi) and the "Hindi only" setting
bbad4e0 Hindi/English pattern on login, password, register, review, group panel
79365c9 "Hindi only" hides all English
805c1e2 check for understanding: questions first, method folded
c278c22 on-screen messages, coverage card folds, one Profile button
66f5fd9 check for understanding: title "समझ की जाँच", fold "कैसे करें?"
d1da622 login demo cards look tappable
8dcea26 this handover note
49aef27 handover note: the lab rules and how they were followed
9c2361e login demo accounts arranged by the reviewer's time
64b6c4e handover note: login layout, file count
5748c20 "today" is the phone's local date, not UTC
98b9c24 dashboard carries today per subject; reading aloud on its own skill, unknown roll 404
6974eb8 Progress: Today card, each child's result, "इन बच्चों पर एक नज़र"; ⬆ everywhere
1d8ad37 Review: Observed and Reading-aloud blocks after a save
0c3fe08 handover note: the additions
98c72e6 reading aloud shows pace, not "reader" (Review block and Progress row)
```

Files: 51. They're `pwa/src` (31), `pwa/tests` (12), `docs/` (3: `GROUP_SKILLS.md`, `DEMO_ACCESS.md` and this note) and the backend (5: `progress_service.py`, `review_service.py`, `routes.py`, `schemas.py`, `tests/test_progress_today.py`). **No database, migration or prompt changes**, and no new route.

### ⚠ Depends on lab-only work

`dce44f3` is a separate WIP snapshot: employee-code sign-in, the consent gate and the login rework. It is **lab-only and still under review**, and it is not part of this handover. The UI commits build on it, and **8 files overlap**:

- `pwa/src/App.jsx`
- `pwa/src/screens/AccountScreen.jsx`, `ChangePinScreen.jsx`, `ConsentGate.jsx` (new in the WIP), `LoginScreen.jsx`
- `pwa/tests/consent.dom.test.mjs`, `login.dom.test.mjs`
- `docs/DEMO_ACCESS.md`

So the UI commits **cannot be applied to `main` on their own as they are.** The packaging choices are:
- **(a)** take the sign-in work first, then the UI
- **(b)** take the UI without those 8 files' sign-in parts, and redo the small UI edits in them by hand. Mostly that means wrapping labels in `<Bi>` and the tappable demo cards.

## Open decisions for the team

1. **"English only":**
   - The labels alone would take about 2–3 hours: mark the Hindi, and write English for 60–100 bits that have none.
   - The lesson content is generated in Hindi only, so English lessons would mean prompt and backend changes and more AI cost.
   - Decided for now: the default (Hindi with English) is enough.
2. **The Devanagari font is never loaded.** `index.css` names Noto Sans Devanagari, but nothing loads it. Android usually has it built in; Windows and older devices fall back to other fonts. Self-host a small `.woff2`, or drop the name.
3. **The re-teach block** still says "Show-me" in two English places: the pace line and one tip. These are deliberately unchanged.
4. **Not converted:** the printable worksheet template (`backend/app/templates/worksheet.html`) was not reviewed.
5. **Reading aloud, decided:** the daily label is pace (see addition 6). Two points remain for later:
   - **Speed only.** The bands come from words per minute alone; the skills' accuracy rule (90–95%) isn't used, and the error count is shown but not scored.
   - **Two reading skills aren't about speed** (L2.5.2 pauses, L3.5.2 expression). They keep the A/PA/NA line, but the reading-aloud form still scores them against a default speed. They would be better recorded the Observed way.
6. **The Hindi of the additions** is with an expert for review.
7. `docs/LEVELS.md` and `docs/STATUS.md` still call the underlying flag the "consider re-assessing" flag. That's the design concept's name, not screen text; rename it if the team wants it to match.
