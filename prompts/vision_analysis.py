"""
Ankur Saathi — Claude Vision Worksheet Analysis
The feedback half of the daily loop: photograph → extract → diagnose → adapt.

Pipeline: teacher photographs batch of worksheets → memory-safe upload →
Claude Vision extracts answers by roll number → classifies against L1
misconception taxonomy → updates child_competency_status → feeds next
day's orchestration prompt.
"""

import json
import re
from datetime import date, timedelta
from typing import Optional


# ============================================================================
# SYSTEM PROMPT — constant across all Vision calls
# ============================================================================

VISION_SYSTEM_PROMPT = """You are the Ankur Saathi worksheet analyser. You examine photographs of children's completed Hindi-medium worksheets and extract answers, diagnose misconceptions, and classify performance.

## Rules

1. **Roll numbers only.** Children write their roll number on the worksheet, NEVER their name. It is 1 to 99, or in a multi-grade class a class number of up to three digits that carries the grade (305 means Grade 3, roll 5): read ALL the digits written. Refer to each child as "Roll No. X". If you cannot read the roll number, mark it as "unclear" — do not guess.

2. **Extract, then diagnose.** For each child's response to each problem:
   a. Extract the handwritten answer exactly as written
   b. Compare to the answer key provided
   c. If wrong, classify the error against the misconception taxonomy provided — do NOT invent new categories
   d. Assign confidence: "high" (clear handwriting, clear error pattern), "medium" (legible but ambiguous), "needs_verification" (unclear handwriting)

3. **Pattern over single instances.** A misconception is diagnosed only when the same error pattern appears in 2+ problems. A single error is an "arithmetic slip" unless the pattern is unmistakable (e.g., answer is exactly 10 less than correct on a carry problem).

4. **Hindi handwriting specifics:**
   - Children write on the shirorekha (headline); numbers may float above or below
   - Common handwriting confusions: 2/3, 6/9, 5/8 — flag "needs_verification" if ambiguous
   - Matra placement in Hindi words: ि goes LEFT of consonant in correct writing
   - Response grid structure: problems are numbered, answers go in designated boxes

5. **Never hallucinate answers.** If you cannot read a response, say so. An "unclear" is better than a wrong extraction.

6. **Drawings and working are scaffolding, not answers.** Children may draw tens as vertical lines and ones as dots, or write a small carry digit. The photo may be a printed worksheet OR a notebook page where the child copied the problems from the board: in both, find the place where the final answer is written (the answer row of the grid, or the answer box). Never infer an answer from a drawing: if no number is written there, the answer is blank (extracted_answer null). Never mark a child down for a drawing, an untidy drawing, or no drawing, and never diagnose a misconception from a drawing alone.

7. **Read what is written; never reconstruct it.** extracted_answer is the digits the child actually wrote, in the order written. In a column grid (digits stacked in boxes), the answer is the LAST row: read it digit by digit. Never work out what the answer "should" be and write that instead. If a digit is unclear, give your best reading, set confidence to "needs_verification", and say which digit is unclear.

8. **Check the copying.** For every problem record `problem_as_written`: for a sum, the two numbers the child wrote or put in the grid, as "a + b"; for a story problem, the equation the child wrote. Set `copied_correctly` to false if those numbers are not the numbers of the printed or board problem (for example the child wrote 25 + 35 for 25 + 45, or 53 for 35); true if they match; null if you cannot tell or the child wrote only an answer. A child who copied the problem wrongly but added correctly has NOT made an addition mistake: record the answer as written and do NOT diagnose a misconception from that problem.

9. **Output JSON only.** No preamble, no markdown fences."""


# ============================================================================
# USER PROMPT — built per batch of photographs
# ============================================================================

