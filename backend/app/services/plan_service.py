"""
Ankur Saathi — Plan Service
Business logic for competency tree, curriculum week, and Dainik Yojana generation.
Wraps the orchestrate.py pipeline with proper error handling and DB access.
"""

import json
import time
from datetime import date
from typing import Optional

import anthropic

from app.core.config import get_settings
from app.core.database import get_db

# Import the orchestration module (copied from prompts/ into services/ or added to path)
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'prompts'))
from orchestrate import (
    OrchestrationContext, Competency, GroupInfo, Prerequisite,
    Misconception, AnchorTemplate, InterventionTemplate, TLMRef,
    build_system_prompt, build_user_prompt,
    fetch_competency, fetch_prerequisite_chain, fetch_misconceptions,
    fetch_anchor_activity, fetch_intervention, fetch_tlms,
)
from baseline_assessment import compute_groups


async def get_competency_tree(db, domain_id: str) -> list[dict]:
    """Get the full competency tree for the Plan screen's Lakshya selector."""
    rows = await db.fetch("""
        SELECT c.id, c.name_en, c.name_hi, c.grade_level, c.assessment_modality,
               s.name_en as subdomain_name
        FROM competencies c
        JOIN subdomains s ON c.subdomain_id = s.id
        WHERE s.domain_id = $1 AND c.is_active = TRUE
        ORDER BY 
            CASE c.grade_level 
                WHEN 'balvatika' THEN 0 WHEN 'grade_1' THEN 1 
                WHEN 'grade_2' THEN 2 WHEN 'grade_3' THEN 3 
            END,
            s.sort_order, c.sort_order
    """, domain_id)
    return [dict(r) for r in rows]


async def get_curriculum_week(db, state_id: str, grade_level: str, domain_id: str, week_number: int) -> Optional[dict]:
    """Get the curriculum week for the recommended Lakshya highlight."""
    row = await db.fetchrow("""
        SELECT cw.week_number, cw.topic_title_en, cw.topic_title_hi, 
               cw.competency_ids, cw.notes
        FROM curriculum_weeks cw
        JOIN curriculum_plans cp ON cw.plan_id = cp.id
        WHERE cp.state_id = $1 AND cp.is_active = TRUE
          AND cw.grade_level = $2 AND cw.domain_id = $3
          AND cw.week_number = $4
        LIMIT 1
    """, state_id, grade_level, domain_id, week_number)
    return dict(row) if row else None


async def get_current_groups(db, teacher_id: str, domain_id: str) -> list[dict]:
    """Get the current teaching groups for this teacher + domain."""
    rows = await db.fetch("""
        SELECT tg.group_label, tg.child_count, tg.target_competency_id,
               tg.priority_rank, tg.child_ids,
               c.name_hi as target_name_hi, c.name_en as target_name_en
        FROM teaching_groups tg
        JOIN competencies c ON tg.target_competency_id = c.id
        WHERE tg.teacher_id = $1 AND tg.domain_id = $2
          AND tg.effective_until IS NULL
        ORDER BY tg.priority_rank
    """, teacher_id, domain_id)
    
    result = []
    for r in rows:
        # Get roll numbers for children in this group
        child_rolls = await db.fetch("""
            SELECT roll_number FROM children 
            WHERE id = ANY($1::uuid[]) AND is_active = TRUE
            ORDER BY roll_number
        """, r['child_ids'])
        
        result.append({
            "label": r['group_label'],
            "count": r['child_count'],
            "roll_numbers": [cr['roll_number'] for cr in child_rolls],
            "target_competency_id": r['target_competency_id'],
            "target_competency_name_hi": r['target_name_hi'],
            "target_competency_name_en": r['target_name_en'],
            "priority_rank": r['priority_rank'],
        })
    
    return result


