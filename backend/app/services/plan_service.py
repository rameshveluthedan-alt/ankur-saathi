"""
Ankur Saathi — Plan Service
Business logic for competency tree, curriculum week, and Dainik Yojana generation.
Wraps the orchestrate.py pipeline with proper error handling and DB access.
"""

import json
import re
import time
from collections import Counter
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
    fetch_anchor_activity, fetch_intervention, fetch_tlms, fetch_tlms_for_competencies,
    STICK_PAIR_KIT_TOTAL, STICK_TEACHER_KIT_TOTAL,
)
from baseline_assessment import compute_groups


# Claude Sonnet 5.5 runs adaptive thinking by default, and thinking tokens share
# max_tokens with the answer. At default effort, plan generation used all 16,000
# tokens on thinking and never wrote the plan. "between_tools" turns off up-front
# thinking (documented for Sonnet 5.5; "disabled" returns a 400 on this model).
# Sent via extra_body because the pinned SDK (0.34.0) predates this parameter.
# To test thinking later, try:
#   {"thinking": {"type": "adaptive"}, "output_config": {"effort": "medium"}}
CLAUDE_THINKING_BODY = {"thinking": {"type": "between_tools"}}


def validate_plan_shape(plan: dict) -> list[str]:
    """
    Check Claude's plan against the shape the PWA, worksheet renderer and Vision
    analysis read. Returns human-readable problems (empty list = good).
    The plan is stored either way so generation cost is never lost.
    """
    issues = []
    levels = ("beginner", "progressor", "proficient")

    anchor = plan.get("anchor") or {}
    for k in ("narration_hi", "opening_question_hi", "closing_question_hi",
              "beginner_participation_hi", "progressor_participation_hi",
              "proficient_participation_hi"):
        if not anchor.get(k):
            issues.append(f"anchor.{k} missing")

    blocks = (plan.get("rotation_schedule") or {}).get("blocks") or []
    if not blocks:
        issues.append("rotation_schedule.blocks missing or empty")
    teach_groups = []
    for i, b in enumerate(blocks):
        if b.get("type") not in ("anchor", "setup", "reteach", "teach", "transition"):
            issues.append(f"blocks[{i}].type invalid: {b.get('type')!r}")
        if not b.get("duration_minutes"):
            issues.append(f"blocks[{i}].duration_minutes missing")
        if b.get("type") == "teach":
            teach_groups.append(b.get("teach_group"))
            tp = b.get("talking_points") or {}
            for k in ("i_do_hi", "we_do_hi", "you_do_hi"):
                if not tp.get(k):
                    issues.append(f"blocks[{i}].talking_points.{k} missing")
    if sorted(g for g in teach_groups if g) != sorted(levels):
        issues.append(f"teach blocks should cover each group once, got {teach_groups}")

    for level in levels:
        problems = ((plan.get("worksheets") or {}).get(level) or {}).get("problems") or []
        if not problems:
            issues.append(f"worksheets.{level}.problems missing or empty")
            continue
        if len(problems) > 8:
            issues.append(f"worksheets.{level} has {len(problems)} problems (max 8 for one page)")
        ws = (plan.get("worksheets") or {}).get(level) or {}
        rc = ws.get("required_count")
        if not isinstance(rc, int) or isinstance(rc, bool) or not 1 <= rc <= len(problems):
            issues.append(f"worksheets.{level}.required_count missing or invalid: {rc!r}")
        else:
            if level == "beginner" and len(problems) > 5 and rc != 5:
                issues.append(f"worksheets.beginner has {len(problems)} problems but required_count is {rc} (should be 5)")
            if level == "progressor" and len(problems) > 6 and rc != 6:
                issues.append(f"worksheets.progressor has {len(problems)} problems but required_count is {rc} (should be 6)")
            for p in problems:
                n = p.get("number")
                if p.get("diagnostic_for_misconception") and isinstance(n, int) and n > rc:
                    issues.append(f"worksheets.{level} problem {n} reveals a misconception but is an extra (required_count {rc})")
        for p in problems:
            for k in ("number", "problem_hi", "answer"):
                if p.get(k) in (None, ""):
                    issues.append(f"worksheets.{level} problem {p.get('number', '?')}: {k} missing")

    # Stick examples must fit the kits: teacher demo kit, and the Beginner pair kit for what children build
    uses_sticks = False
    for b in blocks:
        if b.get("type") != "teach":
            continue
        g, tp = b.get("teach_group"), b.get("talking_points") or {}
        for key in ("i_do_hi", "we_do_hi", "you_do_hi"):
            text = tp.get(key) or ""
            if not any(w in text for w in ("छड़ी", "छड़ियों", "छड़ियाँ")):
                continue
            uses_sticks = True
            totals = [int(a) + int(c) for a, c in re.findall(r"(\d{1,3})\s*\+\s*(\d{1,3})", text)]
            cap = STICK_PAIR_KIT_TOTAL if (g == "beginner" and key != "i_do_hi") else STICK_TEACHER_KIT_TOTAL
            if totals and max(totals) > cap:
                issues.append(f"{g} {key}: a stick example totals {max(totals)} but the kit holds only {cap} sticks")
    if uses_sticks and "छड़" not in " ".join(plan.get("prep_hi") or []):
        issues.append("sticks are used in the talking points but prep_hi does not mention them")

    items = (plan.get("explainability") or {}).get("items")
    if not isinstance(items, list) or not items:
        issues.append("explainability.items missing or empty")
    else:
        for i, it in enumerate(items):
            if not isinstance(it, dict):
                issues.append(f"explainability.items[{i}] is not an object")
                continue
            for k in ("title_hi", "title_en", "body_hi", "body_en"):
                if not it.get(k):
                    issues.append(f"explainability.items[{i}].{k} missing")

    return issues



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