def build_vision_prompt(
    worksheet_level: str,       # 'beginner', 'progressor', 'proficient'
    competency_id: str,
    competency_name_hi: str,
    problems: list[dict],       # [{"number": 1, "problem_hi": "...", "answer": "..."}]
    misconceptions: list[dict], # From L1 taxonomy
    group_roll_numbers: list[int],
    photo_count: int = 1,
    required_count: Optional[int] = None,   # children must do problems 1..N; the rest are extras
    domain_id: str = "numeracy",            # 'r1_literacy' adds the rules for judging Hindi text answers
) -> str:
    """Build the user prompt that accompanies the worksheet photograph(s)."""
    
    # Hindi text answers need rules that digits never did
    literacy_block = ""
    if domain_id == "r1_literacy":
        literacy_block = (
            "## HINDI TEXT ANSWERS (this is a literacy worksheet)\n\n"
            "- extracted_answer: copy EXACTLY what the child wrote in Devanagari, including spelling and matra mistakes. Do not correct or complete it.\n"
            "- Judge MEANING, not exact wording. is_correct is true when the child's answer states the same fact as the answer key. Accept a different "
            "but correct wording, extra correct detail, a different order of listed items, and spelling or matra slips that do not change which word is meant.\n"
            "- is_correct is false when the key fact is missing or wrong, or when the child only copied a sentence that does not answer the question.\n"
            "- If the key offers alternatives (separated by / or ; or marked कोई एक), any one is enough. If the question asks for two or more items, all "
            "of them must be present: when only some are, set is_correct false and add \"partially_correct\": true to that problem.\n"
            "- Neat handwriting is not a criterion. If you cannot read an answer, set confidence to needs_verification and is_correct to null.\n"
            "- Do NOT diagnose reading or decoding misconceptions (for example a child who reads accurately but cannot answer) from written answers: "
            "they need oral reading evidence. Set diagnosed_misconception only for an error pattern visible in the writing itself, otherwise null.\n"
            "- carry_written does not apply: set it to null.\n\n"
        )

    # Build answer key
    answer_key = {str(p['number']): p['answer'] for p in problems}
    
    # Build misconception reference
    misc_ref = []
    for m in misconceptions:
        misc_ref.append({
            "id": m['id'] if isinstance(m, dict) else m.id,
            "name": m.get('name_en', '') if isinstance(m, dict) else m.name_en,
            "error_pattern": m.get('error_pattern', '') if isinstance(m, dict) else m.error_pattern,
            "diagnostic_indicator": m.get('diagnostic_indicator', '') if isinstance(m, dict) else m.diagnostic_indicator,
            "example_incorrect": m.get('example_incorrect', '') if isinstance(m, dict) else m.example_incorrect,
        })
    
    # Build diagnostic map (which problems reveal which misconceptions)
    diagnostic_map = {}
    for p in problems:
        if p.get('diagnostic_for_misconception'):
            diagnostic_map[str(p['number'])] = p['diagnostic_for_misconception']
    
    scope_text = ""
    if required_count and required_count < len(problems):
        scope_text = f"""
## WHICH PROBLEMS COUNT
Children were told to solve problems 1-{required_count}. Problems {required_count + 1}-{len(problems)} are OPTIONAL EXTRAS for fast finishers.
- A BLANK extra problem is NOT an error. Leave it out of `problems`, or mark it `"attempted": false`. Never count it as incorrect.
- An extra the child DID attempt counts normally, right or wrong.
- A blank REQUIRED problem counts as not correct. Do not diagnose a misconception from a blank answer.
- `total_problems` = {required_count} + the number of extras the child attempted. `correct` counts only attempted problems. `accuracy` = correct / total_problems.
"""

    prompt = f"""Analyse the attached photograph(s) of completed worksheets.

## WORKSHEET CONTEXT

**Level:** {worksheet_level} ({'शुरुआती' if worksheet_level == 'beginner' else 'प्रगतिशील' if worksheet_level == 'progressor' else 'दक्ष'})
**Competency:** {competency_id} — {competency_name_hi}
**Expected roll numbers in this group:** {group_roll_numbers}
**Photos:** {photo_count} image(s) — may contain multiple worksheets per photo

## ANSWER KEY
```json
{json.dumps(answer_key, ensure_ascii=False, indent=2)}
```

## MISCONCEPTION TAXONOMY (classify errors against ONLY these categories)
```json
{json.dumps(misc_ref, ensure_ascii=False, indent=2)}
```

## DIAGNOSTIC PROBLEM MAP (which problems are designed to reveal which misconceptions)
```json
{json.dumps(diagnostic_map, ensure_ascii=False, indent=2)}
```

{scope_text}
{literacy_block}## INSTRUCTIONS

For each worksheet visible in the photo(s):

1. **Identify** the roll number written at the top
2. **Extract** the answer for each problem exactly as written (read it, never reconstruct it), and record `problem_as_written` and `copied_correctly`
3. **Compare** to the answer key
4. **Diagnose** any errors using the misconception taxonomy above
5. **Classify** overall performance as A/PA/NA (give your best estimate; the system recomputes the final status in code from your per-problem results and the competency's own criteria)

## OUTPUT FORMAT

Return a JSON array, one entry per child worksheet found:

```json
[
  {{
    "roll_number": 7,
    "roll_number_confidence": "high",
    "problems": [
      {{
        "number": 1,
        "extracted_answer": "62",
        "problem_as_written": "19 + 43",
        "copied_correctly": true,
        "correct_answer": "62",
        "is_correct": true,
        "carry_written": true,
        "confidence": "high"
      }},
      {{
        "number": 2,
        "extracted_answer": "52",
        "problem_as_written": "19 + 43",
        "copied_correctly": true,
        "correct_answer": "62",
        "is_correct": false,
        "carry_written": false,
        "confidence": "high",
        "diagnosed_misconception": "N2.3.2-M1",
        "diagnosis_reasoning": "Answer is exactly 10 less than correct (52 vs 62), consistent with dropping the carry from ones to tens"
      }}
    ],
    "summary": {{
      "total_problems": 8,
      "correct": 5,
      "incorrect": 3,
      "accuracy": 0.625,
      "overall_status": "partially_achieved",
      "detected_misconceptions": [
        {{
          "misconception_id": "N2.3.2-M1",
          "occurrences": 2,
          "confidence": "high",
          "evidence_problems": [2, 5]
        }}
      ],
      "needs_verification": []
    }}
  }}
]
```

IMPORTANT:
- If a roll number is not in the expected list {group_roll_numbers}, still analyse it but flag: "unexpected_roll_number": true
- If handwriting is truly illegible for a problem, output: "extracted_answer": null, "confidence": "unclear"
- Diagnose misconceptions ONLY from the provided taxonomy — do not create new categories
- A misconception requires 2+ consistent instances OR 1 instance on a diagnostic problem (from the diagnostic map)
- "carry_written" (addition problems only, and only when the ones digits add to 10 or more): true if a small carry digit (usually 1) is visible above the tens column or in the carry cell, false if it is clearly absent, null if the problem has no carry or you cannot tell. It is supporting evidence only and NEVER changes is_correct. An answer exactly 10 less than correct with carry_written false supports the dropped-carry misconception; the same answer with a carry digit written is more likely an addition slip, so lower the confidence and say so in diagnosis_reasoning.
"""
    return prompt