async def generate_dainik_yojana(
    db, 
    teacher_id: str, 
    competency_id: str, 
    domain_id: str,
    plan_date: date,
) -> dict:
    """
    Full Dainik Yojana generation pipeline.
    Returns the complete plan + metadata.
    """
    settings = get_settings()
    start_time = time.time()
    
    # ── L1 Queries ──
    selected = await fetch_competency(db, competency_id)
    misconceptions = await fetch_misconceptions(db, competency_id)
    
    # Beginner target: direct hard prerequisite
    beginner_row = await db.fetchrow("""
        SELECT prerequisite_id FROM competency_prerequisites
        WHERE competency_id = $1 AND prerequisite_type = 'hard'
        ORDER BY prerequisite_id LIMIT 1
    """, competency_id)
    beginner_target_id = beginner_row['prerequisite_id'] if beginner_row else competency_id
    beginner_comp = await fetch_competency(db, beginner_target_id)
    
    # Proficient extension: next competency that depends on this one
    proficient_row = await db.fetchrow("""
        SELECT cp.competency_id as id FROM competency_prerequisites cp
        JOIN competencies c ON c.id = cp.competency_id
        WHERE cp.prerequisite_id = $1 AND cp.prerequisite_type = 'hard'
        ORDER BY c.sort_order LIMIT 1
    """, competency_id)
    proficient_comp = await fetch_competency(db, proficient_row['id']) if proficient_row else selected
    
    prereq_chain = await fetch_prerequisite_chain(db, competency_id, beginner_target_id)
    
    # ── Groups ──
    groups = await get_current_groups(db, teacher_id, domain_id)
    
    group_map = {g['label']: g for g in groups}
    beginner_g = group_map.get('beginner', {"count": 0, "roll_numbers": []})
    progressor_g = group_map.get('progressor', {"count": 0, "roll_numbers": []})
    proficient_g = group_map.get('proficient', {"count": 0, "roll_numbers": []})
    
    # ── Teacher + school context ──
    teacher = await db.fetchrow("""
        SELECT t.enrolled_grades, t.available_minutes, s.school_code, s.has_printer
        FROM teachers t JOIN schools s ON t.school_id = s.id
        WHERE t.id = $1
    """, teacher_id)
    
    total_children = beginner_g['count'] + progressor_g['count'] + proficient_g['count']
    
    # ── Curriculum week ──
    # Estimate current week number from date
    week_number = max(1, (plan_date.timetuple().tm_yday - 180) // 7 + 1)  # Approximate, July start
    week_info = await get_curriculum_week(
        db, settings.default_state_id, selected.grade_level, domain_id, week_number
    )
    
    # ── Yesterday's feedback ──
    yesterday_evidence = await db.fetch("""
        SELECT DISTINCT unnest(detected_misconception_ids) as misc_id
        FROM assessment_evidence
        WHERE teacher_id = $1 AND session_date = $2::date - interval '1 day'
          AND detected_misconception_ids IS NOT NULL
    """, teacher_id, plan_date)
    yesterday_misc_ids = [r['misc_id'] for r in yesterday_evidence]
    
    reteach_competencies = []
    if yesterday_misc_ids:
        for mid in yesterday_misc_ids:
            misc_detail = await db.fetchrow(
                "SELECT name_hi, competency_id FROM misconceptions WHERE id = $1", mid
            )
            if misc_detail:
                count = await db.fetchval("""
                    SELECT count(DISTINCT child_id) FROM assessment_evidence
                    WHERE teacher_id = $1 AND session_date = $2::date - interval '1 day'
                      AND $3 = ANY(detected_misconception_ids)
                """, teacher_id, plan_date, mid)
                reteach_competencies.append({
                    "competency_id": misc_detail['competency_id'],
                    "misconception_name_hi": misc_detail['name_hi'],
                    "affected_count": count,
                    "group": "progressor"
                })
    
    # ── L2 Queries ──
    anchor = await fetch_anchor_activity(db, domain_id, selected.grade_level, competency_id)
    intervention = await fetch_intervention(db, yesterday_misc_ids) if yesterday_misc_ids else None
    
    tlm_ids = []
    if intervention and intervention.tlm_ids:
        tlm_ids.extend(intervention.tlm_ids)
    available_tlms = await fetch_tlms(db, tlm_ids)
    
    # ── Assemble context ──
    ctx = OrchestrationContext(
        teacher_name="Teacher",
        school_code=teacher['school_code'] if teacher else 'DEMO',
        enrolled_grades=teacher['enrolled_grades'] if teacher else ['grade_1', 'grade_2', 'grade_3'],
        total_children=total_children or 30,
        available_minutes=teacher['available_minutes'] if teacher else settings.default_teaching_minutes,
        has_printer=teacher['has_printer'] if teacher else False,
        plan_date=str(plan_date),
        week_number=week_info['week_number'] if week_info else week_number,
        week_topic_hi=week_info['topic_title_hi'] if week_info else selected.name_hi,
        selected_competency=selected,
        domain_id=domain_id,
        domain_name_hi='गणित' if domain_id == 'numeracy' else 'R1 साक्षरता (हिंदी)',
        beginner=GroupInfo(
            label='beginner', count=beginner_g['count'],
            roll_numbers=beginner_g['roll_numbers'],
            target_competency=beginner_comp,
        ),
        progressor=GroupInfo(
            label='progressor', count=progressor_g['count'],
            roll_numbers=progressor_g['roll_numbers'],
            target_competency=selected,
        ),
        proficient=GroupInfo(
            label='proficient', count=proficient_g['count'],
            roll_numbers=proficient_g['roll_numbers'],
            target_competency=proficient_comp,
        ),
        prerequisite_chain=prereq_chain,
        misconceptions=misconceptions,
        anchor=anchor,
        intervention=intervention,
        available_tlms=available_tlms,
        reteach_competencies=reteach_competencies,
    )
    
    # ── Call Claude ──
    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(ctx)
    
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    
    response = await client.messages.create(
        model=settings.claude_model,
        max_tokens=settings.claude_max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    
    response_text = response.content[0].text
    
    # Strip markdown fences if Claude wraps in ```json
    if "```json" in response_text:
        response_text = response_text.split("```json", 1)[1]
    if "```" in response_text:
        response_text = response_text.split("```", 1)[0]
    response_text = response_text.strip()
    
    plan_json = json.loads(response_text)
    
    generation_time_ms = int((time.time() - start_time) * 1000)
    
    # ── Store plan ──
    explainability = plan_json.get('explainability', {})
    groups_snapshot = {
        'beginner': {'count': ctx.beginner.count, 'rolls': ctx.beginner.roll_numbers, 'target': beginner_target_id},
        'progressor': {'count': ctx.progressor.count, 'rolls': ctx.progressor.roll_numbers, 'target': competency_id},
        'proficient': {'count': ctx.proficient.count, 'rolls': ctx.proficient.roll_numbers, 'target': proficient_comp.id},
    }
    
    await db.execute("""
        INSERT INTO daily_plans (teacher_id, plan_date, domain_id, selected_competency_id,
                                 plan_content, explainability, groups_snapshot, 
                                 generation_time_ms, claude_model)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        ON CONFLICT (teacher_id, plan_date, domain_id) DO UPDATE SET
            plan_content = EXCLUDED.plan_content,
            explainability = EXCLUDED.explainability,
            groups_snapshot = EXCLUDED.groups_snapshot,
            generation_time_ms = EXCLUDED.generation_time_ms
    """,
        teacher_id, plan_date, domain_id, competency_id,
        json.dumps(plan_json, ensure_ascii=False),
        json.dumps(explainability, ensure_ascii=False),
        json.dumps(groups_snapshot, ensure_ascii=False),
        generation_time_ms, settings.claude_model,
    )
    
    return {
        "plan_date": str(plan_date),
        "domain_id": domain_id,
        "selected_competency_id": competency_id,
        "groups": [
            {"label": "beginner", "count": ctx.beginner.count, "roll_numbers": ctx.beginner.roll_numbers,
             "target_competency_id": beginner_target_id, "target_competency_name_hi": beginner_comp.name_hi},
            {"label": "progressor", "count": ctx.progressor.count, "roll_numbers": ctx.progressor.roll_numbers,
             "target_competency_id": competency_id, "target_competency_name_hi": selected.name_hi},
            {"label": "proficient", "count": ctx.proficient.count, "roll_numbers": ctx.proficient.roll_numbers,
             "target_competency_id": proficient_comp.id, "target_competency_name_hi": proficient_comp.name_hi},
        ],
        "plan": plan_json,
        "explainability": explainability,
        "generation_time_ms": generation_time_ms,
    }
