"""
Ankur Saathi — Review Service
Evidence capture across 3 channels, Claude Vision analysis, 
advance/reteach decision flow, level change detection.
"""

import json
import base64
from datetime import date
from typing import Optional

import anthropic

from app.core.config import get_settings

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'prompts'))
from vision_analysis import (
    VISION_SYSTEM_PROMPT, build_vision_prompt, 
    process_vision_results, check_level_changes,
)


async def record_teacher_decisions(db, teacher_id: str, plan_date: date, domain_id: str, decisions: dict):
    """
    Store the teacher's Advance/Re-teach/Not-sure decisions per group.
    Called BEFORE AI analysis — captures teacher's independent judgment.
    """
    for group_label, decision in decisions.items():
        if decision not in ('advance', 'reteach', 'not_sure'):
            continue
        
        # Update all evidence records for this group's children on this date
        # (Evidence may not exist yet if photos haven't been analysed)
        # Store as a session-level record instead
        await db.execute("""
            INSERT INTO daily_plans (teacher_id, plan_date, domain_id, selected_competency_id,
                                     plan_content, explainability, groups_snapshot)
            SELECT teacher_id, plan_date, domain_id, selected_competency_id,
                   plan_content,
                   jsonb_set(
                       COALESCE(explainability, '{}'::jsonb),
                       $4::text[],
                       to_jsonb($5::text)
                   ),
                   groups_snapshot
            FROM daily_plans
            WHERE teacher_id = $1 AND plan_date = $2 AND domain_id = $3
            ON CONFLICT (teacher_id, plan_date, domain_id) DO UPDATE SET
                explainability = jsonb_set(
                    COALESCE(daily_plans.explainability, '{}'::jsonb),
                    $4::text[],
                    to_jsonb($5::text)
                )
        """, teacher_id, plan_date, domain_id, 
            [f'teacher_decision_{group_label}'], decision)
    
    return {"status": "recorded", "decisions": decisions}


async def record_observed_assessments(db, teacher_id: str, session_date: date, items: list[dict]):
    """
    Store teacher-observed A/PA/NA assessments.
    Channel: 'observed' — teacher taps judgment in real-time during teaching.
    """
    recorded = 0
    for item in items:
        child = await db.fetchrow("""
            SELECT id FROM children 
            WHERE teacher_id = $1 AND roll_number = $2 AND is_active = TRUE
        """, teacher_id, item['roll_number'])
        
        if not child:
            continue
        
        await db.execute("""
            INSERT INTO assessment_evidence
                (child_id, competency_id, teacher_id, channel, status,
                 evidence_data, confidence, session_date, assessment_tier)
            VALUES ($1, $2, $3, 'observed', $4, $5, 'teacher_reported', $6, 'daily')
        """,
            child['id'], item['competency_id'], teacher_id, item['status'],
            json.dumps({"teacher_judgment": item['status']}, ensure_ascii=False),
            session_date,
        )
        
        # Update child_competency_status
        existing = await db.fetchrow("""
            SELECT status, consecutive_days_at_status 
            FROM child_competency_status
            WHERE child_id = $1 AND competency_id = $2
        """, child['id'], item['competency_id'])
        
        consecutive = (existing['consecutive_days_at_status'] + 1) if (existing and existing['status'] == item['status']) else 1
        
        await db.execute("""
            INSERT INTO child_competency_status
                (child_id, competency_id, status, assessment_count,
                 last_assessment_date, consecutive_days_at_status, confidence)
            VALUES ($1, $2, $3, 1, $4, $5, 'teacher_reported')
            ON CONFLICT (child_id, competency_id) DO UPDATE SET
                status = EXCLUDED.status,
                assessment_count = child_competency_status.assessment_count + 1,
                last_assessment_date = EXCLUDED.last_assessment_date,
                consecutive_days_at_status = $5,
                confidence = 'teacher_reported',
                updated_at = NOW()
        """, child['id'], item['competency_id'], item['status'], session_date, consecutive)
        
        recorded += 1
    
    return {"status": "recorded", "items_recorded": recorded}