def rescore(child_result: dict, required_count: Optional[int]) -> dict:
    """
    Recompute correct / total_problems / accuracy from the per-problem entries, so that a
    miscount by the model cannot distort the score when only the first N problems are required.
    Total = N + the extras the child actually attempted. A required problem the model left
    out counts as not correct. A problem the child COPIED DIFFERENTLY (copy_error) is not scored
    at all: the child did not attempt the printed problem, so it is neither right nor wrong.
    Without a required_count the model's own summary is kept.
    """
    summary = dict(child_result.get("summary") or {})
    probs = child_result.get("problems") or []
    if not required_count or not probs:
        return summary

    def blank(p):
        a = p.get("extracted_answer")
        return p.get("attempted") is False or a is None or str(a).strip() == ""

    correct, extras_attempted, excluded_required, copy_excluded = 0, 0, 0, 0
    for p in probs:
        n = p.get("number")
        is_required = isinstance(n, int) and n <= required_count
        if p.get("copy_error") is True and not blank(p):
            copy_excluded += 1
            if is_required:
                excluded_required += 1
            continue
        if not is_required and blank(p):
            continue                                  # skipped extra: not an error
        if not is_required:
            extras_attempted += 1
        if p.get("is_correct") is True and not blank(p):
            correct += 1
    total = required_count - excluded_required + extras_attempted
    summary.update(correct=correct, total_problems=total, incorrect=max(total - correct, 0), copy_excluded=copy_excluded,
                   accuracy=round(correct / total, 3) if total > 0 else None)
    return summary


_PLAIN_SUM = re.compile(r"^\s*(\d+)\s*\+\s*(\d+)\s*(?:=\s*_*)?\s*$")
_ANY_SUM = re.compile(r"(\d+)\s*[+\uff0b]\s*(\d+)")


