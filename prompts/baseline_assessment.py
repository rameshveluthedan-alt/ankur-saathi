"""
Ankur Saathi — Baseline Assessment Generator
Generates a graded diagnostic assessment from the L1 competency tree.

Two modes:
  1. FULL BASELINE (start of year / periodic): Tests across the complete
     Balvatika→Grade 3 ladder to place every child on the progression.
  2. ON-DEMAND DIAGNOSTIC: Focused assessment for one child showing anomalies.

The baseline uses ALL THREE assessment channels:
  - Written: worksheet items (photo capture → Claude Vision)
  - Observed: teacher taps A/PA/NA in real-time (oral competencies)
  - Oral reading: teacher stopwatch + manual entry (fluency competencies)
"""

import json
from dataclasses import dataclass


# ============================================================================
# BASELINE ITEM GENERATION — queries L1 to build the diagnostic
# ============================================================================

async def generate_baseline_items(db, domain_id: str, grade_levels: list[str]) -> dict:
    """
    Generates a structured baseline assessment by querying L1 competencies.
    
    Returns items grouped by assessment channel, ordered from lowest
    to highest on the progression ladder (so the teacher can stop
    when the child starts failing consistently — adaptive ceiling).
    """
    
    # Get all competencies for this domain, ordered by progression
    competencies = await db.fetch("""
        SELECT c.id, c.name_en, c.name_hi, c.grade_level, 
               c.assessment_modality, c.apna_criteria, c.number_range,
               c.problem_types, c.sort_order,
               s.name_hi as subdomain_name_hi
        FROM competencies c
        JOIN subdomains s ON c.subdomain_id = s.id
        WHERE s.domain_id = $1
          AND c.is_active = TRUE
          AND c.grade_level = ANY($2)
        ORDER BY 
            CASE c.grade_level 
                WHEN 'balvatika' THEN 0 WHEN 'grade_1' THEN 1 
                WHEN 'grade_2' THEN 2 WHEN 'grade_3' THEN 3 
            END,
            s.sort_order, c.sort_order
    """, domain_id, grade_levels)
    
    # Group by assessment channel
    written_items = []
    observed_items = []
    oral_reading_items = []
    
    for comp in competencies:
        item = {
            "competency_id": comp['id'],
            "competency_name_hi": comp['name_hi'],
            "competency_name_en": comp['name_en'],
            "grade_level": comp['grade_level'],
            "subdomain_hi": comp['subdomain_name_hi'],
            "assessment_modality": comp['assessment_modality'],
            "apna_criteria": comp['apna_criteria'],
            "number_range": comp['number_range'],
        }
        
        if comp['assessment_modality'] == 'written':
            item["channel"] = "written_photo"
            item["item_type"] = "worksheet_problems"
            item["num_problems"] = 3  # 3 problems per competency for baseline (not full 8-10)
            item["instruction_hi"] = _generate_written_instruction(comp)
            written_items.append(item)
            
        elif comp['assessment_modality'] == 'observed':
            item["channel"] = "observed"
            item["item_type"] = "teacher_observation"
            item["observation_prompt_hi"] = _generate_observation_prompt(comp)
            item["response_options"] = ["achieved", "partially_achieved", "not_achieved"]
            observed_items.append(item)
            
        elif comp['assessment_modality'] == 'oral_reading':
            item["channel"] = "oral_reading"
            item["item_type"] = "reading_fluency"
            item["instruction_hi"] = _generate_orf_instruction(comp)
            oral_reading_items.append(item)
    
    return {
        "assessment_type": "baseline",
        "domain": domain_id,
        "grade_levels": grade_levels,
        "total_competencies": len(competencies),
        "channels": {
            "observed": {
                "description": "Teacher observes and taps A/PA/NA in real-time. Do these FIRST — fastest channel.",
                "items": observed_items,
                "estimated_minutes": len(observed_items) * 1  # ~1 min per observed item per child
            },
            "written_photo": {
                "description": "Worksheet items. Print/board-copy, children complete, teacher photographs.",
                "items": written_items,
                "estimated_minutes": len(written_items) * 2  # ~2 min per written competency
            },
            "oral_reading": {
                "description": "Teacher stopwatch + manual entry. One child at a time.",
                "items": oral_reading_items,
                "estimated_minutes": len(oral_reading_items) * 3  # ~3 min per child per passage
            }
        },
        "administration_sequence": [
            "1. Observed items first (can be done during any class activity)",
            "2. Written worksheet items (whole class, 15-20 min)",
            "3. Oral reading (individual, during independent work time)"
        ],
        "adaptive_ceiling_rule": "If a child scores Not Achieved on 3 consecutive competencies at a grade level, stop that channel for that child at that level. Their position is at the last Achieved/PA competency."
    }


