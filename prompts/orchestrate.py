"""
Ankur Saathi — Dainik Yojana Orchestration Pipeline
Queries L1 (structured KB) + L2 (content bank) and assembles the Claude prompt.

This is the core function the FastAPI endpoint calls.
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Optional


# ============================================================================
# DATA CLASSES — typed structures for the orchestration context
# ============================================================================

@dataclass
class Competency:
    id: str
    name_en: str
    name_hi: str
    grade_level: str
    assessment_modality: str
    apna_criteria: dict
    number_range: Optional[dict] = None
    problem_types: Optional[list] = None

@dataclass
class Prerequisite:
    id: str
    name_en: str
    name_hi: str
    prerequisite_type: str  # 'hard' or 'soft'
    is_beginner_target: bool = False

@dataclass
class Misconception:
    id: str
    name_en: str
    name_hi: str
    error_pattern: str
    diagnostic_indicator: str
    example_correct: Optional[str]
    example_incorrect: Optional[str]
    severity: str
    frequency: str

@dataclass
class GroupInfo:
    label: str  # 'beginner', 'progressor', 'proficient'
    count: int
    roll_numbers: list[int]
    target_competency: Competency
    yesterday_decision: Optional[str] = None  # 'advance', 'reteach', 'not_sure'

@dataclass
class AnchorTemplate:
    id: str
    title_en: str
    title_hi: str
    theme: str
    template_body: str

@dataclass
class InterventionTemplate:
    id: str
    title_en: str
    title_hi: str
    misconception_ids: list[str]
    steps: list[dict]
    tlm_ids: Optional[list[str]] = None

@dataclass
class TLMRef:
    id: str
    name_en: str
    name_hi: str
    availability: str
    diy_instructions: Optional[str] = None

@dataclass
class OrchestrationContext:
    """Everything the Claude prompt needs, assembled from L1 + L2 queries."""
    
    # Classroom
    teacher_name: str
    school_code: str
    enrolled_grades: list[str]
    total_children: int
    available_minutes: int
    has_printer: bool
    plan_date: str
    week_number: int
    week_topic_hi: str
    
    # Selected competency
    selected_competency: Competency
    domain_id: str
    domain_name_hi: str
    
    # Groups
    beginner: GroupInfo
    progressor: GroupInfo
    proficient: GroupInfo
    
    # L1 context
    prerequisite_chain: list[Prerequisite]
    misconceptions: list[Misconception]
    
    # L2 retrieved content
    anchor: AnchorTemplate
    intervention: Optional[InterventionTemplate] = None
    available_tlms: list[TLMRef] = field(default_factory=list)
    
    # Yesterday's feedback
    reteach_competencies: list[dict] = field(default_factory=list)
    yesterday_analysis: Optional[dict] = None
    
    # Assessment prompts
    observed_competencies: list[dict] = field(default_factory=list)
    orf_scheduled: bool = False
    orf_roll_numbers: list[int] = field(default_factory=list)
    orf_passage_id: Optional[str] = None
    orf_target_cwpm: Optional[int] = None


# ============================================================================
# DATABASE QUERIES — each returns typed data from L1 or L2
# ============================================================================

async def fetch_competency(db, competency_id: str) -> Competency:
    """L1 deterministic lookup: get competency details."""
    row = await db.fetchrow("""
        SELECT c.id, c.name_en, c.name_hi, c.grade_level, 
               c.assessment_modality, c.apna_criteria, 
               c.number_range, c.problem_types
        FROM competencies c
        WHERE c.id = $1
    """, competency_id)
    return Competency(
        id=row['id'], name_en=row['name_en'], name_hi=row['name_hi'],
        grade_level=row['grade_level'], assessment_modality=row['assessment_modality'],
        apna_criteria=row['apna_criteria'], number_range=row['number_range'],
        problem_types=row['problem_types']
    )


async def fetch_prerequisite_chain(db, competency_id: str, beginner_target_id: str = None) -> list[Prerequisite]:
    """L1 recursive DAG walk: get all prerequisites in learning order."""
    rows = await db.fetch("""
        WITH RECURSIVE chain AS (
            SELECT c.id, c.name_en, c.name_hi, cp.prerequisite_type, 0 as depth
            FROM competency_prerequisites cp
            JOIN competencies c ON c.id = cp.prerequisite_id
            WHERE cp.competency_id = $1
            
            UNION ALL
            
            SELECT c.id, c.name_en, c.name_hi, cp.prerequisite_type, ch.depth + 1
            FROM competency_prerequisites cp
            JOIN competencies c ON c.id = cp.prerequisite_id
            JOIN chain ch ON cp.competency_id = ch.id
            WHERE ch.depth < 8
        )
        SELECT DISTINCT id, name_en, name_hi, prerequisite_type, MIN(depth) as depth
        FROM chain
        GROUP BY id, name_en, name_hi, prerequisite_type
        ORDER BY depth DESC
    """, competency_id)
    
    return [
        Prerequisite(
            id=r['id'], name_en=r['name_en'], name_hi=r['name_hi'],
            prerequisite_type=r['prerequisite_type'],
            is_beginner_target=(r['id'] == beginner_target_id)
        )
        for r in rows
    ]


async def fetch_misconceptions(db, competency_id: str) -> list[Misconception]:
    """L1 deterministic lookup: misconception taxonomy for this competency."""
    rows = await db.fetch("""
        SELECT id, name_en, name_hi, error_pattern, diagnostic_indicator,
               example_correct, example_incorrect, severity, frequency
        FROM misconceptions
        WHERE competency_id = $1
        ORDER BY sort_order
    """, competency_id)
    
    return [Misconception(**dict(r)) for r in rows]


async def fetch_anchor_activity(
    db, domain_id: str, grade_level: str, 
    competency_id: str, query_embedding=None
) -> AnchorTemplate:
    """
    L2 retrieval: find best anchor activity.
    Uses semantic search if embedding provided, falls back to keyword + competency match.
    """
    if query_embedding is not None:
        # Semantic retrieval (when embeddings are populated)
        row = await db.fetchrow("""
            SELECT id, title_en, title_hi, theme, template_body,
                   1 - (embedding <=> $4) AS similarity
            FROM anchor_activities
            WHERE domain_id = $1
              AND $2 = ANY(grade_range)
              AND is_active = TRUE
            ORDER BY similarity DESC
            LIMIT 1
        """, domain_id, grade_level, competency_id, query_embedding)
    else:
        # Fallback: competency match + keyword
        row = await db.fetchrow("""
            SELECT id, title_en, title_hi, theme, template_body
            FROM anchor_activities
            WHERE domain_id = $1
              AND $2 = ANY(grade_range)
              AND ($3 = ANY(primary_competency_ids) OR $3 = ANY(secondary_competency_ids))
              AND is_active = TRUE
            ORDER BY 
                CASE WHEN $3 = ANY(primary_competency_ids) THEN 0 ELSE 1 END,
                random()
            LIMIT 1
        """, domain_id, grade_level, competency_id)
    
    if not row:
        # Last fallback: any anchor for this domain + grade
        row = await db.fetchrow("""
            SELECT id, title_en, title_hi, theme, template_body
            FROM anchor_activities
            WHERE domain_id = $1 AND $2 = ANY(grade_range) AND is_active = TRUE
            ORDER BY random() LIMIT 1
        """, domain_id, grade_level)
    
    return AnchorTemplate(
        id=row['id'], title_en=row['title_en'], title_hi=row['title_hi'],
        theme=row['theme'], template_body=row['template_body']
    )


async def fetch_intervention(db, misconception_ids: list[str]) -> Optional[InterventionTemplate]:
    """L2 deterministic retrieval: intervention for detected misconceptions."""
    if not misconception_ids:
        return None
    
    row = await db.fetchrow("""
        SELECT id, title_en, title_hi, misconception_ids, steps, tlm_ids
        FROM intervention_templates
        WHERE misconception_ids && $1::text[]
          AND is_active = TRUE
        ORDER BY effectiveness_score DESC NULLS LAST
        LIMIT 1
    """, misconception_ids)
    
    if not row:
        return None
    
    return InterventionTemplate(
        id=row['id'], title_en=row['title_en'], title_hi=row['title_hi'],
        misconception_ids=row['misconception_ids'], steps=row['steps'],
        tlm_ids=row['tlm_ids']
    )


async def fetch_tlms(db, tlm_ids: list[str]) -> list[TLMRef]:
    """L2 lookup: get TLM details."""
    if not tlm_ids:
        return []
    
    rows = await db.fetch("""
        SELECT id, name_en, name_hi, availability, diy_instructions
        FROM tlm_references
        WHERE id = ANY($1::text[])
    """, tlm_ids)
    
    return [TLMRef(**dict(r)) for r in rows]


# ============================================================================
# PROMPT ASSEMBLY — builds the complete Claude prompt from context
# ============================================================================

def build_system_prompt() -> str:
    """Returns the static system prompt."""
    return """You are the Ankur Saathi orchestration engine. You generate a complete Dainik Yojana (daily teaching plan) for an Indian FLN classroom using a station rotation model.