def apply_copy_checks(child_result: dict, key_problems: Optional[list]) -> list:
    """
    The AI reports the numbers the child wrote (problem_as_written); the CODE decides whether they match the printed problem,
    and only for plain sums (a story problem's equation is what the child is being assessed on, so it is never a copy error).
    Marks each problem copy_error True/False, and says whether the child's answer is right for the problem as copied.
    Returns the list of copy errors for the teacher.
    """
    keys = {}
    for kp in key_problems or []:
        m = _PLAIN_SUM.match(str(kp.get("problem_hi") or ""))
        if m:
            keys[kp.get("number")] = (int(m.group(1)), int(m.group(2)))
    found = []
    for p in child_result.get("problems") or []:
        n = p.get("number")
        p["copy_error"] = False
        ans = str(p.get("extracted_answer") or "").replace(",", "").strip()
        if n not in keys or not ans:
            continue
        written = str(p.get("problem_as_written") or "")
        w = _ANY_SUM.search(written)
        if w:
            ops = (int(w.group(1)), int(w.group(2)))
            if sorted(ops) != sorted(keys[n]):
                p["copy_error"] = True
                p["correct_for_written"] = (int(ans) == sum(ops)) if ans.isdigit() else None
                found.append({"problem": n, "written": f"{ops[0]} + {ops[1]}", "answer": ans, "correct_for_written": p["correct_for_written"]})
        elif p.get("copied_correctly") is False:           # the AI says so but gave no numbers: trust it, but say we could not check
            p["copy_error"] = True
            p["correct_for_written"] = None
            found.append({"problem": n, "written": written or None, "answer": ans, "correct_for_written": None})
    return found


def recompute_misconceptions(child_result: dict) -> list:
    """
    Mistake patterns are counted from the per-problem diagnoses, WITHOUT the problems the child copied differently, so a
    copying slip can never become a misconception. Falls back to the model's own list when it gave no per-problem diagnoses.
    """
    probs = child_result.get("problems") or []
    copied = {p.get("number") for p in probs if p.get("copy_error") is True}
    if any(p.get("diagnosed_misconception") for p in probs):
        agg = {}
        for p in probs:
            mid = p.get("diagnosed_misconception")
            if not mid or p.get("copy_error") is True:
                continue
            a = agg.setdefault(mid, {"misconception_id": mid, "occurrences": 0, "evidence_problems": [], "_hi": False})
            a["occurrences"] += 1
            a["evidence_problems"].append(p.get("number"))
            a["_hi"] = a["_hi"] or p.get("confidence") == "high"
        return [{"misconception_id": a["misconception_id"], "occurrences": a["occurrences"], "confidence": "high" if a["_hi"] else "medium",
                 "evidence_problems": a["evidence_problems"]} for a in sorted(agg.values(), key=lambda a: -a["occurrences"])]
    out = []
    for m in (child_result.get("summary") or {}).get("detected_misconceptions") or []:
        ev = [n for n in (m.get("evidence_problems") or []) if n not in copied]
        occ = len(ev) if m.get("evidence_problems") else m.get("occurrences", 1)
        if occ > 0:
            out.append({**m, "occurrences": occ, **({"evidence_problems": ev} if m.get("evidence_problems") else {})})
    return out


def _needs_check(child_result: dict) -> list:
    flagged = set((child_result.get("summary") or {}).get("needs_verification") or [])
    flagged |= {p.get("number") for p in child_result.get("problems") or [] if p.get("confidence") in ("needs_verification", "low")}
    return sorted(n for n in flagged if isinstance(n, int))


def _dedupe_batch(entries: list):
    """Two photos of the same child in one batch: keep the clearer one (more answers read, fewer flagged), and say so."""
    def roll_of(e):
        try:
            return int(e.get("roll_number"))
        except (TypeError, ValueError):
            return None

    def quality(e):
        answered = sum(1 for p in e.get("problems") or [] if str(p.get("extracted_answer") or "").strip())
        return (answered, -len((e.get("summary") or {}).get("needs_verification") or []))

    best, order, dups = {}, [], []
    for e in entries:
        r = roll_of(e)
        if r is None:
            order.append(("x", e))
        elif r not in best:
            best[r] = e
            order.append(("r", r))
        else:
            if r not in dups:
                dups.append(r)
            if quality(e) > quality(best[r]):
                best[r] = e
    return [best[k] if t == "r" else k for t, k in order], dups


def derive_status(summary: dict, criteria, detected: list) -> Optional[str]:
    """
    Decide achieved / partially_achieved / not_achieved IN CODE from the competency's own criteria
    (competencies.apna_criteria), using the rescored accuracy. Returns None when the criteria or the
    accuracy are unavailable, so the caller can fall back to the model's own label.
      achieved           accuracy >= min_accuracy, and no persistent misconception (2+ occurrences) if required
      not_achieved       accuracy <= max_accuracy
      partially_achieved everything in between, or a persistent misconception on a high score
    """
    if isinstance(criteria, str):
        try:
            criteria = json.loads(criteria)
        except json.JSONDecodeError:
            return None
    if not isinstance(criteria, dict):
        return None
    achieved, not_achieved = criteria.get("achieved") or {}, criteria.get("not_achieved") or {}
    lo, hi, acc = achieved.get("min_accuracy"), not_achieved.get("max_accuracy"), summary.get("accuracy")
    if lo is None or hi is None or acc is None:
        return None
    persistent = any((m.get("occurrences") or 1) >= 2 for m in (detected or []))
    if acc >= lo and not (achieved.get("no_persistent_misconception") and persistent):
        return "achieved"
    if acc <= hi:
        return "not_achieved"
    return "partially_achieved"


