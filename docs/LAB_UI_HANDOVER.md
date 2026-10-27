# Lab handover: teacher UI review (27 Oct)

**Branch:** `lab/experiments` (lab worktree, not pushed) · **Base:** `main` at `4e17b06` (Release candidate 3)
**Status:** done in the lab and tested; **not** in `main`. To be reviewed, then packaged for `main` by the release owner.

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

## Tests

`python scripts\run_tests.py --env-file backend\.env --pwa`, run on the lab database:
- **38 backend suites:** all OK
- **14 front-end suites:** all OK, 287 checks

New suites:
- `bilingual.test.mjs` (13 checks)
- `cfu_fold.test.mjs` (6)
- `notices.test.mjs` (6)

Updated to the new wording or format:
- `consent.dom`, `login.dom`, `group_skills`, `reteach_note`, `no_audio`. These now check that both the Hindi and the English are present, instead of requiring "Hindi (English)" in brackets.

Not checked yet: by eye on a real phone.

## The commits

The UI work is the 12 commits after `dce44f3`:

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
```

Files: 35. They're `pwa/src` (27), `pwa/tests` (6) and `docs/GROUP_SKILLS.md` / `docs/DEMO_ACCESS.md`. **There are no backend, database or prompt changes.**

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
