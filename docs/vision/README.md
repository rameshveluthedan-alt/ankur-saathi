# Photo analysis: a smoke test on five worksheets (30 Oct 2026)

**What this is.** The scored run of the app's photo analysis (`scripts/eval_vision.py`, the same prompt, photo shrinking and model call the app uses) on five photographed
N2.3.2 Progressor worksheets: three printed sheets (rolls 14, 4, 18) and two notebook pages with the problems copied from the board (rolls 25, 27). The photos were taken on
19 Oct 2026; the scored run is of 30 Oct, at about $0.03 a photo.

**What this is not.** A validation. It is five sheets, one skill, and **the handwriting is an adult's** (the person who prepared the sheets wrote them, with deliberate mistakes
and copying slips from the protocol in `docs/VISION_PHOTO_TEST.md`), not children's. It shows how the analysis behaves on clean, deliberate examples, and where it is weak.

| File | What it is |
|---|---|
| `eval_summary.md` | the score, written by the script |
| `eval_problems.csv` | every one of the 40 answers: what was written, what the AI read, and what it concluded |
| `truth_numeracy.csv` | the answer-by-answer truth, written before the run and checked by the sheets' author (Claude drafted the transcription from the photos; the author checked every row) |
| `plan_n232_19oct.json` | the answer key, read off the printed sheet (the sheets are not the plan in `docs/samples`) |

The photos are not in the repository (they are handwriting on a school-style sheet; none shows a name).

## What it showed
- **Reading: strong.** Roll number 5 of 5. The six sums on each sheet: 30 of 30 read exactly, and the AI's right-or-wrong matched the teacher's on all 24 that were scored.
  No answer was wrongly accepted or rejected. 39 of the 40 answers were read with the right number; the one misread is a crossed 7 running into a 1 (written 715, read 745).
  The script's "text answers 7 of 10" counts two word problems whose truth was written as the final number only ("45") while the AI read the whole line ("38+17=45"): a format
  difference in the truth file, not a misreading.
- **Naming the mistake: weak.** Right on 1 of 3 sheets. On any sheet with carry mistakes it named M1 (drops the carry) and M2 (writes the whole ones sum) together, so it cannot
  tell them apart; it never named M3 (carries the wrong digit) and called both such answers M2.
- **Copy errors: 5 of 8 found.** Missed: 45 + 35 copied for 25 + 45 (roll 4), and a plus changed to a minus (roll 18, twice). A missed copy error is scored as a wrong answer.
  No correct answer was flagged as a copy error.
- **Carry digit: 7 of 9** seen or not seen correctly, 2 not reported.

In practice: the photo analysis reads handwriting and numbers very well, but its diagnosis of which mistake a child made is rough. That fits how the app uses it: the teacher
decides, and the analysis proposes. See `docs/KNOWN_ISSUES.md`. A real validation needs children's handwriting, more skills and Hindi sheets.