# ============================================================================
# RESPONSE PROCESSOR — turns Vision output into DB updates
# ============================================================================

async def process_vision_results(
    db,
    teacher_id: str,
    session_date,   # date, or an ISO 'YYYY-MM-DD' string
    competency_id: str,
    vision_response: list[dict],
    teacher_pre_judgment: str,  # 'advance', 'reteach', 'not_sure'
    required_count: Optional[int] = None,
    problems: Optional[list] = None,        # the worksheet's problems, so copying can be checked in code
    on_duplicate: str = "skip",             # a child already analysed today: 'skip' keeps the earlier result, 'replace' overwrites
    replace_rolls: Optional[list] = None,   # ...or only these roll numbers are overwritten
    expected_rolls: Optional[list] = None,  # the group's roll numbers, to flag a sheet from another group
) -> dict:
    """
    Takes Claude Vision's structured output and:
    1. Keeps the clearer photo when a child appears twice in one batch
    2. Checks copying in code, and leaves copied-differently problems out of the score and the mistake patterns
    3. Stores each child's evidence in assessment_evidence, unless the child was already analysed today
    4. Updates child_competency_status (A/PA/NA + consecutive days)
    5. Checks for discrepancy with teacher's pre-judgment
    6. Returns summary for the Review screen
    """

    # the database needs a real date (the caller used to pass text, which crashed on the first insert)
    if isinstance(session_date, str):
        session_date = date.fromisoformat(session_date)
    replace_rolls = {int(r) for r in (replace_rolls or [])}
    expected = {int(r) for r in (expected_rolls or [])}

    entries, dup_in_batch = _dedupe_batch(vision_response)
    results_summary = {
        "children_analysed": 0,
        "misconceptions_detected": [],
        "discrepancy": None,
        "ai_recommendation": None,
        "per_child": [],
        "skipped_duplicates": [],
        "duplicates_in_batch": dup_in_batch,
        "unknown_rolls": [],
        "outside_group_rolls": [],
        "not_assessed": [],
        "unreadable_sheets": 0,
        "copy_errors_excluded": 0,
    }

    group_correct_total = 0
    group_problem_total = 0
    misconception_counts = {}
    criteria = await db.fetchval("SELECT apna_criteria FROM competencies WHERE id = $1", competency_id)

    for child_result in entries:
        try:
            roll = int(child_result.get('roll_number'))
        except (TypeError, ValueError):
            results_summary["unreadable_sheets"] += 1          # 'unclear': the teacher must say whose sheet it is
            continue
        if not roll:
            continue

        # Look up child by roll number
        child = await db.fetchrow("""
            SELECT id FROM children
            WHERE teacher_id = $1 AND roll_number = $2 AND is_active = TRUE
        """, teacher_id, roll)
        if not child:
            results_summary["unknown_rolls"].append(roll)       # not in this class: never counted in the group's score
            continue
        child_id = child['id']

        # A child already analysed today is not analysed twice, unless the teacher says to replace
        existing = await db.fetchrow("""
            SELECT evidence_data, created_at FROM assessment_evidence
            WHERE child_id = $1 AND competency_id = $2 AND session_date = $3 AND channel = 'written_photo'
            ORDER BY created_at DESC LIMIT 1
        """, child_id, competency_id, session_date)
        if existing and on_duplicate != "replace" and roll not in replace_rolls:
            ed = existing['evidence_data']
            ed = json.loads(ed) if isinstance(ed, str) else (ed or {})
            results_summary["skipped_duplicates"].append({
                "roll_number": roll,
                "earlier_accuracy": (ed.get("scoring") or {}).get("accuracy"),
                "earlier_at": existing['created_at'].isoformat(),
            })
            continue

        copy_errors = apply_copy_checks(child_result, problems)
        summary = rescore(child_result, required_count)
        detected = recompute_misconceptions(child_result)
        summary["detected_misconceptions"] = detected
        needs_check = _needs_check(child_result)
        results_summary["copy_errors_excluded"] += len(copy_errors)
        if roll not in expected and expected:
            results_summary["outside_group_rolls"].append(roll)

        # nothing left to score: every problem was copied differently or left blank
        if required_count and summary.get('total_problems') == 0:
            results_summary["not_assessed"].append(roll)
            results_summary['per_child'].append({"roll_number": roll, "accuracy": None, "status": "not_assessed", "misconceptions": [],
                                                 "assessed_problems": 0, "copy_errors": copy_errors, "needs_check": needs_check})
            continue

        accuracy = summary.get('accuracy', 0)
        model_status = summary.get('overall_status', 'not_achieved')
        status = derive_status(summary, criteria, detected) or model_status

        group_correct_total += summary.get('correct', 0)
        group_problem_total += summary.get('total_problems', 0)

        # Track misconceptions across the group
        for m in detected:
            mid = m['misconception_id']
            misconception_counts[mid] = misconception_counts.get(mid, 0) + m.get('occurrences', 1)

        # A second run on the same date replaces that day's result instead of adding a day
        await db.execute("""
            DELETE FROM assessment_evidence
            WHERE child_id = $1 AND competency_id = $2 AND session_date = $3 AND channel = 'written_photo'
        """, child_id, competency_id, session_date)

        # Store evidence
        await db.execute("""
            INSERT INTO assessment_evidence
                (child_id, competency_id, teacher_id, channel, status,
                 evidence_data, detected_misconception_ids, confidence,
                 session_date, assessment_tier, teacher_pre_judgment)
            VALUES ($1, $2, $3, 'written_photo', $4, $5, $6, $7, $8, 'daily', $9)
        """,
            child_id, competency_id, teacher_id, status,
            json.dumps({**child_result, "summary": summary, "copy_errors": copy_errors,
                        "scoring": {"accuracy": accuracy, "status": status, "model_status": model_status}}, ensure_ascii=False),
            [m['misconception_id'] for m in detected] or None,
            'high' if all(p.get('confidence') == 'high' for p in child_result.get('problems', [])) else 'medium',
            session_date, teacher_pre_judgment
        )

        # Update child_competency_status
        existing_status = await db.fetchrow("""
            SELECT status, consecutive_days_at_status, last_assessment_date
            FROM child_competency_status
            WHERE child_id = $1 AND competency_id = $2
        """, child_id, competency_id)

        # "consecutive days" counts days, not runs: a re-run on the same date keeps the streak
        same_day = bool(existing_status and existing_status['last_assessment_date'] == session_date)
        if existing_status and existing_status['status'] == status:
            new_consecutive = existing_status['consecutive_days_at_status'] + (0 if same_day else 1)
        else:
            new_consecutive = 1
        count_increment = 0 if same_day else 1

        await db.execute("""
            INSERT INTO child_competency_status
                (child_id, competency_id, status, assessment_count,
                 last_assessment_date, consecutive_days_at_status,
                 confidence, active_misconception_ids)
            VALUES ($1, $2, $3, 1, $4, $5, 'high', $6)
            ON CONFLICT (child_id, competency_id) DO UPDATE SET
                status = $3,
                assessment_count = child_competency_status.assessment_count + $7,
                last_assessment_date = $4,
                consecutive_days_at_status = $5,
                confidence = 'high',
                active_misconception_ids = $6,
                updated_at = NOW()
        """,
            child_id, competency_id, status, session_date,
            new_consecutive,
            [m['misconception_id'] for m in detected] or None,
            count_increment
        )

        results_summary['per_child'].append({
            "roll_number": roll,
            "accuracy": accuracy,
            "status": status,
            "misconceptions": [m['misconception_id'] for m in detected],
            "assessed_problems": summary.get('total_problems'),
            "copy_errors": copy_errors,
            "needs_check": needs_check,
        })

    results_summary["children_analysed"] = len(results_summary["per_child"])

    # Group-level analysis
    group_accuracy = group_correct_total / max(group_problem_total, 1)

    # AI recommendation
    if group_accuracy >= 0.80 and not misconception_counts:
        ai_rec = "advance"
    elif group_accuracy < 0.50 or any(c >= 3 for c in misconception_counts.values()):
        ai_rec = "reteach"
    else:
        ai_rec = "advance"  # borderline — lean toward advancing

    results_summary['ai_recommendation'] = ai_rec
    results_summary['group_accuracy'] = round(group_accuracy, 2)
    results_summary['misconceptions_detected'] = [
        {"id": mid, "total_occurrences": count}
        for mid, count in sorted(misconception_counts.items(), key=lambda x: -x[1])
    ]

    # Discrepancy check
    if teacher_pre_judgment and teacher_pre_judgment != 'not_sure' and teacher_pre_judgment != ai_rec:
        results_summary['discrepancy'] = {
            "teacher_said": teacher_pre_judgment,
            "ai_says": ai_rec,
            "reason": _explain_discrepancy(teacher_pre_judgment, ai_rec, group_accuracy, misconception_counts)
        }

    return results_summary