Your role: Generate structured, differentiated teaching plans. Every competency, prerequisite, misconception, and assessment criterion you reference MUST come from the structured context provided. Do not invent curriculum content from training data.

Design principles:
1. AI proposes, teacher decides. Tone is supportive, never prescriptive.
2. Level-matched instruction. Beginners get prerequisite content. Progressors get target with scaffolding. Proficients get extensions.
3. Station rotation. Two groups work independently (on previously mastered content) while teacher teaches one group. No group does new content independently before teacher has taught it.
4. Noise-robust assessment. Use the competency's modality tag for assessment channel.
5. Hindi-first. All teacher-facing content in Hindi. English only for metadata.
6. Offline-friendly. Plan must work once cached.

Output format: Return a JSON object with the structure specified in the user prompt."""


def build_user_prompt(ctx: OrchestrationContext) -> str:
    """Assembles the user prompt with all L1 + L2 context injected."""
    
    # Priority group logic
    priority_group = "beginner"
    priority_reason = "Default: Beginners get first slot for prerequisite foundation."
    if ctx.reteach_competencies:
        # If reteach needed, that group gets priority
        reteach_groups = [r.get('group', 'beginner') for r in ctx.reteach_competencies]
        if 'progressor' in reteach_groups:
            priority_group = "progressor"
            priority_reason = f"Yesterday's analysis detected misconceptions in Progressor group."
        elif 'proficient' in reteach_groups:
            priority_group = "proficient"
            priority_reason = f"Yesterday's analysis detected misconceptions in Proficient group."
    
    # Build misconception section
    misconception_text = ""
    for m in ctx.misconceptions:
        misconception_text += f"""
