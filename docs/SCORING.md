# How a child's day is scored

A photographed worksheet becomes a **score** and then a **status** (achieved / partly achieved / not achieved). Both are computed **in code** from the per-problem results the AI reads off the sheet:
`rescore` (prompts/vision_analysis.py) for the score, `derive_status` for the status. Tests: `backend/tests/test_scoring.py`.

## What counts toward the score
- **Required problems** (the first N on the sheet: 5 Beginner, 6 Progressor, 8 Proficient) are always scored. One left blank counts as wrong.
- **Extras** (the rest) count only if the child attempted them. A blank extra is not an error.
- **EXTRAS CAN ONLY HELP** (decided 21 Oct). The result is the better of the required problems alone and the required problems plus the attempted extras, so a wrong extra never lowers it and right extras can raise it.
  Before, an attempted extra counted whether right or wrong: a child with all 6 required problems right and 2 extras wrong scored 6 of 8 = 75% and was "partly achieved".
  `summary.score_basis` says which basis was used, and `correct`, `total_problems` and `accuracy` always describe that same basis.
- A problem the child **copied wrongly** is left out of the score (neither right nor wrong).
- An answer the app **cannot read** counts as not correct, and is listed on the result screen for the teacher to check in the notebook.

## What the status needs
Each skill carries its own thresholds in `competencies.apna_criteria`:

| Group (N2.3.2 lesson) | Skill | Required | Achieved | Partly | Not achieved |
| --- | --- | --- | --- | --- | --- |
| Beginner | N2.3.1: at least 85%, at most 50% | 5 | 5 of 5 | 3 or 4 | 0 to 2 |
| Progressor | N2.3.2: at least 80%, at most 40% | 6 | 5 or 6 | 3 or 4 | 0 to 2 |
| Proficient | N3.3.1: at least 80%, at most 40% | 8 | 7 or 8 | 4 to 6 | 0 to 3 |

If the skill says `no_persistent_misconception`, the same mistake twice or more stops "achieved" even on a high score (with 5 to 8 problems this rarely changes anything).

## Which skills have a calculated status
- **40 skills** (type `computation`: 32 numeracy, 8 literacy) have a numeric rule, and the status is calculated.
- **61 skills** have none: **50 observational** (the teacher's own A / PA / NA is the evidence), **8 written production** (descriptive criteria) and **3 fluency** (oral reading, which has its own words-per-minute rule).
  For these, `derive_status` returns nothing and the status of a **photo** is **the AI's own label** (`status = derive_status(...) or model_status`).

## Known gap
The knowledge base says "achieved needs 2 sessions" (`sessions_required: 2`). **The code does not use it**: one good day shows as "achieved". The daily status is evidence for that day, not mastery.