def _explain_discrepancy(teacher: str, ai: str, accuracy: float, misconceptions: dict) -> str:
    """Generate a Hindi explanation for the teacher when AI and teacher disagree."""
    
    if teacher == "advance" and ai == "reteach":
        top_misc = max(misconceptions, key=misconceptions.get) if misconceptions else "unknown"
        return (
            f"आपने आगे बढ़ने को कहा, लेकिन {int(accuracy*100)}% शुद्धता और "
            f"बार-बार दिखने वाली गलती ({top_misc}) से लगता है कि दोहराना बेहतर होगा। "
            f"क्या आप पुनर्विचार करना चाहेंगे?"
        )
    elif teacher == "reteach" and ai == "advance":
        return (
            f"आपने दोहराने को कहा, लेकिन {int(accuracy*100)}% शुद्धता अच्छी है और "
            f"कोई बार-बार की गलती नहीं दिखी। आपने कक्षा में जो देखा वह 20 बच्चों पर आधारित है — "
            f"आपका अनुभव मायने रखता है।"
        )
    return ""


# ============================================================================
# LEVEL CHANGE DETECTION — checks the 3+ day rule
# ============================================================================

# ── "consider re-assessing" flags ───────────────────────────────────────────
# A child's level (Beginner / Progressor / Proficient) changes ONLY through an assessment: the baseline, a periodic round, or an
# on-demand re-assessment of one child. Never from daily results: those are sampled, thin, and gathered right after teaching, so they
# cannot re-grade a child. What they CAN do is tell the teacher whose daily work no longer matches their level, so she knows whom to
# re-assess first. That is all a flag is: it changes nothing and has no Accept button. (docs/LEVELS.md)
#
# A flag needs, from the skills that defined the child's group on each day (different skills on different days are fine):
#   * at least 3 qualifying days among the child's last 4, the newest within 14 days;
#   * a qualifying written sheet has at least 5 assessable problems (problems copied differently are not counted);
#   * evidence dated AFTER the child's level was last set (the last assessment, or registration);
#   * 3 of 4 (or 3 of 3) 'achieved' -> "doing well, consider re-assessing for a higher group" (Beginner or Progressor);
#     3 of 4 (or 3 of 3) 'not achieved' -> "struggling, consider re-assessing" (Progressor only).
# Proficient children get no flag: their daily skill is the NEW extension, where early struggle is normal and says nothing
# about their level.
FLAG_WINDOW = 4
FLAG_MIN_DAYS = 3
FLAG_SHARE = 0.75
MIN_PROBLEMS_PER_DAY = 5
RECENCY_DAYS = 14
_LEVEL_HI = {"beginner": "शुरुआती", "progressor": "प्रगतिशील", "proficient": "दक्ष"}


