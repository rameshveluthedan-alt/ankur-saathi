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
from app.services.plan_service import get_current_groups

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'prompts'))
from vision_analysis import (
    VISION_SYSTEM_PROMPT, build_vision_prompt, 
    process_vision_results, check_level_changes,
)


# Sonnet 5.5 thinks by default and thinking tokens share max_tokens with the answer.
# "between_tools" turns off up-front thinking (see plan_service.py for details).
# Revisit once we test with real worksheet photos: handwriting extraction may
# benefit from some thinking, in which case use adaptive + output_config effort.
CLAUDE_THINKING_BODY = {"thinking": {"type": "between_tools"}}


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
            DELETE FROM assessment_evidence
            WHERE child_id = $1 AND competency_id = $2 AND session_date = $3 AND channel = 'observed'
        """, child['id'], item['competency_id'], session_date)

        await db.execute("""
            INSERT INTO assessment_evidence
                (child_id, competency_id, teacher_id, channel, status,
                 evidence_data, confidence, session_date, assessment_tier)
            VALUES ($1, $2, $3, 'observed', $4, $5, 'medium', $6, 'daily')
        """,
            child['id'], item['competency_id'], teacher_id, item['status'],
            json.dumps({"teacher_judgment": item['status']}, ensure_ascii=False),
            session_date,
        )
        
        # Update child_competency_status
        existing = await db.fetchrow("""
            SELECT status, consecutive_days_at_status, last_assessment_date
            FROM child_competency_status
            WHERE child_id = $1 AND competency_id = $2
        """, child['id'], item['competency_id'])

        same_day = bool(existing and existing['last_assessment_date'] == session_date)   # a re-entry replaces, not adds a day
        consecutive = (existing['consecutive_days_at_status'] + (0 if same_day else 1)) if (existing and existing['status'] == item['status']) else 1
        count_increment = 0 if same_day else 1
        
        await db.execute("""
            INSERT INTO child_competency_status
                (child_id, competency_id, status, assessment_count,
                 last_assessment_date, consecutive_days_at_status, confidence)
            VALUES ($1, $2, $3, 1, $4, $5, 'medium')
            ON CONFLICT (child_id, competency_id) DO UPDATE SET
                status = EXCLUDED.status,
                assessment_count = child_competency_status.assessment_count + $6,
                last_assessment_date = EXCLUDED.last_assessment_date,
                consecutive_days_at_status = $5,
                confidence = 'medium',
                updated_at = NOW()
        """, child['id'], item['competency_id'], item['status'], session_date, consecutive, count_increment)
        
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
        VALUES ($1, $2, $3, 'oral_reading', $4, $5, 'medium', $6, 'daily')
    """,
        child['id'], entry.get('competency_id', 'L2.5.1'), teacher_id, status,
        json.dumps(evidence_data, ensure_ascii=False), session_date,
    )
    
    return {"status": "recorded", "roll_number": entry['roll_number'], "cwpm": entry['cwpm'], "classification": status}


