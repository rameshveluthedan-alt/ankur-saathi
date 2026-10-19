"""
Ankur Saathi — Claude Vision Worksheet Analysis
The feedback half of the daily loop: photograph → extract → diagnose → adapt.

Pipeline: teacher photographs batch of worksheets → memory-safe upload →
Claude Vision extracts answers by roll number → classifies against L1
misconception taxonomy → updates child_competency_status → feeds next
day's orchestration prompt.
"""

import json
from datetime import date
from typing import Optional


# ============================================================================
# SYSTEM PROMPT — constant across all Vision calls
# ============================================================================

VISION_SYSTEM_PROMPT = """You are the Ankur Saathi worksheet analyser. You examine photographs of children's completed Hindi-medium worksheets and extract answers, diagnose misconceptions, and classify performance.

## Rules

1. **Roll numbers only.** Children write their roll number (1-99) on the worksheet, NEVER their name. Refer to each child as "Roll No. X". If you cannot read the roll number, mark it as "unclear" — do not guess.

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

7. **Output JSON only.** No preamble, no markdown fences."""


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
2. **Extract** the answer for each problem
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
        "correct_answer": "62",
        "is_correct": true,
        "carry_written": true,
        "confidence": "high"
      }},
      {{
        "number": 2,
        "extracted_answer": "52",
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
    out counts as not correct. Without a required_count the model's own summary is kept.
    """
    summary = dict(child_result.get("summary") or {})
    probs = child_result.get("problems") or []
    if not required_count or not probs:
        return summary

    def blank(p):
        a = p.get("extracted_answer")
        return p.get("attempted") is False or a is None or str(a).strip() == ""

    correct, extras_attempted = 0, 0
    for p in probs:
        n = p.get("number")
        is_required = isinstance(n, int) and n <= required_count
        if not is_required and blank(p):
            continue                                  # skipped extra: not an error
        if not is_required:
            extras_attempted += 1
        if p.get("is_correct") is True and not blank(p):
            correct += 1
    total = required_count + extras_attempted
    summary.update(correct=correct, total_problems=total, incorrect=total - correct,
                   accuracy=round(correct / total, 3))
    return summary


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
) -> dict:
    """
    Takes Claude Vision's structured output and:
    1. Stores each child's evidence in assessment_evidence
    2. Updates child_competency_status (A/PA/NA + consecutive days)
    3. Checks for discrepancy with teacher's pre-judgment
    4. Returns summary for the Review screen
    """
    
    # the database needs a real date (the caller used to pass text, which crashed on the first insert)
    if isinstance(session_date, str):
        session_date = date.fromisoformat(session_date)

    results_summary = {
        "children_analysed": len(vision_response),
        "misconceptions_detected": [],
        "discrepancy": None,
        "ai_recommendation": None,
        "per_child": []
    }
    
    group_correct_total = 0
    group_problem_total = 0
    misconception_counts = {}
    criteria = await db.fetchval("SELECT apna_criteria FROM competencies WHERE id = $1", competency_id)
    
    for child_result in vision_response:
        roll = child_result.get('roll_number')
        if not roll:
            continue
        
        summary = rescore(child_result, required_count)
        accuracy = summary.get('accuracy', 0)
        model_status = summary.get('overall_status', 'not_achieved')
        detected = summary.get('detected_misconceptions', [])
        status = derive_status(summary, criteria, detected) or model_status
        
        group_correct_total += summary.get('correct', 0)
        group_problem_total += summary.get('total_problems', 0)
        
        # Track misconceptions across the group
        for m in detected:
            mid = m['misconception_id']
            misconception_counts[mid] = misconception_counts.get(mid, 0) + m.get('occurrences', 1)
        
        # Look up child by roll number
        child = await db.fetchrow("""
            SELECT id FROM children 
            WHERE teacher_id = $1 AND roll_number = $2 AND is_active = TRUE
        """, teacher_id, roll)
        
        if not child:
            continue
        
        child_id = child['id']
        
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
            json.dumps({**child_result, "scoring": {"accuracy": accuracy, "status": status, "model_status": model_status}}, ensure_ascii=False),
            [m['misconception_id'] for m in detected] or None,
            'high' if all(p.get('confidence') == 'high' for p in child_result.get('problems', [])) else 'medium',
            session_date, teacher_pre_judgment
        )
        
        # Update child_competency_status
        existing = await db.fetchrow("""
            SELECT status, consecutive_days_at_status, last_assessment_date
            FROM child_competency_status
            WHERE child_id = $1 AND competency_id = $2
        """, child_id, competency_id)

        # "consecutive days" counts days, not runs: a re-run on the same date keeps the streak
        same_day = bool(existing and existing['last_assessment_date'] == session_date)
        if existing and existing['status'] == status:
            new_consecutive = existing['consecutive_days_at_status'] + (0 if same_day else 1)
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
            "misconceptions": [m['misconception_id'] for m in detected]
        })
    
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

async def check_level_changes(db, teacher_id: str, domain_id: str) -> list[dict]:
    """
    Checks for children who meet the level change criteria:
    - 3+ consecutive days of Achieved → recommend Beginner→Progressor or Progressor→Proficient
    - 3+ consecutive days of Not Achieved → recommend downward movement
    
    Returns recommendations for teacher approval.
    """
    
    candidates = await db.fetch("""
        SELECT cs.child_id, c.roll_number, cs.competency_id, cs.status,
               cs.consecutive_days_at_status, cs.active_misconception_ids,
               clp.bpp_level as current_bpp,
               comp.name_hi as competency_name_hi, comp.grade_level
        FROM child_competency_status cs
        JOIN children c ON cs.child_id = c.id
        JOIN child_lakshya_positions clp ON clp.child_id = c.id AND clp.domain_id = $2
        JOIN competencies comp ON cs.competency_id = comp.id
        JOIN subdomains sd ON sd.id = comp.subdomain_id AND sd.domain_id = $2   -- evidence counts only for its own subject
        WHERE c.teacher_id = $1
          AND cs.consecutive_days_at_status >= 3
          AND c.is_active = TRUE
        ORDER BY cs.consecutive_days_at_status DESC
    """, teacher_id, domain_id)
    
    # teacher-facing Hindi: level names and the names of the active mistakes, not codes
    level_hi = {"beginner": "शुरुआती", "progressor": "प्रगतिशील", "proficient": "दक्ष"}
    active_ids = sorted({m for cand in candidates for m in (cand['active_misconception_ids'] or [])})
    mis_hi = {r['id']: r['name_hi'] for r in await db.fetch(
        "SELECT id, name_hi FROM misconceptions WHERE id = ANY($1::text[])", active_ids)} if active_ids else {}

    recommendations = []
    for cand in candidates:
        if cand['status'] == 'achieved' and cand['current_bpp'] != 'proficient':
            # Upward movement
            new_bpp = 'progressor' if cand['current_bpp'] == 'beginner' else 'proficient'
            recommendations.append({
                "roll_number": cand['roll_number'],
                "child_id": str(cand['child_id']),
                "direction": "up",
                "from_level": cand['current_bpp'],
                "to_level": new_bpp,
                "competency": cand['competency_id'],
                "competency_name_hi": cand['competency_name_hi'],
                "consecutive_days": cand['consecutive_days_at_status'],
                "evidence_hi": (
                    f"Roll No. {cand['roll_number']} — {cand['consecutive_days_at_status']} दिनों से "
                    f"लगातार 'प्राप्त' ({cand['competency_name_hi']})। "
                    f"सुझाव: {level_hi[cand['current_bpp']]} → {level_hi[new_bpp]}"
                )
            })
        
        elif cand['status'] == 'not_achieved' and cand['current_bpp'] != 'beginner':
            # Downward movement
            new_bpp = 'progressor' if cand['current_bpp'] == 'proficient' else 'beginner'
            misc_text = ""
            if cand['active_misconception_ids']:
                misc_text = " सक्रिय गलती: " + ", ".join(mis_hi.get(m, m) for m in cand['active_misconception_ids'])
            recommendations.append({
                "roll_number": cand['roll_number'],
                "child_id": str(cand['child_id']),
                "direction": "down",
                "from_level": cand['current_bpp'],
                "to_level": new_bpp,
                "competency": cand['competency_id'],
                "competency_name_hi": cand['competency_name_hi'],
                "consecutive_days": cand['consecutive_days_at_status'],
                "evidence_hi": (
                    f"Roll No. {cand['roll_number']} — {cand['consecutive_days_at_status']} दिनों से "
                    f"लगातार 'अप्राप्त' ({cand['competency_name_hi']})।{misc_text} "
                    f"सुझाव: {level_hi[cand['current_bpp']]} → {level_hi[new_bpp]}"
                )
            })
    
    return recommendations
