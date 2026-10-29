# Lab handover: teacher UI review (27–28 Oct)

**Branch:** `lab/experiments` (lab worktree, not pushed) · **Base:** `main` at `4e17b06` (Release candidate 3)
**Status:** done in the lab and tested; **not** in `main`. To be reviewed, then packaged for `main` by the release owner.
**Updated (27 Oct, later):** five Progress and Review additions, plus two fixes found on the way. See "Additions after the first handover" below.
**Updated (28 Oct):** the follow-up spec: today's time (45 / 60 / 90), the signal panel, "छोटी स्क्रीन", the printed plan and the time chip, with a lab-only mock for the phone test. See "Follow-up spec" below. Items 1–3 (Progress) were checked on a phone on 28 Oct; the rest is for the phone pass on Thursday.
**Updated (29 Oct):** a UI review against the evaluation criteria (user at the centre; how the solution comes together) and a navigation review: see "UI review and navigation (29 Oct)" below.
**Updated (29 Oct, later):** the Review reworked from the team's click-through: three steps (first judgment, the children's work, a final decision with today's evidence), recorded choices kept visible, how to do each way of checking, the text to read aloud. See "The Review, reworked (29 Oct, later)" below.

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
  - When the AI limit is reached, the recorded sample plan is served. It was made for 90 minutes, whatever time was chosen; the time chip (below) says so honestly ("90 मिनट").

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

**The time chip (built).** "⏱ 60 मिनट" in the plan screen's title, next to "दैनिक योजना" (`services/planMinutes.js`, shared with the printed plan's "योजना समय").
- **The server records the plan's length** on every new plan, as `plan.session_minutes` (`plan_service.py`, one line): the time the teacher chose (or her stored time, 90, when none was sent); a recorded sample plan keeps the length it was made for (90 for the six today: `SAMPLE_PLAN_MINUTES`, unless a sample plan records its own). The AI's own `total_minutes` is never read: it is a hint the model wrote, not a fact the system recorded.
- **A plan made before this** has no `session_minutes`: the chip adds up its blocks' minutes, and within 5 minutes of 45, 60 or 90 shows the preset ("87" shows "90"); further off, the exact sum. The printed plan says "लगभग" in that case.

**The printed plan (built).** One A4 page the teacher carries, at `/plan/print` (`screens/PlanPrint.jsx`), opened by "🖨️ प्रिंट" in the plan screen's title row (on a narrow phone the groups' skill codes move to their own line). It prints the plan already on the phone, so it works offline; the browser's Print or "Save as PDF" does the rest, and "🖨️ प्रिंट करें" on the page calls it.
- **Content:** teacher code, class, date, main skill; "योजना समय: N मिनट" (the length the plan records, as on the time chip; "लगभग" and the blocks added up only for a plan made before that); the anchor's title; for each teach block its group, skill and minutes, a one-line re-teach note (rolls and the first mistake), the script (two lines), the signal panel, the first understanding-check question and "बाकी" (the plan's own `other_groups_hi`, one line); the observation reminders, "फ़ोटो: समीक्षा स्क्रीन पर चुने जाएँगे" and, for a reading-speed skill, "पढ़कर सुनाना"; one worksheet line ("● शुरुआती 3 मुख्य + 2 · …"); the footer.
- **Left out:** I do / We do / You do, the understanding-check method and the other questions, worksheet content, and child names (roll numbers only).
- **The same page for every teacher:** Hindi only, whatever "सिर्फ़ हिंदी" says, and the same with "छोटी स्क्रीन" on or off.
- **The signal panel is the screen's own component** in a `compact` form (title, then the questions on one line; the prompt with its title, two lines), so the server's `signal` reaches both at once.
- **One page:** every line declares an allowance (one line, or two for the script and the panel) that CSS enforces by cutting with "…"; a block takes at most 8 lines and the page at most 36 (`PRINT_LINE_BUDGET`; the worst-case fixture comes to 32). The real fit on paper is a manual check: 11 pt now, 10.5 pt if it is tight.

**Held: item 9, the "आज क्या अलग है" line** at the top of the plan screen. Not built, as the spec recommends; decide after the phone pass.