### {m.id}: {m.name_hi}
- **Error pattern:** {m.error_pattern}
- **How to detect:** {m.diagnostic_indicator}
- **Example correct:** {m.example_correct or 'N/A'}
- **Example incorrect:** {m.example_incorrect or 'N/A'}
- **Severity:** {m.severity} | **Frequency:** {m.frequency}
"""
    
    # Build prerequisite chain
    prereq_text = ""
    for p in ctx.prerequisite_chain:
        marker = " ← शुरुआती समूह का लक्ष्य (BEGINNER TARGET)" if p.is_beginner_target else ""
        prereq_text += f"- **{p.id}** — {p.name_hi} ({p.prerequisite_type}){marker}\n"
    
    if not prereq_text:
        prereq_text = "- Root competency — no prerequisites.\n"
    
    # Build reteach section
    reteach_text = ""
    if ctx.reteach_competencies:
        reteach_text = "Yesterday's gaps require a 5-minute re-teaching segment:\n"
        for r in ctx.reteach_competencies:
            reteach_text += f"- {r['competency_id']}: {r['misconception_name_hi']} ({r['affected_count']} children)\n"
    else:
        reteach_text = "No re-teaching needed from yesterday."
    
    # Build intervention section
    intervention_text = ""
    if ctx.intervention:
        intervention_text = f"""
**Template ID:** {ctx.intervention.id} — {ctx.intervention.title_hi}
**Targets:** {', '.join(ctx.intervention.misconception_ids)}
**Steps:**
```json
{json.dumps(ctx.intervention.steps, ensure_ascii=False, indent=2)}
```
**Required TLM:** {', '.join(ctx.intervention.tlm_ids or ['None'])}
"""
    else:
        intervention_text = "No intervention template needed."
    
    # Build TLM section
    tlm_text = ""
    for t in ctx.available_tlms:
        diy = f" — DIY: {t.diy_instructions}" if t.diy_instructions else ""
        tlm_text += f"- {t.id}: {t.name_hi} ({t.availability}){diy}\n"
    if not tlm_text:
        tlm_text = "- No TLMs required for today's plan.\n"
    
    # Build observation reminders
    obs_text = ""
    if ctx.observed_competencies:
        for oc in ctx.observed_competencies:
            obs_text += f"  - {oc['id']}: {oc['name_hi']} — for Roll Nos. {oc['target_roll_numbers']}\n"
    
    # Compute rotation timing
    anchor_duration = 10
    setup_duration = 2
    reteach_duration = 5 if ctx.reteach_competencies else 0
    transition_total = 4  # 2 transitions × 2 min each
    teaching_time = ctx.available_minutes - anchor_duration - setup_duration - reteach_duration - transition_total
    priority_duration = max(teaching_time * 4 // 10, 15)  # ~40% of teaching time
    standard_duration = (teaching_time - priority_duration) // 2
    
    # Determine group rotation order
    groups = ['beginner', 'progressor', 'proficient']
    groups.remove(priority_group)
    rotation_order = [priority_group] + groups
    
    # Top misconception IDs for worksheet design
    top_misconception_ids = [m.id for m in ctx.misconceptions[:3]]
    
    prompt = f"""Generate today's Dainik Yojana using ONLY the structured context below.