def _generate_written_instruction(comp: dict) -> str:
    """Generate Hindi instruction text for a written baseline item."""
    grade_labels = {'balvatika': 'बालवाटिका', 'grade_1': 'कक्षा 1', 'grade_2': 'कक्षा 2', 'grade_3': 'कक्षा 3'}
    grade = grade_labels.get(comp['grade_level'], '')
    return f"({grade}) {comp['name_hi']} — 3 सवाल हल करो।"


def _generate_observation_prompt(comp: dict) -> str:
    """Generate Hindi observation prompt for the teacher."""
    criteria = comp['apna_criteria']
    if isinstance(criteria, str):
        criteria = json.loads(criteria)
    
    achieved_desc = criteria.get('achieved', {}).get('description', '')
    na_desc = criteria.get('not_achieved', {}).get('description', '')
    
    return (
        f"बच्चे से करवाएँ: {comp['name_hi']}\n"
        f"✓ प्राप्त: {achieved_desc}\n"
        f"✗ अप्राप्त: {na_desc}"
    )


def _generate_orf_instruction(comp: dict) -> str:
    """Generate Hindi instruction for oral reading fluency assessment."""
    criteria = comp['apna_criteria']
    if isinstance(criteria, str):
        criteria = json.loads(criteria)
    
    min_cwpm = criteria.get('achieved', {}).get('min_cwpm', 'N/A')
    return (
        f"{comp['name_hi']}\n"
        f"बच्चे को अनुच्छेद पढ़ने दें। स्टॉपवॉच शुरू करें।\n"
        f"1 मिनट बाद रोकें। सही शब्द गिनें।\n"
        f"लक्ष्य CWPM: {min_cwpm}"
    )


# ============================================================================
# CLAUDE PROMPT FOR BASELINE WORKSHEET GENERATION
# ============================================================================

BASELINE_WORKSHEET_SYSTEM = """You are the Ankur Saathi baseline assessment generator. You create graded diagnostic worksheets that accurately place children on the NIPUN Bharat Lakshya progression ladder.

Rules:
1. Generate EXACTLY the number of problems specified per competency.
2. Problems must match the number range and type constraints provided.
3. Problems progress in difficulty within each competency section.
4. Visual scaffolding for Balvatika and Grade 1 items (pictures, number lines).
5. Clear structured response grid with roll number field.
6. All text in Hindi.
7. Each problem maps to exactly one competency — no ambiguous items.
8. Include 1 problem per competency designed to reveal the most common misconception."""


def build_baseline_worksheet_prompt(items: list[dict], has_printer: bool) -> str:
    """Build the Claude prompt for generating the baseline worksheet."""
    
    mode = "प्रिंट-रेडी A4 PDF" if has_printer else "बोर्ड-कॉपी (शिक्षक बोर्ड पर लिखें)"
    
    item_specs = []
    for item in items:
        spec = {
            "competency_id": item["competency_id"],
            "name_hi": item["competency_name_hi"],
            "grade_level": item["grade_level"],
            "num_problems": item["num_problems"],
            "number_range": item.get("number_range"),
            "instruction_hi": item["instruction_hi"]
        }
        item_specs.append(spec)
    
    prompt = f"""Generate a baseline diagnostic worksheet for the following competencies.
Format: {mode}

Each section has a competency header and 3 problems. Problems go easy → medium → diagnostic (reveals misconception).

Competencies (in order from lowest to highest on the progression):
```json
{json.dumps(item_specs, ensure_ascii=False, indent=2)}
```

Output format:
```json
{{
  "title_hi": "आधारभूत मूल्यांकन — गणित / साक्षरता",
  "sections": [
    {{
      "competency_id": "...",
      "header_hi": "...",
      "problems": [
        {{
          "number": 1,
          "difficulty": "easy",
          "problem_hi": "...",
          "answer": "...",
          "diagnostic_for_misconception": null
        }},
        {{
          "number": 2,
          "difficulty": "medium", 
          "problem_hi": "...",
          "answer": "...",
          "diagnostic_for_misconception": null
        }},
        {{
          "number": 3,
          "difficulty": "diagnostic",
          "problem_hi": "...",
          "answer": "...",
          "diagnostic_for_misconception": "N2.3.2-M1"
        }}
      ]
    }}
  ],
  "roll_number_field": true,
  "response_grid": true
}}
```"""
    return prompt