def _extract_json_array(text: str):
    """Parse the model's JSON array even if it added a markdown fence or a line of preamble."""
    text = (text or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    i, j = text.find("["), text.rfind("]")
    if i != -1 and j > i:
        return json.loads(text[i:j + 1])
    raise ValueError("The Vision reply did not contain a JSON array")


class BadImageError(ValueError):
    """The upload is not an image we can read."""


def prepare_photo(data: bytes, max_side: int = 1800, quality: int = 85, max_bytes: int = 1_500_000) -> bytes:
    """
    Phone photos are 3 to 10 MB and often rotated by an EXIF flag, and the model API has a size limit.
    Turn any upload into an upright JPEG with its longest side at most max_side and a size under max_bytes.
    Handwriting stays legible at 1800 px. Anything that is not an image raises ValueError.
    """
    from io import BytesIO
    from PIL import Image, ImageOps, UnidentifiedImageError
    try:
        img = Image.open(BytesIO(data))
        img = ImageOps.exif_transpose(img)
    except (UnidentifiedImageError, OSError) as e:
        raise BadImageError("The upload is not a readable image") from e
    img = img.convert("RGB")
    if max(img.size) > max_side:
        scale = max_side / max(img.size)
        img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    for q in (quality, 75, 65, 55):
        buf = BytesIO()
        img.save(buf, "JPEG", quality=q, optimize=True)
        if buf.tell() <= max_bytes:
            break
    return buf.getvalue()


async def call_vision(photo_bytes_list: list, vision_prompt: str):
    """
    The one place the worksheet photos go to Claude Vision. Production and scripts/eval_vision.py both use it,
    so what is measured is exactly what runs. Returns (the parsed JSON array, a usage dict).
    """
    settings = get_settings()
    content = []
    for photo_bytes in photo_bytes_list:
        b64 = base64.b64encode(prepare_photo(photo_bytes)).decode("utf-8")
        content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}})
    content.append({"type": "text", "text": vision_prompt})
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model=settings.claude_vision_model,
        max_tokens=12000,
        system=VISION_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
        extra_body=CLAUDE_THINKING_BODY,
    )
    response_text = next((b.text for b in response.content if getattr(b, "type", None) == "text"), None)
    if response_text is None:
        raise ValueError(f"No text block found in Claude Vision's response. Block types received: {[getattr(b, 'type', '?') for b in response.content]}")
    usage = {"input_tokens": getattr(response.usage, "input_tokens", 0), "output_tokens": getattr(response.usage, "output_tokens", 0)}
    return _extract_json_array(response_text), usage


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
        SELECT plan_content, groups_snapshot FROM daily_plans
        WHERE teacher_id = $1 AND plan_date = $2 AND domain_id = $3
    """, teacher_id, session_date, domain_id)
    # Each level's sheet is credited to THAT group's own skill (the Beginner sheet to the prerequisite, the
    # Proficient sheet to the extension), not to the day's main skill for all three.
    if plan and plan['groups_snapshot']:
        snap = plan['groups_snapshot']
        snap = json.loads(snap) if isinstance(snap, str) else snap
        competency_id = (snap.get(worksheet_level) or {}).get('target') or competency_id
    
    problems = []
    required_count = None
    if plan and plan['plan_content']:
        plan_data = plan['plan_content'] if isinstance(plan['plan_content'], dict) else json.loads(plan['plan_content'])
        worksheet_data = plan_data.get('worksheets', {}).get(worksheet_level, {})
        problems = worksheet_data.get('problems', [])
        try:
            required_count = int(worksheet_data['required_count']) if worksheet_data.get('required_count') else None
        except (TypeError, ValueError):
            required_count = None
    
    # Get misconceptions from L1
    misconception_rows = await db.fetch("""
        SELECT id, name_en, name_hi, error_pattern, diagnostic_indicator,
               example_correct, example_incorrect, severity, frequency
        FROM misconceptions WHERE competency_id = $1 ORDER BY sort_order
    """, competency_id)
    misconceptions = [dict(r) for r in misconception_rows]
    
    # Get group roll numbers (stored groups, or derived from the children's levels)
    groups = await get_current_groups(db, teacher_id, domain_id)
    group_rolls = next((g['roll_numbers'] for g in groups if g['label'] == worksheet_level), [])
    
    if not problems:
        raise LookupError(
            "No worksheet found for this date, subject and level. Generate today's plan first, "
            "so the photos can be checked against its answer key."
        )

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
        required_count=required_count,
        domain_id=domain_id,
    )
    
    vision_results, _usage = await call_vision(photo_bytes_list, vision_prompt)
    
    # Process into DB updates
    summary = await process_vision_results(
        db, teacher_id, session_date, competency_id,
        vision_results, teacher_pre_judgment, required_count=required_count,
    )
    
    return summary
