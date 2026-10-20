# Levels: what changes a child's group, and what daily results are for

A child's level (Beginner, Progressor or Proficient, per subject) decides which group they are in. **A level changes only
through an assessment**: the baseline, a periodic round, or a re-assessment of one child. It never changes from daily results.
There is no "move this child" button either: the teacher's lever is "re-assess".

## Why daily results cannot change a level
They are about one skill, gathered right after it was taught, from a sample of the group, on a sheet of a handful of problems.
That is a good signal for tomorrow's teaching and a poor basis for re-grading a child. An earlier version suggested level
changes after 3 days on the same skill. With each skill taught for a day or two that almost never happened, and when it did
it could mislead (for example moving a Proficient child down for struggling with the new extension skill). It was removed.

## What daily results ARE used for
| Use | How |
| --- | --- |
| The group's advance or re-teach decision | the sample's accuracy and the misconceptions found are shown next to the teacher's own judgement; she decides |
| What to re-teach | the next plan reads the misconceptions found at the **most recent review within a week, in the same subject** (so a Friday review feeds a Monday plan, and numeracy gaps never become a literacy re-teach) |
| Whom to re-assess first | the **"consider re-assessing" flag** below |
| Reports | the class report and the officer report show each child's level and when it was last set |

## The "consider re-assessing" flag
A flag changes nothing and has no Accept button. It appears when a child's recent daily work does not match their level.

It needs, from the skills that defined the child's group on each day (different skills on different days are fine):
- at least **3 qualifying days among the last 4**, the newest within **14 days**;
- a written sheet counts only with at least **5 assessable problems** (problems copied differently are not counted);
- only evidence dated **after the level was last set** (the last assessment, or registration);
- **3 of 4 (or 3 of 3) achieved** gives "doing well" (Beginner or Progressor); **3 of 4 (or 3 of 3) not achieved** gives
  "struggling" (Progressor only).

Proficient children get no flag: their daily skill is the new extension, where early struggle is normal and says nothing about
their level.

Code: `check_reassessment_flags` in `prompts/vision_analysis.py`. Tests: `backend/tests/test_reassessment_flags.py` (16 patterns)
and `backend/tests/test_reteach_lookback.py`.

## Where the level comes from today
- **Registration:** the teacher's own judgement per subject, or Progressor if left empty (`docs/REGISTER.md`).
- **Baseline:** `/baseline/generate` and `/baseline/submit` exist in the backend; there are no screens for them yet.
- **Periodic rounds and on-demand re-assessment:** not built. Until they are, levels stay as registered or as the baseline set them.

## Still to build
1. Screens for the baseline and periodic rounds, written on the same ladder, using all three channels.
2. A **history of rounds** (each child's level at each round). Today only the latest level is kept, so progress between rounds
   cannot be shown; this is also the evidence needed for impact reporting.
3. **Re-assess one child now** (the on-demand mode the assessment code already describes), which becomes the only way to change
   one level between rounds.

## Demo data
`scripts/demo_progress.py` writes marked synthetic evidence; the flag rule treats it as "role unknown" (it has no real plan
behind it), and every other condition still applies. Because of the 14-day rule, seed the demo close to when it is shown.
