# Real-photo test of the Vision analysis (numeracy and Hindi literacy)

Goal: measure how well the photo analysis reads real children's worksheets, and put the numbers on the evaluation slide.
Run: `python scripts/eval_vision.py ...` (see its header). It uses the same prompt, the same photo shrinking and the same model
call as the app, so the numbers describe what a juror will get.

## What to prepare (15 to 25 sheets per subject is enough)

1. **Two formats, both.** The app's printed worksheets, **and** notebook pages with the problems copied from the board. A school with
   no printer will only ever have notebook pages.
2. **One "child" per sheet,** with a roll number written clearly. If you can, have **several different people** write them: the AI
   must cope with more than one handwriting. Use pencil on some and pen on others.
3. **Vary the conditions on purpose:** some photos flat, in good light, whole page in frame; some at an angle, in dim light, with a
   shadow, slightly blurred or with a folded corner. Use the phone's normal camera, full resolution. The app shrinks photos itself.

## Numeracy sheets: the answers to write

all correct (a few) | forgets the carry (62 written 52) on several problems | writes the whole ones sum (512) | carries the wrong digit (72) |
one careless slip only (should NOT be called a pattern) | extras left blank, and some attempted | a rubbed-out answer, a crossing-out |
a carry digit written above the tens, and one sheet with no carry digit.

## Hindi literacy sheets: the answers to write

Hindi answers are where jurors will probe, so cover these on purpose:
1. **Exactly the key's wording** (a few).
2. **Correct but worded differently** ("वह किसान होते हैं" for "किसान"): the AI should accept it.
3. **Correct with a small spelling or matra slip** (missing nukta, wrong choti/badi ee): should be accepted when the word is clear.
4. **Partly correct** (one of two things asked for): should be flagged partial, not correct.
5. **Wrong** (a different fact), **copied a sentence from the passage** that does not answer the question, and **blank**.
6. **Short** (one word) and **long** (a full sentence) answers; some on the shirorekha, some floating above or below it.
7. **Hard handwriting:** joined letters, tiny writing, an overwritten word, and ink that bleeds through the page.

## Name the photos

`roll07_printed_a.jpg`, `roll12_notebook_b.jpg`: roll number, format, a letter. Keep the originals.

## The truth file (this is what makes the score possible)

Copy `vision_truth_template.csv` and write **one row per problem on every photo**:

| Column | What to write |
| --- | --- |
| photo_file | the file name |
| roll_number | the roll number the child wrote |
| problem_number | the problem's number on the sheet |
| child_wrote | exactly what the child wrote, even if wrong; empty if left blank |
| judged | what a teacher would say: correct / partial / incorrect / blank (numeracy: filled in for you if you leave it empty) |
| carry_digit_visible | yes / no / na (numeracy only) |
| expected_pattern | a mistake id such as N2.3.2-M1, or `slip` for a careless error; empty otherwise |
| notes | anything useful |

The `judged` column is **your** judgement, written before you see the AI's answer. Do not look at the AI's output first.

## What gets scored

Roll number read correctly | each written answer read correctly (exact and "close enough") | right and wrong judged as the teacher
would, split into wrongly accepted and wrongly rejected | partly-correct answers flagged | carry digit seen | mistake pattern named
correctly | time and cost per photo | and the worst misreadings, listed. Results go to `docs/vision/` (commit them).

## Known limits to say out loud

- A written answer cannot show reading problems such as the "word-caller" (reads accurately, cannot answer): that needs oral
  reading evidence, so the AI is told not to diagnose it from writing.
- An answer the AI cannot read is flagged for the teacher to check, and counts as not correct until she does.