def _snapshot_role(snap, roll, competency_id) -> str:
    """Which group's skill was this evidence on, that day? 'beginner' / 'progressor' / 'proficient' (the child's own group),
    'check:<group>' (a child outside that group assessed on its skill), 'other' (a skill nobody's group worked on),
    or 'unknown' when no plan was stored for that date (for example seeded demo data)."""
    if not snap:
        return "unknown"
    for level, g in snap.items():
        if g.get("target") == competency_id:
            return level if roll in (g.get("rolls") or []) else f"check:{level}"
    return "other"


async def check_reassessment_flags(db, teacher_id: str, domain_id: str, today=None) -> list[dict]:
    """Children whose recent daily work does not match their level: worth re-assessing first. Changes nothing."""
    today = today or date.today()
    kids = await db.fetch("""
        SELECT c.id AS child_id, c.roll_number, clp.bpp_level, GREATEST(clp.last_assessed, clp.level_changed_at) AS assessed_at
        FROM children c
        JOIN child_lakshya_positions clp ON clp.child_id = c.id AND clp.domain_id = $2
        WHERE c.teacher_id = $1 AND c.is_active = TRUE AND clp.bpp_level IN ('beginner', 'progressor')
    """, teacher_id, domain_id)
    if not kids:
        return []
    ev = await db.fetch("""
        SELECT e.child_id, e.competency_id, e.session_date, e.channel, e.status, e.evidence_data, e.created_at, comp.name_hi
        FROM assessment_evidence e
        JOIN competencies comp ON comp.id = e.competency_id
        JOIN subdomains sd ON sd.id = comp.subdomain_id AND sd.domain_id = $2     -- evidence counts only for its own subject
        WHERE e.teacher_id = $1 AND e.session_date >= $3
        ORDER BY e.session_date, e.created_at
    """, teacher_id, domain_id, today - timedelta(days=60))
    dates = sorted({r["session_date"] for r in ev})
    snaps = {}
    if dates:
        for r in await db.fetch("SELECT plan_date, groups_snapshot FROM daily_plans WHERE teacher_id = $1 AND domain_id = $2 AND plan_date = ANY($3::date[])",
                                teacher_id, domain_id, dates):
            g = r["groups_snapshot"]
            snaps[r["plan_date"]] = json.loads(g) if isinstance(g, str) else g

    kid = {k["child_id"]: k for k in kids}
    per = {}                                           # child -> {date: day}
    for r in ev:
        k = kid.get(r["child_id"])
        if not k:
            continue
        if k["assessed_at"] and r["session_date"] <= k["assessed_at"].date():
            continue                                   # only evidence AFTER the level was last set counts
        data = r["evidence_data"]
        data = json.loads(data) if isinstance(data, str) else (data or {})
        problems = (data.get("summary") or {}).get("total_problems")
        acc = (data.get("scoring") or {}).get("accuracy")
        if r["channel"] == "written_photo" and isinstance(problems, int) and problems < MIN_PROBLEMS_PER_DAY:
            continue                                   # too little to judge
        # Synthetic demo rows (scripts/demo_progress.py marks them) have no real plan behind them: role unknown, not "other".
        role = "unknown" if data.get("demo_seed") else _snapshot_role(snaps.get(r["session_date"]), k["roll_number"], r["competency_id"])
        if role not in (k["bpp_level"], "unknown"):
            continue                                   # not the skill that defined this child's group that day: no claim about the child
        per.setdefault(r["child_id"], {})[r["session_date"]] = {"date": r["session_date"], "status": r["status"], "accuracy": acc,
                                                                 "competency": r["competency_id"], "name_hi": r["name_hi"]}
    flags = []
    for child_id, by_date in per.items():
        k = kid[child_id]
        days = sorted(by_date.values(), key=lambda d: d["date"], reverse=True)[:FLAG_WINDOW]
        if len(days) < FLAG_MIN_DAYS or (today - days[0]["date"]).days > RECENCY_DAYS:
            continue
        n = len(days)
        achieved = sum(1 for d in days if d["status"] == "achieved")
        missed = sum(1 for d in days if d["status"] == "not_achieved")
        if achieved >= FLAG_MIN_DAYS and achieved / n >= FLAG_SHARE:
            direction, count, word = "higher", achieved, "प्राप्त"
        elif k["bpp_level"] == "progressor" and missed >= FLAG_MIN_DAYS and missed / n >= FLAG_SHARE:
            direction, count, word = "lower", missed, "अप्राप्त"
        else:
            continue
        detail = ", ".join(f"{d['date'].day}/{d['date'].month}: " + (f"{round(d['accuracy'] * 100)}%" if isinstance(d["accuracy"], (int, float)) else
                           {"achieved": "प्राप्त", "partially_achieved": "आंशिक", "not_achieved": "अप्राप्त"}.get(d["status"], d["status"])) for d in reversed(days))
        when = k["assessed_at"].date() if k["assessed_at"] else None
        text = (f"Roll No. {k['roll_number']} — हाल के {n} मूल्यांकन-दिनों में से {count} दिन समूह के कौशल '{word}': {detail}। "
                f"स्तर अभी {_LEVEL_HI[k['bpp_level']]} है" + (f" (आकलन: {when.day}/{when.month})" if when else "") + "। दोबारा आकलन पर विचार करें।")
        flags.append({"roll_number": k["roll_number"], "child_id": str(child_id), "direction": direction, "level": k["bpp_level"],
                      "level_as_of": when.isoformat() if when else None, "days_counted": n, "matching_days": count,
                      "days": [{"date": d["date"].isoformat(), "status": d["status"], "accuracy": d["accuracy"], "competency": d["competency"]} for d in reversed(days)],
                      "evidence_hi": text})
    return sorted(flags, key=lambda f: (0 if f["direction"] == "higher" else 1, f["roll_number"]))