async def record_orf_assessment(db, teacher_id: str, session_date: date, entry: dict):
    """
    Store oral reading fluency entry — teacher stopwatch + manual CWPM.
    Channel: 'oral_reading'.
    """
    child = await db.fetchrow("""
        SELECT id FROM children 
        WHERE teacher_id = $1 AND roll_number = $2 AND is_active = TRUE
    """, teacher_id, entry['roll_number'])
    
    if not child:
        return {"status": "error", "message": f"Roll {entry['roll_number']} not found"}
    
    # Determine A/PA/NA from CWPM using the competency's criteria
    comp = await db.fetchrow(
        "SELECT apna_criteria FROM competencies WHERE id = $1",
        entry.get('competency_id', 'L2.5.1')  # Default to Grade 2 ORF
    )
    
    status = 'not_achieved'
    if comp:
        criteria = comp['apna_criteria'] if isinstance(comp['apna_criteria'], dict) else json.loads(comp['apna_criteria'])
        achieved_cwpm = criteria.get('achieved', {}).get('min_cwpm', 60)
        pa_cwpm = criteria.get('partially_achieved', {}).get('cwpm_range', [25, 59])
        
        if entry['cwpm'] >= achieved_cwpm:
            status = 'achieved'
        elif entry['cwpm'] >= pa_cwpm[0]:
            status = 'partially_achieved'
    
    evidence_data = {
        "cwpm": entry['cwpm'],
        "error_count": entry['error_count'],
        "passage_id": entry['passage_id'],
        "error_types": entry.get('error_types', []),
    }
    
    await db.execute("""
        INSERT INTO assessment_evidence
            (child_id, competency_id, teacher_id, channel, status,
             evidence_data, confidence, session_date, assessment_tier)
        VALUES ($1, $2, $3, 'oral_reading', $4, $5, 'teacher_reported', $6, 'daily')
    """,
        child['id'], entry.get('competency_id', 'L2.5.1'), teacher_id, status,
        json.dumps(evidence_data, ensure_ascii=False), session_date,
    )
    
    return {"status": "recorded", "roll_number": entry['roll_number'], "cwpm": entry['cwpm'], "classification": status}


async def analyse_worksheet_photos(
    db,
    teacher_id: str,
    session_date: date,
    domain_id: str,
    competency_id: str,
    worksheet_level: str,
    photo_bytes_list: list[bytes],
    teacher_pre_judgment: Optional[str] = None,
) -> dict:
    """
    Full Claude Vision analysis pipeline:
    1. Build the Vision prompt with L1 misconception context
    2. Send photos to Claude Vision
    3. Process results into DB updates
    4. Check for discrepancies with teacher's judgment
    """
    settings = get_settings()
    
    # Get worksheet problems (from today's plan)
    plan = await db.fetchrow("""
        SELECT plan_content FROM daily_plans
        WHERE teacher_id = $1 AND plan_date = $2 AND domain_id = $3
    """, teacher_id, session_date, domain_id)
    
    problems = []
    if plan and plan['plan_content']:
        plan_data = plan['plan_content'] if isinstance(plan['plan_content'], dict) else json.loads(plan['plan_content'])
        worksheet_data = plan_data.get('worksheets', {}).get(worksheet_level, {})
        problems = worksheet_data.get('problems', [])
    
    # Get misconceptions from L1
    misconception_rows = await db.fetch("""
        SELECT id, name_en, name_hi, error_pattern, diagnostic_indicator,
               example_correct, example_incorrect, severity, frequency
        FROM misconceptions WHERE competency_id = $1 ORDER BY sort_order
    """, competency_id)
    misconceptions = [dict(r) for r in misconception_rows]
    
    # Get group roll numbers
    group_row = await db.fetchrow("""
        SELECT child_ids FROM teaching_groups
        WHERE teacher_id = $1 AND domain_id = $2 AND group_label = $3
          AND effective_until IS NULL
    """, teacher_id, domain_id, worksheet_level)
    
    group_rolls = []
    if group_row:
        rolls = await db.fetch("""
            SELECT roll_number FROM children 
            WHERE id = ANY($1::uuid[]) AND is_active = TRUE ORDER BY roll_number
        """, group_row['child_ids'])
        group_rolls = [r['roll_number'] for r in rolls]
    
    # Build Vision prompt
    vision_prompt = build_vision_prompt(
        worksheet_level=worksheet_level,
        competency_id=competency_id,
        competency_name_hi=(await db.fetchval(
            "SELECT name_hi FROM competencies WHERE id = $1", competency_id
        )) or competency_id,
        problems=problems,
        misconceptions=misconceptions,
        group_roll_numbers=group_rolls,
        photo_count=len(photo_bytes_list),
    )
    
    # Build Claude Vision request with images
    content = []
    for photo_bytes in photo_bytes_list:
        b64 = base64.b64encode(photo_bytes).decode('utf-8')
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}
        })
    content.append({"type": "text", "text": vision_prompt})
    
    # Call Claude Vision
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    
    response = await client.messages.create(
        model=settings.claude_vision_model,
        max_tokens=4000,
        system=VISION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
    )
    
    response_text = response.content[0].text
    if "```json" in response_text:
        response_text = response_text.split("```json", 1)[1]
    if "```" in response_text:
        response_text = response_text.split("```", 1)[0]
    
    vision_results = json.loads(response_text.strip())
    
    # Process into DB updates
    summary = await process_vision_results(
        db, teacher_id, str(session_date), competency_id,
        vision_results, teacher_pre_judgment,
    )
    
    return summary