async def get_curriculum_week_for_competency(db, state_id: str, domain_id: str, competency_id: str) -> Optional[dict]:
    """
    Find the week of the state plan that teaches the selected competency.
    Prefers the focus week (fewest competencies listed), then the earliest.
    Looking up by competency, not by calendar date, keeps the week topic and notes
    consistent with what the teacher actually selected.
    """
    row = await db.fetchrow("""
        SELECT cw.week_number, cw.topic_title_en, cw.topic_title_hi,
               cw.competency_ids, cw.notes
        FROM curriculum_weeks cw
        JOIN curriculum_plans cp ON cw.plan_id = cp.id
        WHERE cp.state_id = $1 AND cp.is_active = TRUE
          AND cw.domain_id = $2 AND $3 = ANY(cw.competency_ids)
        ORDER BY array_length(cw.competency_ids, 1), cw.week_number
        LIMIT 1
    """, state_id, domain_id, competency_id)
    return dict(row) if row else None


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
    """
    The current Beginner / Progressor / Proficient groups for this teacher and subject.

    Built from each child's CURRENT level (child_lakshya_positions), so a level change the
    teacher accepts shows up in the very next plan. The teaching_groups table is only a
    fallback for databases that have no level records: nothing keeps it in step with level
    changes, so trusting it would leave children in their old group.
    """
    groups = await derive_groups_from_positions(db, teacher_id, domain_id)
    if groups:
        return groups
    return await _stored_groups(db, teacher_id, domain_id)


async def _stored_groups(db, teacher_id: str, domain_id: str) -> list[dict]:
    """Groups saved in the teaching_groups table (fallback only; see get_current_groups)."""
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