## CLASSROOM CONTEXT

**Teacher:** {ctx.teacher_name} ({ctx.school_code})
**Grades in room:** {', '.join(ctx.enrolled_grades)}
**Total children:** {ctx.total_children}
**Available teaching time:** {ctx.available_minutes} minutes
**Has printer:** {'हाँ' if ctx.has_printer else 'नहीं (board-copy mode)'}
**Date:** {ctx.plan_date}
**Week:** {ctx.week_number} ({ctx.week_topic_hi})

## TODAY'S LAKSHYA

**Domain:** {ctx.domain_name_hi} ({ctx.domain_id})
**Competency:** {ctx.selected_competency.id} — {ctx.selected_competency.name_hi}
({ctx.selected_competency.name_en})
**Grade level:** {ctx.selected_competency.grade_level}
**Assessment modality:** {ctx.selected_competency.assessment_modality}

A/PA/NA Criteria:
```json
{json.dumps(ctx.selected_competency.apna_criteria, ensure_ascii=False, indent=2)}
```

Number range: {json.dumps(ctx.selected_competency.number_range, ensure_ascii=False) if ctx.selected_competency.number_range else 'N/A'}
Problem types: {', '.join(ctx.selected_competency.problem_types) if ctx.selected_competency.problem_types else 'General'}

## THREE GROUPS

### शुरुआती (Beginner) — {ctx.beginner.count} children (Roll: {ctx.beginner.roll_numbers})
Working on PREREQUISITE: {ctx.beginner.target_competency.id} — {ctx.beginner.target_competency.name_hi}

### प्रगतिशील (Progressor) — {ctx.progressor.count} children (Roll: {ctx.progressor.roll_numbers})
Working on TODAY'S LAKSHYA with scaffolding: {ctx.progressor.target_competency.id} — {ctx.progressor.target_competency.name_hi}

### दक्ष (Proficient) — {ctx.proficient.count} children (Roll: {ctx.proficient.roll_numbers})
Working on EXTENSION: {ctx.proficient.target_competency.id} — {ctx.proficient.target_competency.name_hi}

## PREREQUISITE CHAIN (from L1)
{prereq_text}

## MISCONCEPTION TAXONOMY (from L1)
{misconception_text}

## YESTERDAY'S FEEDBACK
{reteach_text}

## RETRIEVED CONTENT (from L2)

### Anchor Activity Template
**{ctx.anchor.id}** — {ctx.anchor.title_hi} (Theme: {ctx.anchor.theme})
```
{ctx.anchor.template_body}
```
Adapt this for today's competency and number range. Fill all {{{{placeholders}}}}.

### Intervention Template
{intervention_text}

### Available TLMs
{tlm_text}

## GENERATE THE DAINIK YOJANA

### PART A: ANCHOR ({anchor_duration} min, whole class)
Adapt the anchor template. Hindi narration, differentiated participation, closing question.

### PART B: THREE WORKSHEETS
- शुरुआती: {ctx.beginner.target_competency.name_hi} — 8-10 problems with visual scaffolding
- प्रगतिशील: {ctx.selected_competency.name_hi} — 8-10 problems, scaffolding faded, misconception-revealing problems for {', '.join(top_misconception_ids)}
- दक्ष: {ctx.proficient.target_competency.name_hi} — 8-10 extension problems + word problems
Include answer keys and misconception diagnostic maps.

### PART C: ROTATION SCHEDULE ({ctx.available_minutes} min total)
- Anchor: {anchor_duration} min
- Setup: {setup_duration} min
{f'- Re-teach: {reteach_duration} min' if reteach_duration else ''}
- Block 1: TEACH {rotation_order[0]} ({priority_duration} min) — {priority_reason}
- Block 2: TEACH {rotation_order[1]} ({standard_duration} min)
- Block 3: TEACH {rotation_order[2]} ({standard_duration} min)
- Transitions: 2 min each
Each block: I Do → We Do → You Do with Hindi talking points.