**Server work still to come (owner: Ramesh, planned for Wednesday)** — the screen side above is built against its contract and needs no change when it lands:
- `signal` on each teach block (`maths_questions` / `writing_prompt`; `null` for the other shapes this round), with `signal_curated` read from `docs/CURATED_SKILLS.md`.
- The worksheet as 3 core + 1 / 2 / 3 extras by session length, the plan checks in `plan_service.py` changed from "first 5 or 6 required" to "the 3 core are the signal", and the photo analysis reading the 3 core problems.
- The prompt: few-shot examples per length (45 / 60 / 90) and per shape (maths, writing), with the Hindi of the six reviewed.
- **Already in the lab, to build on rather than redo:** `session_minutes` accepted on `/plan/generate` (`schemas.py`, `routes.py`), passed to the prompt as the teaching time and recorded on the stored plan (`plan_service.py`: `SAMPLE_PLAN_MINUTES` and the line after `plan_json["served_from"]`), and `backend/tests/test_plan_service.py`.

## Item 12: today's plan is not replaced by accident

Before, the Plan screen always invited a Generate: a plan already made for today was replaced silently (and another AI call spent), leaving any results recorded against it without their plan.

**Now, when the Plan screen opens it asks the server for today's plan in the active subject** (`GET /plan/{teacher}/{date}/{subject}`, the call the plan screen already used):
- **No plan (404):** the open picker and Generate, as before.
- **A plan exists:** a status card instead of the picker: the subject, "कौशल: N2.3.2 🔒", "समय: 90 मिनट 🔒", "✓ आज की योजना बन चुकी है", "योजना खोलें →" and "🪄 नई योजना बनाएँ". No skill list, no time buttons, no group panel, and none of the plan itself (that stays on दैनिक योजना).
- **"🪄 नई योजना बनाएँ" asks first** (`components/ReplacePlanDialog.jsx`). With nothing recorded: "आज की योजना पहले से बनी है। नई योजना बनाने पर पुरानी हट जाएगी। क्या आप इसे बदलना चाहते हैं?". With results recorded it names them: "आप इस योजना के लिए इन समूहों पर कुछ बच्चों का रिकॉर्ड पहले ही दर्ज कर चुके हैं: ● शुरुआती — 4 बच्चे · ▲ प्रगतिशील — 6 बच्चे … नई योजना बनाने पर पुरानी हट जाएगी, लेकिन आपके पुराने रिकॉर्ड सुरक्षित रहेंगे। क्या आप बदलना चाहते हैं?" (a group with 0 is not listed). "नहीं, वही रखें" is the default: it has the focus, and Escape or a tap outside also keeps.
- **"हाँ, बदलें" only unlocks; it does not generate.** The picker, the time and the group panel come back with the plan's skill and length already chosen (the length is not saved as the phone's own choice), the button is the usual "📋 दैनिक योजना बनाएँ", and a hint says "✓ अब आप बदलाव कर सकते हैं। नई योजना बनाने के लिए '📋 दैनिक योजना बनाएँ' दबाएँ।" (✕ closes it). The old plan stays, named in a line with its own "योजना खोलें →", until the teacher taps Generate: one AI call for a different skill, and nothing lost if she changes her mind.
- **"योजना खोलें →"** puts this plan in place first, then goes to दैनिक योजना (the app may hold another subject's plan).
- **The check failed** (not a 404): "आज की योजना की जाँच नहीं हो सकी", the picker open, and Generate asks "… अगर योजना पहले से बनी है, तो नई योजना बनाने पर पुरानी हट जाएगी। आगे बढ़ें?" first. A failed check never replaces silently.
- **Per subject:** a maths plan locks only the maths tab.
- **Wording:** reviewed by Vaishnavi on 28 Oct and applied ("क्या आप इसे…", "योजना" not "प्लान", "दर्ज कर चुके हैं", "सुरक्षित रहेंगे", "अब आप…"), kept gender-neutral as in items 1–5, with the groups' Hindi names and shapes (not English names inside the Hindi), the hint naming the real button, and **नई** (not नई) as in the rest of the app.

**Server (no new route, no database change):** the GET reply gains `has_evidence` and `evidence_by_group` (`{beginner, progressor, proficient}`, zeros included), from `plan_service.plan_evidence`: per group, the children in the plan's **snapshot** (their group when the plan was made), with a result **that day**, on **the group's own skill**, recorded by **this teacher**, any channel (observed, reading aloud, photo). Each evidence row is joined to its own child. An older snapshot without roll numbers counts any of the teacher's children on the group's skill, so a missing list never hides evidence.

**The server never replaces a plan silently either.** `POST /plan/generate` takes `replace` (default false). If a plan already exists for that teacher, day and subject and `replace` is not true, it answers **HTTP 409** `plan_exists` ("इस दिन की योजना पहले से बनी है।"), checked first, before the group checks, the AI limit or any paid call. This protects against any client: an older app version, a second phone signed in as the same teacher, another tab. The app sends `replace: true` only after "हाँ, बदलें" (or "हाँ, बनाएँ" when the check failed). If a fresh screen gets a 409 because a plan appeared meanwhile, it loads that plan, shows the locked card and asks, rather than showing an error. One layer only: the server does not look at evidence or at which device asks (a second guard that refuses when results exist, unless a further flag is sent, is Phase 3). Batch scripts and seeding call the service directly and are not affected.

**Known issues** are now listed in `docs/KNOWN_ISSUES.md`: the N0.1.1 worksheet (colour only, and the answer in the question), and photo results counting as evidence as soon as the AI has read the sheet.

**Hindi reviewed** (Vaishnavi's note, section 7, 28 Oct): all of the above, including "आज की योजना देखी जा रही है…", "अभी की योजना: N2.3.2 — नई योजना बनाने पर यह बदल जाएगी", the failed-check question with "नहीं, रुकें" / "हाँ, बनाएँ", and the card's labels; the button stays "🪄 नई योजना बनाएँ". Her suggested feminine forms, English group names, "'Generate' दबाएँ" and a 409 notification were not applied (see the wording line above; a 409 shows the locked card and the question, not a notification).

## UI review and navigation (29 Oct)

A review of the lab version against the Build Stage criteria: **keep the user at the centre** and **explain how the solution comes together**, plus a click-through of the navigation. Built after the review; the new Hindi is for Vaishnavi.

**1. Review, step 1 waits for every group.** "दर्ज करें → बच्चों का काम देखें" (was "… साक्ष्य कैप्चर") stays off until every group with children has a decision, with "हर समूह के लिए एक विकल्प चुनें (बाकी: ● शुरुआती, …)" under it. A step marker "1/3 निर्णय · 2/3 बच्चों का काम · 3/3 विश्लेषण" shows where the teacher is; step 2's heading is "बच्चों का काम देखें" (was "साक्ष्य कैप्चर करें").

**2. "ℹ️ कैसे काम करता है?" (How it works)** (`components/HowItWorks.jsx`), a fold on the login screen and on Profile: four steps in the app's order, each naming what powers it (योजना · कौशल-सीढ़ी; दैनिक योजना · AI + जाँच; समीक्षा · फ़ोटो से पढ़ना, नमूना; प्रगति · आज के नतीजे), the loop ("↻ आपके निर्णय और आज के नतीजे कल की योजना का सुझाव बनाते हैं।") and "🔒 बच्चों के नाम AI को कभी नहीं भेजे जाते।". For criterion 2: an evaluator finds the whole loop in one place.

**3. Logout at the top of Profile, asking first.** It was at the very bottom (after the leader's teacher list) and signed out at once, although signing out removes this phone's offline plans and worksheets. Now it is in the account card, under the code, and asks "लॉग आउट करें? इस फ़ोन पर रखी योजनाएँ और वर्कशीट हट जाएँगी।". A logout on every screen was considered and not done: Profile is one tap away on every screen, and a header button costs space and invites a mis-tap on a shared phone.

**4. Failures in plain Hindi** (`services/errors.js`). The screens showed the server's raw text, often English ("योजना बनाने में समस्या: Plan generation failed: …"). Now: what failed, why and what to do, e.g. "योजना नहीं बन सकी। सर्वर अभी जवाब नहीं दे रहा। थोड़ी देर बाद फिर कोशिश करें।"; a message the server already wrote in Hindi is kept; the offline message is unchanged; plainer reasons where they help (a photo that cannot be read; a reading-aloud roll number not in the class). Used for making a plan, recording decisions, photo analysis, the two Review saves, the reports and opening a worksheet. The raw text goes to the console. The AI-limit message is the server's own (both languages) and is unchanged.

**5. ⓘ instead of hover tooltips** (`components/Hint.jsx`). A phone never shows a `title` tooltip, so the places where a teacher hesitates get a tappable ⓘ (44 px) that opens a line or two: on Review step 1, what each choice does to the next plan; on step 2, what Observed, Photo and Reading aloud mean.

**6. "⭐ सुझाया गया" (Suggested) at the top of the Plan screen's skill list** (`components/SuggestedSkill.jsx`): the Progressors' skill the last review points to (the existing `GET /plan/proposal`: advance → the next skill; re-teach or not sure → the same; no decision but many mistakes → the same), with the reason ("पिछली समीक्षा (24 अक्टू॰): प्रगतिशील: ⬆ आगे बढ़ें"), and "यही चुनें" chooses it as the list does. No card when there is no suggestion, when it is not in this subject's list, or when today's plan already exists (locked). No server change.

**Navigation (the click-through):** a teacher who saved an observation and followed "प्रगति टैब पर … देखें →" could not get back: the Review forgot everything when left, started again at step 1 and (with point 1) asked for every decision again.
- **A. The Review keeps its place** (`services/reviewPlace.js`): step, way of checking, group and the decisions on screen, for that teacher, day and subject, in this browser tab only (`sessionStorage`: it survives a reload, not closing the tab; no names, no photos). An analysis is not kept (it can be reopened from "आज का विश्लेषण"), so a review left at step 3 comes back at step 2.
- **A. The Review loads today's plan itself** (after the app is reopened it is not in memory) and carries on from the decisions already recorded today: with one for every group it opens at step 2; otherwise the recorded ones are already chosen on step 1. A choice the teacher makes on the screen is never overwritten by the server's copy. With no plan: "आज इस विषय की योजना नहीं बनी है…" and "योजना बनाएँ →"; if it cannot be loaded, it says so instead. **Server:** the plan reply (`GET /plan/{teacher}/{date}/{subject}`) gains `decisions` (that day's recorded decision per group).
- **B. Ways back inside the Review:** step 2 "← निर्णय बदलें" (decisions kept); step 3 "← बच्चों का काम: अगला समूह या तरीका" (nothing reset); the step marker can be tapped for steps already reached (step 3 only when there is an analysis to show); "↺ नई समीक्षा शुरू करें" asks first. The header's second "चरण x/3" is gone (the marker shows it).
- **C. Progress opened from the Review's pointer** shows "← समीक्षा पर लौटें" at the top (not when opened from its tab).
- **E. दैनिक योजना leads on:** "पढ़ाने के बाद: समीक्षा करें →" after the plan; with no plan, "योजना बनाएँ →".
- **Not done (suggested):** the phone's Back button following the Review's steps and closing dialogs (D), and Profile's and the register's "← वापस" returning to where the teacher came from instead of always to the Plan screen (F).

## The Review, reworked (29 Oct, later)

From the team's click-through of the Review, one point at a time; each was reviewed in the browser before this commit.

**Three steps, each heading its step:**
- **1/3 · आज हर समूह कैसा रहा?** The teacher's **पहला अनुमान** (first judgment) per group, before looking at any evidence (so the AI's reading cannot anchor it). Saved as stage `first`.
- **2/3 · बच्चों का काम देखें.** The children's work, three ways. A photo analysis opens **inside** this step (2/3 · 🔍 फ़ोटो विश्लेषण), not as a step. "आगे: अंतिम निर्णय →" leads on.
- **3/3 · अंतिम निर्णय** (new). Per group with children: the first judgment, **today's evidence** ("✓ A 2 · ~ PA 1 · ✗ NA 3 (7 में से 6 का आकलन)", fetched afresh), the app's suggestion (re-teach when a third or more made a mistake, the Plan screen's rule; "बहुत कम बच्चे जाँचे गए…" under 4 checked), and the three choices **starting on the first judgment**; a change is said ("पहला अनुमान ⬆ … → अंतिम 🔄 …"). "अंतिम निर्णय दर्ज करें" saves stage `final`: the decision tomorrow's plan suggests from. If the evidence cannot be shown it says so ("अभी नहीं दिख रही"), never "nobody assessed".
- The separate step marker is gone (the headings carry "1/3"…); the back buttons carry the step they go to ("← 1/3 पहला अनुमान बदलें", "← 2/3 बच्चों का काम"). "नई समीक्षा शुरू करें" is removed (every change has its own way). The Review's icon is **☑️** (it is not only photos; 📸 stays on the photo way).

**Step 2, the ways of checking:**
- Tabs say what the teacher does: **✓ देखकर दर्ज करें**, **📸 वर्कशीट की फ़ोटो**, **⏱️ पढ़कर सुनाना**; a line under them says who does what (the photo way: "AI हर बच्चे का काम पढ़ता है"); the repeated card titles ("शिक्षक अवलोकन", "पठन प्रवाह / ORF"…) are gone.
- **"ⓘ यही तरीका क्यों?"** (when today's skills need only some ways) explains why each way fits the skill, names today's groups and skills, and keeps "दूसरे तरीके भी दिखाएँ".
- **"▸ कैसे करें?"** under the way chosen: observing ("स्वतंत्र अभ्यास (तुम करोगे) के दौरान बच्चों को काम करते हुए देखें, फिर हर बच्चे के लिए A / PA / NA चुनें", A / PA / NA meanings, and for a group that also has a worksheet: "इस कौशल की वर्कशीट अभ्यास के लिए है; … वर्कशीट की फ़ोटो से नहीं"); photo (roll number at the top, flat, good light, the sample, no names); reading aloud (one minute, correct words, what counts as an error). The plan's own AI-written observation prompts are **not shown** (they described a task the plan did not contain: `docs/KNOWN_ISSUES.md`).
- **Recorded choices stay visible** (from the server): each child's recorded A / PA / NA is shown chosen with "✓ दर्ज"; a change is marked "PA → NA" until submitted; tapping the recorded choice again is no change; Submit counts "· 1 नया, 2 बदलाव". After a save the block says what happened: "✓ 2 अवलोकन बदले गए", "✓ 3 अवलोकन: 1 नया, 2 बदले गए", "कोई बदलाव नहीं", "बदले: रोल 4 PA → NA", a roll not in the class "… कक्षा में नहीं है, दर्ज नहीं हुआ" (never counted), in the singular for one. Reading aloud lists "आज पढ़ चुके: N बच्चे" with their numbers.
- **Reading aloud shows the text to read:** one from the bank for the skill (or its grade), **not read in class today**, the same all day ("पढ़ने का पाठ: «पानी बचाओ» (72 शब्द)", "पाठ दिखाएँ" opens it large for the child). The score records **that** passage; the fixed `RP-004` is gone (none shown: none recorded).
- The Progress pointer in the two save blocks is a small button, **"📊 प्रगति देखें →"**; step 3 has none (the review is over; the tab does it).
- **Each group's skill** is shown the same way on every step ("● शुरुआती · N0.1.1 · …"; on steps 1 and 3 without the group, which is in the card's badge).

**The plan screen:** "☑️ आज की समीक्षा: कैसे जाँचें" (a fold): each group, its skill and its way of checking, who does what, the worksheet-is-practice line for an observed group, the text to read aloud, the general observing line.

**The printed plan:** its "अवलोकन:" line is the general instruction, not the plan's AI prompt.

**Server:**
- `POST /review/decisions` takes `stage` (`first` default, or `final`). Either becomes the group's current decision (`teacher_decision_<group>`, what tomorrow's plan suggests from; the latest wins, so a review stopped after step 1 still has one); the first judgment and the final decision are also kept (`teacher_first_`, `teacher_final_`), and survive a plan made again.
- The plan reply (`GET /plan/…`) gains `first_judgments`, `final_decisions` and `today_evidence` (per group: A / PA / NA, assessed, group size, `recommend`, `very_small`, from `progress_service.get_today`, which gains `recommend` and `very_small`).
- `POST /review/observed` replies per child: `new` / `changed` / `unchanged` (with the previous status) and `not_found` rolls; `GET /review/coverage/…` gains `recorded` (each child's newest result today; for reading aloud with the two numbers).
- `GET /review/channels/…` gives a reading-aloud group a `passage` (not one read today); `POST /review/orf` takes `passage_id` optional (no made-up id).

**Still to build (agreed, next):** "✓ अभी दर्ज करें" on the plan screen's teach block of a group checked by observation or reading aloud, opening the Review's step 2 for it during the lesson, without asking a first judgment first.

## How to see it

```powershell
# in the lab worktree (C:\dev\Ankur-Saathi-lab), with its own database ankur_lab
backend\venv\Scripts\Activate.ps1
cd pwa; npm run build; cd ..\backend
uvicorn app.production:app --port 8001      # http://localhost:8001 ; main can run on 8000 at the same time
```

- **Run it in your own terminal.** Started from a Claude Code session, the server was stopped repeatedly by the session's background-process reaper.
- **Restart it after a backend change** (the time chip's commit changed `plan_service.py`). A new front-end build needs only a reload of the page.
- **Making a plan needs an Anthropic key.** The lab's `backend\.env` has `ANTHROPIC_API_KEY` empty. Without one, Generate fails with "Could not resolve authentication method". To use main's key for one terminal session only, without writing it into the lab folder or printing it, run this before `uvicorn`:
  ```powershell
  Set-Item Env:ANTHROPIC_API_KEY ((Get-Content C:\dev\Ankur-Saathi\backend\.env | Select-String '^ANTHROPIC_API_KEY\s*=').Line -split '=', 2)[1]
  ```
  Each plan is a real, metered AI call (about 1–1.5 minutes). Reopening today's plan costs nothing.
- **On a phone:** start the server with `--host 0.0.0.0`, put the phone on the same Wi-Fi, and open `http://<this PC's address>:8001` (192.168.1.10 on 28 Oct). If Windows asks, allow Python on private networks only. Over plain `http://` the offline worker does not install, so offline use and "add to home screen" are not tested this way.

Sign in with a demo card. Try:
- Profile → "सिर्फ़ हिंदी दिखाएँ", and "छोटी स्क्रीन"
- योजना → "आज का समय" → choose N2.3.2 → open the group panel → Generate
- दैनिक योजना → the time chip, the skill in each block's title, tap a teach block → "🖨️ प्रिंट" → Print or "Save as PDF" (one A4 page?)
- समीक्षा, प्रगति

Check at phone width (F12, then Ctrl+Shift+M, 360 px).

For the phone test of the signal panel before the server sends it, build with the lab mock, and build again without it afterwards:

```powershell
cd pwa; $env:VITE_MOCK_SIGNAL='1'; npm run build; Remove-Item Env:VITE_MOCK_SIGNAL; cd ..\backend
```

Then: दैनिक योजना → each teach block shows its panel; Profile → "छोटी स्क्रीन" → the plan screen again.

## Tests

`python scripts\run_tests.py --env-file backend\.env --pwa`, run on the lab database:
- **42 backend suites:** all OK (new: `test_review_recorded.py`, 16 checks: new / changed / unchanged, rolls not in the class, the recorded results per child, another group's child kept out, the text to read aloud never one read today, a score with no passage; `test_plan_routes.py`, 19 checks: the two stages, which one wins, today's evidence with the suggestion and the too-few flag; the day's review decisions in the plan reply; nothing recorded, one observation, the same child twice, results that must not count (yesterday, another skill, another teacher, a child outside the snapshot), a photo result, an older snapshot, and no plan; `test_plan_service.py`, 26 checks: 45 / 60 / 90 minutes reach the prompt and PART C, 90 without the field, other values refused, the stored plan records the chosen length (not the AI's total), a sample plan records 90, an existing plan refused with 409 without `replace` (before any paid call, evidence or not) and replaced with it, per subject; and `test_progress_today.py`, 29 checks: today vs yesterday fixtures, counts once per child, A + PA + NA = assessed, the rare lines, reading aloud scored on its own skill, "still to score" per day, group and skill)
- **31 front-end suites:** all OK

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
- `plan_time_chip.test.mjs` (10): the chip reads the recorded length and never the AI's `total_minutes`; an older plan rounds to 45 / 60 / 90 within 5 minutes (both ways), otherwise the exact sum; the printed plan agrees
- `review_steps.test.mjs` (12): the Review's step 1 waits for every group with children, names the ones left, the step marker, the plain wording, and the two ⓘ hints
- `ui_review.test.mjs` (15): "कैसे काम करता है" on the login screen and Profile (four steps, the loop, names never sent), logout at the top asking first, and failures in plain Hindi (offline, 5xx, a Hindi server message kept, a plainer reason, "Hindi only")
- `plan_suggested_skill.test.mjs` (13): the suggestion card from the last review, each reason, "यही चुनें" choosing it (and clearing the grade filter), and no card in four cases or when locked
- `review_final.test.mjs` (22): step 3: the first judgment, today's evidence, the suggestion and the too-few line, choices starting on the first judgment, the change line, recording stage `final`, reopening at step 3, evidence that cannot be shown
- `review_recorded.test.mjs` (18): recorded choices shown and kept after a save and on coming back, changes marked before Submit, the counting Submit, the block's new / changed / no change / not in the class, "यही तरीका क्यों?", reading aloud's list
- `review_howto.test.mjs` (20): "कैसे करें?" for each way (the general observing line, not the plan's AI prompt; the worksheet-is-practice line only with a worksheet), the skill line, the text to read aloud and the passage recorded, the plan screen's "आज की समीक्षा"
- `review_navigation.test.mjs` (26): the Review loading today's plan and carrying on from recorded decisions, keeping its place across Progress, per subject, never overwriting the teacher's tap, the ways back, the step marker, the new-review question, "← समीक्षा पर लौटें" on Progress, and the plan screen's links on
- `plan_load_existing.test.mjs` (32): the real Plan and plan screens in a simulated browser: the status card and the locks, no plan made on opening, the question and its default, the groups and counts, "हाँ, बदलें" unlocking without generating and then one plan, keeping (button, Escape, a tap outside), opening this plan, a 404, a failed check, each subject on its own, `replace: true` only after a yes, and a 409 (a plan made meanwhile) turned into the locked card and the question
- `dev_mock_signal.test.mjs` (9): the lab mock fills only plans, only with the setting, never over the server's own signal
- `plan_session_length.test.mjs` (13): the real Plan screen in a simulated browser: 90 on first use, a stored 60 preselected, the 44 px targets, and the chosen time in the request

Updated to the new wording or format:
- `plan_screen.dom`: the Generate request now also carries today's time; it and `plan_session_length` answer "no plan today" for the new check.
- `consent.dom`, `login.dom`, `group_skills`, `reteach_note`, `no_audio`. These now check that both the Hindi and the English are present, instead of requiring "Hindi (English)" in brackets.
- `login.dom` also checks the new login layout: the card order, the five test-teacher chips and their tap targets.
- `demo_accounts` now reads the guide's range row ("MPT102 to MPT106") and checks each of those codes is on the login screen with its password.

Checked on a real phone: items 1–3 (Progress), 28 Oct. Reviewed in the browser before committing: the UI review and navigation changes, 29 Oct. Not yet: the rest, for the phone pass on Thursday (including the printed plan's fit on one A4 page).

**Mutation runs:** for each new test, the code was broken on purpose in the ways the spec names (a dropped or reordered question, a wrong extras count, a "random" note, a smaller prompt, a panel for a null shape, a folded panel or note, the chip reading the AI's `total_minutes`, the rounding window off by one, the server not recording the length, a talking point or a name on the print page, a longer allowance, and more). Every one made its test fail. Two tests were strengthened on the way, when a first run let a mutation through (`plan_signal_panel`: a later shape drawn as a writing panel; `plan_print`: a three-line allowance).

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
aff6006 handover note: reading aloud shows pace; the codes note and what is left for later
15d2e0d Plan asks "आज का समय" (45/60/90); the plan is laid out for it (session_minutes on /plan/generate)
c591682 signal panel and skill in each teach block; "छोटी स्क्रीन"; lab-only mock signal (VITE_MOCK_SIGNAL=1)
77ad564 CURATED_SKILLS.md corrections; content expansion moved to ROADMAP section 9
e44034d printed plan (/plan/print): one A4 page, the screen's own signal panel (compact)
a55d3b9 time chip: the server records session_minutes on every plan; older plans add up their blocks
c92cb24 handover note: 28 Oct follow-up, how to run it on a phone and with a key
8d40869 item 12: Plan screen keeps today's plan (locked card, ask before replacing, evidence counts); KNOWN_ISSUES.md
d49580a server never replaces a plan silently (409 plan_exists unless replace: true)
3c82855 item 12 wording after Vaishnavi's review
(next)  UI review (step 1 waits, how it works, logout, plain errors, ⓘ hints, suggested skill) and Review navigation (keeps its place, ways back)
```

Files: 87. They're `pwa/src` (45), `pwa/tests` (27), `docs/` (6: `GROUP_SKILLS.md`, `DEMO_ACCESS.md`, `CURATED_SKILLS.md`, `ROADMAP.md`, `KNOWN_ISSUES.md` and this note) and the backend (9: `progress_service.py`, `review_service.py`, `plan_service.py`, `routes.py`, `schemas.py`, `tests/test_progress_today.py`, `tests/test_plan_service.py`, `tests/test_plan_routes.py`, `tests/test_review_recorded.py`). **No database, migration or prompt changes**, and no new server route (`/plan/print` is a screen of the app). New stored values live in existing JSON: the plan's `session_minutes`, and the day's `teacher_first_` / `teacher_final_` decisions next to `teacher_decision_`. The plan reply also carries `has_evidence`, `evidence_by_group`, `decisions`, `first_judgments`, `final_decisions` and `today_evidence`; `POST /plan/generate` takes `session_minutes` and `replace`; `POST /review/decisions` takes `stage`; the observed save, coverage and channels replies gained fields (above).

`docs/CURATED_SKILLS.md` and the new `docs/ROADMAP.md` section 9 are the team's own documents, committed in the lab with these corrections. The lab mock (`pwa/src/services/devMockSignal.js`, `pwa/tests/dev_mock_signal.test.mjs`) is for the phone test: a normal build leaves it out, but whether to package it for `main` at all is the release owner's choice.

### ⚠ Depends on lab-only work

`dce44f3` is a separate WIP snapshot: employee-code sign-in, the consent gate and the login rework. It is **lab-only and still under review**, and it is not part of this handover. The UI commits build on it, and **8 files overlap**:

- `pwa/src/App.jsx`
- `pwa/src/screens/AccountScreen.jsx`, `ChangePinScreen.jsx`, `ConsentGate.jsx` (new in the WIP), `LoginScreen.jsx`
- `pwa/tests/consent.dom.test.mjs`, `login.dom.test.mjs`
- `docs/DEMO_ACCESS.md`

So the UI commits **cannot be applied to `main` on their own as they are.** The packaging choices are:
- **(a)** take the sign-in work first, then the UI
- **(b)** take the UI without those 8 files' sign-in parts, and redo the small UI edits in them by hand. Mostly that means wrapping labels in `<Bi>` and the tappable demo cards, plus, since 28 Oct, the `/plan/print` route and the hidden bottom bar there (`App.jsx`) and the "छोटी स्क्रीन" toggle (`AccountScreen.jsx`).

## Open decisions for the team

0a. **The Review rework's Hindi** (29 Oct, later) is not yet reviewed, and **two of its points are teaching decisions, not only wording: the meanings of A / PA / NA ("करके दिखाया, बिना मदद / मदद से, या आधा सही / अभी नहीं") and the reading-aloud error rule ("गलत शब्द, छूटा शब्द, या जो शब्द आपको बताना पड़ा")**. The rest: "पहला अनुमान", "अंतिम निर्णय", the step headings and back buttons, the three way labels and their "who does what" and "why" lines, "कैसे करें?" and its steps, "पढ़ने का पाठ", "पाठ दिखाएँ…", the recorded / changed / no-change lines, "प्रगति देखें", "आज की समीक्षा: कैसे जाँचें", the general observing line and the worksheet-is-practice line.
0b. **The UI review's Hindi** (29 Oct) is not yet reviewed: the step names "निर्णय / बच्चों का काम / विश्लेषण", "हर समूह के लिए एक विकल्प चुनें", "दर्ज करें → बच्चों का काम देखें", the "कैसे काम करता है" texts, the logout question, the error sentences, the two ⓘ hints, "सुझाया गया / यही चुनें / ✓ चुना गया" and the reasons, "निर्णय बदलें", "बच्चों का काम: अगला समूह या तरीका", the new-review question, "समीक्षा पर लौटें", "पढ़ाने के बाद: समीक्षा करें", "योजना बनाएँ →", the Review's no-plan and could-not-open lines, and "आज की योजना खोली जा रही है…".

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
8. **The follow-up spec's Hindi** (the new labels: "आज का समय", "तीन मुख्य प्रश्न", "लेखन कार्य", "छोटी स्क्रीन", "आज की गतिविधि", the printed plan's lines) is not yet reviewed. The spec's own wording was used.
9. **The printed plan is Hindi only for every teacher,** whatever the "सिर्फ़ हिंदी" setting, so that a printed sheet is the same everywhere and the English cannot push it past one page. Revisit if teachers want the English on paper.
10. **The skill's description is not in the teach block's title,** only its code. It is in the group cards at the top of the plan screen (decided 28 Oct, option 1).
11. **Item 9 ("आज क्या अलग है")** is held until after the phone pass.