# ============================================================================
# PLACEMENT ALGORITHM — maps baseline results to B/P/P positions
# ============================================================================

async def compute_placement(db, child_id: str, domain_id: str, results: list[dict]) -> dict:
    """
    Takes baseline assessment results and computes the child's
    Lakshya position + B/P/P classification.
    
    Args:
        results: list of {"competency_id": str, "status": "A/PA/NA"}
    
    Returns:
        {"current_competency_id": str, "bpp_level": str, "evidence_summary": str}
    """
    
    # Find the highest competency where child has A or PA
    # (ordered by progression — grade level + sort order)
    highest_mastered = None
    a_count = 0
    pa_count = 0
    na_count = 0
    consecutive_na = 0
    
    for r in results:
        if r['status'] == 'achieved':
            highest_mastered = r['competency_id']
            a_count += 1
            consecutive_na = 0
        elif r['status'] == 'partially_achieved':
            highest_mastered = r['competency_id']
            pa_count += 1
            consecutive_na = 0
        else:
            na_count += 1
            consecutive_na += 1
        
        # Adaptive ceiling: stop if 3 consecutive NAs
        if consecutive_na >= 3:
            break
    
    total = a_count + pa_count + na_count
    
    if total == 0:
        return {"current_competency_id": None, "bpp_level": "beginner", 
                "evidence_summary": "No assessment data"}
    
    # B/P/P classification using NIPUN thresholds
    a_pct = a_count / total
    pa_pct = pa_count / total
    
    if a_pct >= 0.75:
        bpp = "proficient"
    elif (a_pct + pa_pct) >= 0.50:
        bpp = "progressor"
    else:
        bpp = "beginner"
    
    # Fall back to first competency if nothing was mastered
    if highest_mastered is None:
        first_comp = await db.fetchval("""
            SELECT c.id FROM competencies c
            JOIN subdomains s ON c.subdomain_id = s.id
            WHERE s.domain_id = $1 AND c.grade_level = 'balvatika'
            ORDER BY s.sort_order, c.sort_order LIMIT 1
        """, domain_id)
        highest_mastered = first_comp
    
    return {
        "current_competency_id": highest_mastered,
        "bpp_level": bpp,
        "evidence_summary": f"A:{a_count} PA:{pa_count} NA:{na_count} ({total} assessed)"
    }


# ============================================================================
# GROUPING ALGORITHM — clusters children into 3 groups from positions
# ============================================================================

async def compute_groups(db, teacher_id: str, domain_id: str) -> list[dict]:
    """
    Reads all children's Lakshya positions for a domain and clusters
    into exactly 3 groups: Beginner, Progressor, Proficient.
    
    Grouping is by B/P/P level, NOT by enrolled grade.
    A Grade 3 child at Grade 1 level joins the Beginner group.
    """
    
    positions = await db.fetch("""
        SELECT c.id as child_id, c.roll_number, c.enrolled_grade,
               clp.current_competency_id, clp.bpp_level
        FROM child_lakshya_positions clp
        JOIN children c ON clp.child_id = c.id
        WHERE c.teacher_id = $1 
          AND clp.domain_id = $2
          AND c.is_active = TRUE
        ORDER BY clp.bpp_level, c.roll_number
    """, teacher_id, domain_id)
    
    groups = {"beginner": [], "progressor": [], "proficient": []}
    for p in positions:
        groups[p['bpp_level']].append({
            "child_id": str(p['child_id']),
            "roll_number": p['roll_number'],
            "enrolled_grade": p['enrolled_grade'],
            "current_competency": p['current_competency_id']
        })
    
    # Determine target competency for each group
    # Beginner: the most common "working on" competency in the group
    # Progressor: the teacher-selected Lakshya (passed at plan time)
    # Proficient: the next competency after the teacher-selected one
    
    result = []
    for level in ['beginner', 'progressor', 'proficient']:
        children = groups[level]
        result.append({
            "group_label": level,
            "child_count": len(children),
            "roll_numbers": [c['roll_number'] for c in children],
            "child_ids": [c['child_id'] for c in children],
            "enrolled_grades": list(set(c['enrolled_grade'] for c in children)),
            "competency_spread": list(set(c['current_competency'] for c in children))
        })
    
    return result