### PART D: CLASSROOM MANAGEMENT
Rotation chart, peer monitors, transition scripts (Hindi), independent station activities (on PREVIOUSLY MASTERED content only).

### PART E: REVIEW PROMPTS
- Photo sample: ALL of {rotation_order[0]}, 3-4 each from other groups
- Observation: {obs_text if obs_text else 'No observed-modality competencies today.'}
{'- ORF: Roll Nos. ' + str(ctx.orf_roll_numbers) + ' on passage ' + ctx.orf_passage_id if ctx.orf_scheduled else ''}

Return as a single JSON object with keys: anchor, worksheets, rotation_schedule, classroom_management, review_prompts, explainability.
"""
    
    return prompt


# ============================================================================
# MAIN ORCHESTRATION FUNCTION — called by the FastAPI endpoint
# ============================================================================

async def generate_dainik_yojana(
    db,
    anthropic_client,
    teacher_id: str,
    selected_competency_id: str,
    plan_date: date,
):
    """
    Full orchestration pipeline:
    1. Query L1 for competency + prerequisites + misconceptions
    2. Query L2 for anchor activity + intervention (if needed)
    3. Assemble prompt with all context
    4. Call Claude API
    5. Parse and validate response
    6. Store plan in daily_plans table
    7. Return structured Dainik Yojana
    """
    
    # ── Step 1: L1 Queries ──
    competency = await fetch_competency(db, selected_competency_id)
    
    # Get the direct hard prerequisite (= Beginner group's target)
    hard_prereqs = await db.fetch("""
        SELECT prerequisite_id FROM competency_prerequisites
        WHERE competency_id = $1 AND prerequisite_type = 'hard'
        ORDER BY prerequisite_id
        LIMIT 1
    """, selected_competency_id)
    
    beginner_target_id = hard_prereqs[0]['prerequisite_id'] if hard_prereqs else selected_competency_id
    beginner_competency = await fetch_competency(db, beginner_target_id)
    
    # Get next competency for Proficient extension
    proficient_extension = await db.fetchrow("""
        SELECT cp.competency_id as id FROM competency_prerequisites cp
        JOIN competencies c ON c.id = cp.competency_id
        WHERE cp.prerequisite_id = $1 AND cp.prerequisite_type = 'hard'
        ORDER BY c.sort_order LIMIT 1
    """, selected_competency_id)
    
    if proficient_extension:
        proficient_competency = await fetch_competency(db, proficient_extension['id'])
    else:
        proficient_competency = competency  # Same competency, extension problems
    
    prerequisite_chain = await fetch_prerequisite_chain(db, selected_competency_id, beginner_target_id)
    misconceptions = await fetch_misconceptions(db, selected_competency_id)
    
    # ── Step 2: Get classroom context ──
    teacher = await db.fetchrow("""
        SELECT t.id, t.phone_hash, t.enrolled_grades, t.available_minutes,
               s.school_code, s.has_printer
        FROM teachers t JOIN schools s ON t.school_id = s.id
        WHERE t.id = $1
    """, teacher_id)
    
    # Get current groups
    groups = await db.fetch("""
        SELECT group_label, child_count, child_ids, target_competency_id, priority_rank
        FROM teaching_groups
        WHERE teacher_id = $1 AND domain_id = $2
          AND effective_until IS NULL
        ORDER BY priority_rank
    """, teacher_id, competency.id.split('.')[0] == 'N' and 'numeracy' or 'r1_literacy')
    
    # Get children's roll numbers for each group
    # (simplified — production would join child table)
    total_children = sum(g['child_count'] for g in groups) if groups else 30
    
    domain_id = 'numeracy' if selected_competency_id.startswith('N') else 'r1_literacy'
    domain_name_hi = 'गणित' if domain_id == 'numeracy' else 'R1 साक्षरता (हिंदी)'
    
    # ── Step 3: L2 Queries ──
    anchor = await fetch_anchor_activity(
        db, domain_id, competency.grade_level, selected_competency_id
    )
    
    # Check if re-teaching needed (from yesterday's evidence)
    reteach_competencies = []
    yesterday_misconception_ids = []
    yesterday = await db.fetch("""
        SELECT DISTINCT unnest(detected_misconception_ids) as misc_id
        FROM assessment_evidence
        WHERE teacher_id = $1 
          AND session_date = $2::date - interval '1 day'
          AND detected_misconception_ids IS NOT NULL
    """, teacher_id, plan_date)
    
    if yesterday:
        yesterday_misconception_ids = [r['misc_id'] for r in yesterday]
    
    intervention = await fetch_intervention(db, yesterday_misconception_ids)
    
    # Get TLMs
    tlm_ids = []
    if intervention and intervention.tlm_ids:
        tlm_ids.extend(intervention.tlm_ids)
    available_tlms = await fetch_tlms(db, tlm_ids)
    
    # Get curriculum week
    week_info = await db.fetchrow("""
        SELECT week_number, topic_title_hi FROM curriculum_weeks
        WHERE plan_id = (SELECT id FROM curriculum_plans WHERE state_id = 'mp' AND is_active = TRUE LIMIT 1)
          AND grade_level = $1 AND domain_id = $2
          AND week_number = EXTRACT(WEEK FROM $3::date) - 26
    """, competency.grade_level, domain_id, plan_date)
    
    # ── Step 4: Assemble context ──
    ctx = OrchestrationContext(
        teacher_name="Teacher",  # Name never sent to Claude (privacy)
        school_code=teacher['school_code'] if teacher else 'DEMO-001',
        enrolled_grades=teacher['enrolled_grades'] if teacher else ['grade_1','grade_2','grade_3'],
        total_children=total_children,
        available_minutes=teacher['available_minutes'] if teacher else 90,
        has_printer=teacher['has_printer'] if teacher else False,
        plan_date=str(plan_date),
        week_number=week_info['week_number'] if week_info else 10,
        week_topic_hi=week_info['topic_title_hi'] if week_info else competency.name_hi,
        selected_competency=competency,
        domain_id=domain_id,
        domain_name_hi=domain_name_hi,
        beginner=GroupInfo(
            label='beginner', count=8,
            roll_numbers=[1,4,7,12,15,18,22,25],
            target_competency=beginner_competency,
        ),
        progressor=GroupInfo(
            label='progressor', count=12,
            roll_numbers=[2,3,5,8,9,13,16,19,20,23,26,28],
            target_competency=competency,
        ),
        proficient=GroupInfo(
            label='proficient', count=10,
            roll_numbers=[6,10,11,14,17,21,24,27,29,30],
            target_competency=proficient_competency,
        ),
        prerequisite_chain=prerequisite_chain,
        misconceptions=misconceptions,
        anchor=anchor,
        intervention=intervention,
        available_tlms=available_tlms,
        reteach_competencies=reteach_competencies,
    )
    
    # ── Step 5: Build prompt and call Claude ──
    system_prompt = build_system_prompt()
    user_prompt = build_user_prompt(ctx)
    
    response = await anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )
    
    # ── Step 6: Parse response ──
    response_text = response.content[0].text
    
    # Strip markdown code fences if present
    if response_text.startswith("```"):
        response_text = response_text.split("\n", 1)[1]
    if response_text.endswith("```"):
        response_text = response_text.rsplit("\n", 1)[0]
    
    plan_json = json.loads(response_text)
    
    # ── Step 7: Store in daily_plans ──
    await db.execute("""
        INSERT INTO daily_plans (teacher_id, plan_date, domain_id, selected_competency_id,
                                 plan_content, explainability, groups_snapshot, claude_model)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (teacher_id, plan_date, domain_id) 
        DO UPDATE SET plan_content = $5, explainability = $6, 
                      groups_snapshot = $7, updated_at = NOW()
    """, 
        teacher_id, plan_date, domain_id, selected_competency_id,
        json.dumps(plan_json, ensure_ascii=False),
        json.dumps(plan_json.get('explainability', {}), ensure_ascii=False),
        json.dumps({
            'beginner': {'count': ctx.beginner.count, 'rolls': ctx.beginner.roll_numbers, 'target': ctx.beginner.target_competency.id},
            'progressor': {'count': ctx.progressor.count, 'rolls': ctx.progressor.roll_numbers, 'target': ctx.progressor.target_competency.id},
            'proficient': {'count': ctx.proficient.count, 'rolls': ctx.proficient.roll_numbers, 'target': ctx.proficient.target_competency.id},
        }),
        "claude-sonnet-4-6"
    )
    
    return plan_json


# ============================================================================
# PROMPT PREVIEW — for testing without Claude API
# ============================================================================

def preview_prompt(ctx: OrchestrationContext) -> dict:
    """Returns both prompts for inspection without calling Claude."""
    return {
        "system_prompt": build_system_prompt(),
        "user_prompt": build_user_prompt(ctx),
        "estimated_tokens": len(build_user_prompt(ctx).split()) * 1.3,  # rough estimate
    }