async def derive_groups_from_positions(db, teacher_id: str, domain_id: str) -> list[dict]:
    """
    Build the Beginner / Progressor / Proficient groups from each child's current level in
    this subject (child_lakshya_positions): the same data the Progress screen shows.
    Children with no level recorded for this subject are not placed in any group.
    The returned target competency is the one most children in the group are currently
    working on. It is for display only: plan generation derives each group's teaching
    target from the prerequisite graph.
    """
    rows = await db.fetch("""
        SELECT c.roll_number, clp.bpp_level, clp.current_competency_id
        FROM child_lakshya_positions clp
        JOIN children c ON clp.child_id = c.id
        WHERE c.teacher_id = $1 AND clp.domain_id = $2 AND c.is_active = TRUE
        ORDER BY c.roll_number
    """, teacher_id, domain_id)
    if not rows:
        return []

    by_level: dict[str, list] = {}
    for r in rows:
        by_level.setdefault(r['bpp_level'], []).append(r)

    comp_ids = list({r['current_competency_id'] for r in rows if r['current_competency_id']})
    names = {}
    if comp_ids:
        for n in await db.fetch("SELECT id, name_hi, name_en FROM competencies WHERE id = ANY($1::text[])", comp_ids):
            names[n['id']] = (n['name_hi'], n['name_en'])

    result = []
    for rank, label in enumerate(('beginner', 'progressor', 'proficient'), start=1):
        members = by_level.get(label)
        if not members:
            continue
        counts = Counter(m['current_competency_id'] for m in members if m['current_competency_id'])
        target = min(counts, key=lambda k: (-counts[k], k)) if counts else None   # most common; ties by id
        name_hi, name_en = names.get(target, ('', ''))
        result.append({
            "label": label,
            "count": len(members),
            "roll_numbers": [m['roll_number'] for m in members],
            "target_competency_id": target,
            "target_competency_name_hi": name_hi,
            "target_competency_name_en": name_en,
            "priority_rank": rank,
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

    # What each group may safely practise on its own, and the new skill it is taught today
    safe_beginner = []
    if beginner_target_id != competency_id:
        for r in await db.fetch("""
            SELECT c.id, c.name_hi FROM competency_prerequisites cp
            JOIN competencies c ON c.id = cp.prerequisite_id
            WHERE cp.competency_id = $1 AND cp.prerequisite_type = 'hard'
            ORDER BY c.sort_order LIMIT 3""", beginner_target_id):
            safe_beginner.append((r['id'], r['name_hi']))
    group_skills = {
        "beginner": {"safe": safe_beginner, "new": (beginner_comp.id, beginner_comp.name_hi)},
        "progressor": {"safe": [(beginner_comp.id, beginner_comp.name_hi)] if beginner_target_id != competency_id else [],
                       "new": (selected.id, selected.name_hi)},
        "proficient": {"safe": [(selected.id, selected.name_hi)] if proficient_comp.id != selected.id else [],
                       "new": (proficient_comp.id, proficient_comp.name_hi)},
    }
    
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
    week_info = await get_curriculum_week_for_competency(
        db, settings.default_state_id, domain_id, competency_id
    ) or await get_curriculum_week(
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
    if yesterday_misc_ids:
        intervention = await fetch_intervention(db, yesterday_misc_ids)
        intervention_mode = "reteach" if intervention else "none"
    else:
        # No gaps yet: use the template for today's own misconceptions as pre-teaching
        intervention = await fetch_intervention(db, [m.id for m in misconceptions])
        intervention_mode = "preteach" if intervention else "none"
    
    tlm_ids = []
    if intervention and intervention.tlm_ids:
        tlm_ids.extend(intervention.tlm_ids)
    intervention_tlms = await fetch_tlms(db, tlm_ids)
    competency_tlms = await fetch_tlms_for_competencies(
        db, [competency_id, beginner_target_id, proficient_comp.id]
    )
    available_tlms, seen_tlm_ids = [], set()
    for t in competency_tlms + intervention_tlms:   # de-duplicate, keep order
        if t.id not in seen_tlm_ids:
            seen_tlm_ids.add(t.id)
            available_tlms.append(t)

    # Bundling sticks (TLM-001): teacher demo kit + Beginner pair kits sized from the Beginner group
    stick_policy = None
    sticks_for_skill = await db.fetchval(
        "SELECT TRUE FROM tlm_references WHERE id = 'TLM-001' AND $1 = ANY(competency_ids)", competency_id)
    if sticks_for_skill and any(t.id == "TLM-001" for t in available_tlms):
        n_beg = beginner_g['count']
        stick_policy = {"beginner_children": n_beg, "pair_kits": (n_beg + 1) // 2 if n_beg else 0}
    
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
        week_notes=(week_info or {}).get('notes'),
        intervention_mode=intervention_mode,
        group_skills=group_skills,
        stick_policy=stick_policy,
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
        extra_body=CLAUDE_THINKING_BODY,
    )
    
    # Find the text block — content[0] may be a thinking block on some models,
    # so search for the block with type == "text" rather than assuming position.
    response_text = None
    for block in response.content:
        if getattr(block, "type", None) == "text":
            response_text = block.text
            break
    
    print(f"   Claude: stop_reason={response.stop_reason}, usage={response.usage}")
    
    if response_text is None:
        raise ValueError(
            f"No text block found in Claude's response. "
            f"Block types: {[getattr(b, 'type', '?') for b in response.content]}, "
            f"stop_reason={response.stop_reason}. "
            f"If stop_reason is 'max_tokens', thinking used the whole budget: "
            f"raise CLAUDE_MAX_TOKENS in .env."
        )
    
    if response.stop_reason == "max_tokens":
        raise ValueError(
            "Claude's response was cut off by max_tokens, so the plan JSON is incomplete. "
            "Raise CLAUDE_MAX_TOKENS in .env."
        )
    
    # Strip markdown fences if Claude wraps in ```json
    if "```json" in response_text:
        response_text = response_text.split("```json", 1)[1]
    if "```" in response_text:
        response_text = response_text.split("```", 1)[0]
    response_text = response_text.strip()
    
    plan_json = json.loads(response_text)
    
    validation_warnings = validate_plan_shape(plan_json)
    if validation_warnings:
        print(f"   PLAN SHAPE WARNINGS ({len(validation_warnings)}):")
        for w in validation_warnings[:15]:
            print(f"     - {w}")
    else:
        print("   Plan shape OK")
    
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
            generation_time_ms = EXCLUDED.generation_time_ms,
            selected_competency_id = EXCLUDED.selected_competency_id,
            claude_model = EXCLUDED.claude_model
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
        "validation_warnings": validation_warnings,
    }
