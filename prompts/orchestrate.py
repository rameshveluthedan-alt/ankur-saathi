"""
Ankur Saathi — Dainik Yojana Orchestration Pipeline
Queries L1 (structured KB) + L2 (content bank) and assembles the Claude prompt.

This is the core function the FastAPI endpoint calls.
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Optional

from hindi_style import STYLE_PROMPT          # the Hindi tone rules from Vaishnavi's review (prompts/hindi_style.py)
from cfu_prompt import render_cfu_section      # check-for-understanding show-me questions in every lesson (prompts/cfu_prompt.py, docs/CFU.md)


# ============================================================================
# DATA CLASSES — typed structures for the orchestration context
# ============================================================================

# Stick-bundle kits (TLM-001). Fixed so the prep list is predictable and checkable in code.
STICK_TEACHER_KIT = (9, 9)     # bundles, loose sticks -> 99 sticks
STICK_PAIR_KIT = (4, 9)        # bundles, loose sticks -> 49 sticks (one kit per pair of Beginners)
STICK_TEACHER_KIT_TOTAL = STICK_TEACHER_KIT[0] * 10 + STICK_TEACHER_KIT[1]
STICK_PAIR_KIT_TOTAL = STICK_PAIR_KIT[0] * 10 + STICK_PAIR_KIT[1]


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
    match_quality: str = "exact"                  # exact | related | topic_area | loose | semantic
    designed_for: Optional[list] = None           # competencies this template was written for
    linked_to: Optional[list] = None              # related / topic_area: the competencies that created the match

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
    anchor: Optional[AnchorTemplate]   # None when no template is valid for this grade
    intervention: Optional[InterventionTemplate] = None
    available_tlms: list[TLMRef] = field(default_factory=list)
    
    # Yesterday's feedback
    reteach_competencies: list[dict] = field(default_factory=list)
    # None: the old way (a separate 5-minute re-teach block, written in when yesterday's photos found mistakes).
    # A list (it may be EMPTY): the TEACHER decided at the review. Those groups' MAIN teach block is a focused re-teach, there is NO separate block, and a group that moves on is simply taught.
    reteach_groups: Optional[list] = None
    group_skill_ids: dict = field(default_factory=dict)      # {'beginner': id, 'progressor': id, 'proficient': id}: the skill each group is taught today
    yesterday_analysis: Optional[dict] = None
    
    # Assessment prompts
    observed_competencies: list[dict] = field(default_factory=list)
    orf_scheduled: bool = False
    orf_roll_numbers: list[int] = field(default_factory=list)
    orf_passage_id: Optional[str] = None
    orf_target_cwpm: Optional[int] = None
    # Reading passages chosen in code from the content bank, per group (literacy only): {level: {id, title, text, attribution}}
    group_passages: dict = field(default_factory=dict)
    # Texts for each group's independent practice, from the bank: {level: {id, title, text, questions}}
    independent_passages: dict = field(default_factory=dict)
    
    # Curriculum note for the week that teaches today's competency (from L1)
    week_notes: Optional[str] = None
    # How the intervention template is used: 'reteach' (yesterday's gaps),
    # 'preteach' (no gaps yet: use it proactively for today's competency), or 'none'
    intervention_mode: str = "none"
    # {'beginner': {'safe': [(id, name_hi), ...], 'new': (id, name_hi)}, ...}
    group_skills: Optional[dict] = None
    # check for understanding: {group: {competency_id, name_hi, name_en, mistakes: [dict]}} for each group's OWN skill (None = CFU switched off), and {mistake id: children} detected at the last review
    cfu_kb: Optional[dict] = None
    cfu_detected: Optional[dict] = None
    # {'beginner_children': n, 'pair_kits': k} when TLM-001 (bundling sticks) is in today's content
    stick_policy: Optional[dict] = None


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


def _anchor_from_row(row, quality: str) -> AnchorTemplate:
    return AnchorTemplate(
        id=row['id'], title_en=row['title_en'], title_hi=row['title_hi'],
        theme=row['theme'], template_body=row['template_body'],
        match_quality=quality, designed_for=list(row['primary_competency_ids'] or []),
        linked_to=list(row.get('linked_ids') or []) or None,
    )


_ANCHOR_COLS = "a.id, a.title_en, a.title_hi, a.theme, a.template_body, a.primary_competency_ids"
_ANCHOR_SPAN = ("COALESCE(array_length(a.primary_competency_ids, 1), 0) "
                "+ COALESCE(array_length(a.secondary_competency_ids, 1), 0)")


async def fetch_anchor_activity(
    db, domain_id: str, grade_level: str,
    competency_id: str, query_embedding=None
) -> Optional[AnchorTemplate]:
    """
    L2 retrieval: find the best anchor activity. Fully DETERMINISTIC: the same inputs
    always return the same anchor, so demo behaviour is predictable.

    Tiers, best first. The match quality is recorded so the prompt can tell Claude how
    much adapting the template needs:
      1. exact       - today's competency is listed on the anchor (primary before secondary,
                       then the more specific template, then id)
      2. related     - written for a direct prerequisite or dependent of today's competency
                       (prerequisite graph; hard links weigh double)
      3. topic_area  - the anchor is written for other competencies in the same topic area
                       (subdomain); prefers the same grade, then the NEAREST competency in
                       the learning sequence (sort_order), then more overlap, then id
      4. loose       - any anchor valid for this grade; the most broadly applicable first
      5. none        - nothing is valid for this grade: returns None
    """
    if query_embedding is not None:
        # Semantic retrieval (when embeddings are populated)
        row = await db.fetchrow("""
            SELECT id, title_en, title_hi, theme, template_body, primary_competency_ids,
                   1 - (embedding <=> $3) AS similarity
            FROM anchor_activities
            WHERE domain_id = $1 AND $2 = ANY(grade_range) AND is_active = TRUE
            ORDER BY similarity DESC, id
            LIMIT 1
        """, domain_id, grade_level, query_embedding)
        return _anchor_from_row(row, "semantic") if row else None

    # Tier 1: exact
    row = await db.fetchrow(f"""
        SELECT {_ANCHOR_COLS}
        FROM anchor_activities a
        WHERE a.domain_id = $1 AND $2 = ANY(a.grade_range) AND a.is_active = TRUE
          AND ($3 = ANY(a.primary_competency_ids)
               OR $3 = ANY(COALESCE(a.secondary_competency_ids, '{{}}')))
        ORDER BY CASE WHEN $3 = ANY(a.primary_competency_ids) THEN 0 ELSE 1 END,
                 {_ANCHOR_SPAN}, a.id
        LIMIT 1
    """, domain_id, grade_level, competency_id)
    if row:
        return _anchor_from_row(row, "exact")

    # Tier 2: related - an anchor written for a direct prerequisite or dependent of today's
    # competency (from the prerequisite graph); hard links count double
    row = await db.fetchrow(f"""
        WITH nb AS (
            SELECT prerequisite_id AS nid, CASE prerequisite_type WHEN 'hard' THEN 2 ELSE 1 END AS w
            FROM competency_prerequisites WHERE competency_id = $3
            UNION ALL
            SELECT competency_id AS nid, CASE prerequisite_type WHEN 'hard' THEN 2 ELSE 1 END AS w
            FROM competency_prerequisites WHERE prerequisite_id = $3
        )
        SELECT {_ANCHOR_COLS}, array_agg(DISTINCT nb.nid) AS linked_ids
        FROM anchor_activities a
        JOIN nb ON (nb.nid = ANY(a.primary_competency_ids)
                    OR nb.nid = ANY(COALESCE(a.secondary_competency_ids, '{{}}')))
        WHERE a.domain_id = $1 AND $2 = ANY(a.grade_range) AND a.is_active = TRUE
        GROUP BY a.id
        ORDER BY sum(nb.w) DESC,
                 count(*) FILTER (WHERE nb.nid = ANY(a.primary_competency_ids)) DESC,
                 {_ANCHOR_SPAN}, a.id
        LIMIT 1
    """, domain_id, grade_level, competency_id)
    if row:
        return _anchor_from_row(row, "related")

    # Tier 3: same topic area (subdomain)
    row = await db.fetchrow(f"""
        WITH sel AS (SELECT subdomain_id, grade_level, sort_order FROM competencies WHERE id = $3)
        SELECT {_ANCHOR_COLS}, array_agg(DISTINCT c.id) AS linked_ids
        FROM anchor_activities a
        JOIN sel ON TRUE
        JOIN competencies c
          ON c.subdomain_id = sel.subdomain_id
         AND (c.id = ANY(a.primary_competency_ids)
              OR c.id = ANY(COALESCE(a.secondary_competency_ids, '{{}}')))
        WHERE a.domain_id = $1 AND $2 = ANY(a.grade_range) AND a.is_active = TRUE
        GROUP BY a.id
        ORDER BY (count(*) FILTER (WHERE c.grade_level = sel.grade_level) > 0) DESC,
                 min(abs(c.sort_order - sel.sort_order))
                     FILTER (WHERE c.grade_level = sel.grade_level) ASC NULLS LAST,
                 count(*) DESC, a.id
        LIMIT 1
    """, domain_id, grade_level, competency_id)
    if row:
        return _anchor_from_row(row, "topic_area")

    # Tier 4: loose - the most broadly applicable anchor valid for this grade
    row = await db.fetchrow(f"""
        SELECT {_ANCHOR_COLS}
        FROM anchor_activities a
        WHERE a.domain_id = $1 AND $2 = ANY(a.grade_range) AND a.is_active = TRUE
        ORDER BY {_ANCHOR_SPAN} DESC, a.id
        LIMIT 1
    """, domain_id, grade_level)
    if row:
        return _anchor_from_row(row, "loose")

    return None


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


async def fetch_tlms_for_competencies(db, competency_ids: list[str]) -> list[TLMRef]:
    """L2 deterministic retrieval: TLMs tagged for any of these competencies."""
    if not competency_ids:
        return []
    rows = await db.fetch("""
        SELECT id, name_en, name_hi, availability, diy_instructions
        FROM tlm_references
        WHERE competency_ids && $1::text[] AND is_active = TRUE
        ORDER BY id
    """, competency_ids)
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



# ============================================================================
# OUTPUT SCHEMA — the exact JSON shape the PWA, worksheet renderer and Vision
# analysis read. Without this Claude invents its own nested key names.
# ============================================================================

_SCHEMA_COMMON = """
## OUTPUT FORMAT — return ONE JSON object, nothing else (no markdown fences, no commentary).
Use EXACTLY these key names. Do not rename, nest differently, or add other top-level keys.
Keep every talking point to at most 3 short sentences. Be concise; do not repeat the context back.

{
  "prep_hi": ["one line per thing the teacher must prepare before class (e.g. TLMs to make); [] if nothing"],
  "anchor": {
    "title_hi": "...", "narration_hi": "2-3 sentences the teacher narrates",
    "opening_question_hi": "...",
    "beginner_participation_hi": "...", "progressor_participation_hi": "...", "proficient_participation_hi": "...",
    "closing_question_hi": "..."
  },
  "rotation_schedule": {
    "total_minutes": <int>,
    "blocks": [
      {"type": "anchor|setup|reteach|teach|transition", "time_start": "0:00", "duration_minutes": <int>,
       "teach_group": "beginner|progressor|proficient" (only when type is teach, else null),
       "other_groups_hi": "what the two other groups do meanwhile (teach blocks only, else null)",
       "script_hi": "exact words the teacher says (setup and transition blocks, else null)",
       "talking_points": {"i_do_hi": "...", "we_do_hi": "...", "you_do_hi": "..."} (teach blocks only, else null)}
    ]
  },
  "worksheets": { "beginner": <WORKSHEET>, "progressor": <WORKSHEET>, "proficient": <WORKSHEET> },
  "classroom_management": {
    "peer_monitors": {"beginner": "Roll N", "progressor": "Roll N", "proficient": "Roll N"},
    "independent_activities_hi": {"beginner": "...", "progressor": "...", "proficient": "..."}
  },
  "review_prompts": {
    "photo_sample_rolls": {"beginner": [], "progressor": [], "proficient": []},
    "observation_reminders_hi": ["..."]
  },
  "explainability": {
    "items": [
      {"title_hi": "...", "title_en": "...", "body_hi": "1-2 sentences", "body_en": "1-2 sentences"}
    ]
  }
}

Rules:
- "blocks" must list EVERY segment in time order: anchor, setup, a reteach block ONLY if PART C lists one, then the three teach blocks with a transition between them. Use the durations given in PART C.
- "explainability.items" must have 5-6 items covering: why these three groups; why this rotation order; which misconceptions to watch; WHICH RETRIEVED CONTENT you used and how (name the anchor ID and whether it was an exact, related, topic-area or loose match (or original, if none), the intervention ID, each TLM ID, and the curriculum note); and the assumptions and limitations (the curriculum plan is a representative plan, not the state's official weekly plan). Only say a resource was unavailable if it is genuinely absent from the context above.
- Independent stations must follow the INDEPENDENT-WORK RULES above. For numeracy, other_groups_hi and every independent activity must NAME the actual practice: two or three example problems at that group's own level (for example 'जैसे 47 + 28, 56 + 35'), never just 'the problems on the board' without saying which; every example obeys the number range of its skill.
- Numbers, prices and names in every group's anchor task must match the board you describe in narration_hi (same item, same price). If a group needs larger numbers, add new items to the board.
- Each group's anchor task must use ONLY that group's own skills (see INDEPENDENT-WORK RULES): no other operations (for example no subtraction or 'how much is left' in an addition lesson). Do not repeat the group's name at the start of the task text, because the screen already shows it.
- MATERIALS other than the TLM-001 sticks: for any hands-on activity, work out the largest total used and make "prep_hi" match it. Give a kit to every group that uses it, size each kit to the largest example, and count the kits from the group sizes above (children divided by children per kit, rounded up). Kits are reused between groups taught at different times, so prepare for the largest need, not the sum. If a STICK-BUNDLE POLICY section is present, it governs the sticks.
- "required_count": children must do problems 1 to required_count; later problems are extras for fast finishers. Beginner sheet with more than 5 problems: required_count 5. Progressor sheet with more than 6 problems: required_count 6. Proficient: required_count = the number of problems. Every problem with a "diagnostic_for_misconception" must be among the required ones. The Beginner You Do talking point must say to copy and solve problems 1-5 first, and the Progressor You Do problems 1-6 first, and that the rest are extras; every statement about a sheet must match its required_count.
- WORKSHEET PROBLEMS MUST BE NEW: none may repeat an example solved in the I Do or We Do talking points (use different numbers). On one sheet no two problems may have the same answer, and the sums must vary: for carry sheets vary the ones-column sum (include one that is exactly 10 and, where the skill allows, one of 15 or more).
- In explainability, refer to worksheet problems by their NUMBER (for example "Progressor problems 1-3"), never by the numbers inside them: the system may replace a problem's numbers after you write.
- instructions_hi and instructions_en must NOT say how many problems are required: the sheet prints that banner itself. Put a word problem's full text in problem_hi only and leave word_problem_text null. On the Progressor sheet the grid problems get a carry cell automatically, so you may tell children to write the carry there.
- All text fields are PLAIN TEXT: no markdown (no **bold**, no # headings). To show a list inside one field, put each item on its own line starting with "• ".
- Every worksheet problem needs an "answer". Use "diagnostic_for_misconception" (an ID from the misconception list, or null) on problems designed to reveal that error.
- At most 8 problems per worksheet, so each sheet fits ONE A4 page. Fewer than 8 is fine.
- Every problem must have ONE checkable answer (the photo analysis compares against the answer key). Do NOT include open-ended items such as "make your own problem".
- Compute every answer. State which columns carry only after verifying by computing, and never ask for something impossible (e.g. a carry in every column of a 3-digit sum). In a skill whose number range ends at 99, the TOTAL of every sum on the sheet also stays at 99 or less.
- Size each independent activity to the length of the teach blocks (22-29 minutes), and say what fast finishers do. Do not label an activity shorter than the block.
"""

_SCHEMA_WORKSHEET_NUMERACY = """
<WORKSHEET> for numeracy:
{
  "instructions_hi": "...", "instructions_en": "...", "required_count": 5,
  "example_block": {"problem_hi": "21 + 15 = ___", "answer": "36", "show_pv_grid": true, "pv_columns": 2,
                    "row1_t": "2", "row1_o": "1", "row2_t": "1", "row2_o": "5", "answer_t": "3", "answer_o": "6"}
                   or null,
  "problems": [
    {"number": 1, "problem_hi": "23 + 14", "answer": "37", "row_type": "grid",
     "show_pv_grid": true, "pv_columns": 2, "pv_row2": true, "diagnostic_for_misconception": null}
  ]
}
Numeracy worksheet rules (scaffolding fades with level):
- beginner: example_block REQUIRED (a worked example of the prerequisite skill). All problems row_type "grid" with show_pv_grid true, pv_columns 2, pv_row2 true. problem_hi has NO "= ___" (the grid is the answer). Up to 8 problems.
- progressor: example_block REQUIRED, and it must show the carry (e.g. 27 + 15 = 42). Problems 1-3 row_type "grid" (same fields as above); problems 4-6 row_type "plain" with problem_hi like "19 + 43 = ___"; then 1-2 word problems with row_type null, "answer_type": "wide", and "word_problem_text" repeating the problem text.
- proficient: example_block null. Problems 1-6 row_type "plain" (problem_hi like "57 + 36 = ___"); then 2 word problems with row_type null, "answer_type": "wide", "word_problem_text".
- Stay inside the number range given in the context. If a number has 3 digits, use pv_columns 3 and add row1_h, row2_h, answer_h to example_block.
- Place at least 2 problems that reveal the top misconceptions, and set diagnostic_for_misconception on them.
"""

_SCHEMA_WORKSHEET_LITERACY = """
<WORKSHEET> for literacy:
{
  "instructions_hi": "...", "instructions_en": "...", "required_count": 5,
  "example_block": {"problem_hi": "मात्रा जोड़ने का उदाहरण:", "example_text": "क + ो = को"} or null,
  "passage_block": {"title": "...", "text": "short passage at grade level"} or null,
  "problems": [
    {"number": 1, "problem_hi": "...", "answer": "...", "row_type": "plain" or null,
     "answer_type": "box|lines", "answer_lines": <int, only for lines>,
     "show_letter_grid": false, "diagnostic_for_misconception": null}
  ]
}
Literacy worksheet rules:
- beginner: example_block REQUIRED, passage_block null. Q1 may be a letter-tracing item: show_letter_grid true, target_letter "क", letter_grid_cells [{"prefilled": true, "text": "क"}, {"prefilled": false}, ...]. Short-answer items use row_type "plain" (grouped three per row); writing items use row_type null with answer_type "lines".
- progressor: passage_block REQUIRED, example_block null. Short comprehension or matra items row_type "plain"; longer answers row_type null with answer_type "lines".
- proficient: passage_block REQUIRED, example_block null. All items row_type null with answer_type "lines".
- Do not number the passage as a question.
"""


def _output_schema(domain_id: str) -> str:
    ws = _SCHEMA_WORKSHEET_NUMERACY if domain_id == "numeracy" else _SCHEMA_WORKSHEET_LITERACY
    return _SCHEMA_COMMON + ws


def _anchor_prompt_section(ctx: OrchestrationContext) -> str:
    """The anchor section of the prompt, worded according to how well the template matches."""
    a = ctx.anchor
    today = ctx.selected_competency.id
    if a is None:
        return (
            "### Anchor Activity Template\n"
            "**No anchor template is available for today's competency and grade.** Write a short ORIGINAL "
            "10-minute anchor in the same style: a simple story or situation, one whole-class opening question, "
            "and one task per group matched to that group's competency. In the explainability item about "
            "retrieved content, say that no template matched and that the anchor is original.\n"
        )
    head = f"### Anchor Activity Template\n**{a.id}** — {a.title_hi} (Theme: {a.theme})\n"
    body = f"```\n{a.template_body}\n```\n"
    designed = ", ".join(a.designed_for or []) or "other content"
    linked = ", ".join(a.linked_to or [])
    if a.match_quality == "related":
        note = (f"**Match quality: RELATED.** This template was written for {designed} and also covers {linked}, "
                f"linked to today's competency {today} in the prerequisite graph (as a "
                f"prerequisite or a follow-on). It does not cover {today} itself. Keep the story, but rewrite each "
                f"group's task so it practises that group's own competency today. In explainability, say the "
                f"anchor was a related (not exact) match.\n")
    elif a.match_quality == "topic_area":
        note = (f"**Match quality: TOPIC-AREA.** This template was written for {designed} and also covers {linked}, "
                f"in the same topic area as today's {today} but a different skill. Keep the story, but rewrite each "
                f"group's task so it practises that group's own competency today. In explainability, say the "
                f"anchor was a topic-area (not exact) match.\n")
    elif a.match_quality == "loose":
        note = (f"**Match quality: LOOSE.** This template was written for different content ({designed}); nothing "
                f"in the bank matches {today}. Keep only its story setting and format; rewrite every group's task "
                f"so it practises that group's competency today. In explainability, state clearly that no anchor "
                f"matched today's competency and this one was adapted loosely.\n")
    elif a.match_quality == "exact":
        note = ("**Match quality: EXACT.** This template was written for today's competency " + today +
                ". Adapt it for today's number range and fill all {{placeholders}}. In explainability, "
                "say the anchor was an exact match.\n")
    else:
        note = "Adapt this for today's competency and number range. Fill all {{placeholders}}.\n"
    return head + body + note


def _independent_rules_section(ctx: OrchestrationContext) -> str:
    """Names, per group, what is safe to practise alone and what is new today."""
    gs = ctx.group_skills
    if not gs:
        return ""
    names = {"beginner": "शुरुआती (Beginner)", "progressor": "प्रगतिशील (Progressor)", "proficient": "दक्ष (Proficient)"}
    lines = ["## INDEPENDENT-WORK RULES (what the two groups NOT with the teacher may do)",
             "Each group is taught its NEW skill only in its own teach block. Before that, no group may work on",
             "ANY of the new skills below, not even as an extra for fast finishers.", ""]
    for g in ("beginner", "progressor", "proficient"):
        safe = "; ".join(f"{i} — {n}" for i, n in gs[g]["safe"]) or "(none identified: use a simple review of earlier skills)"
        new_id, new_name = gs[g]["new"]
        lines.append(f"- {names[g]}: ALREADY MASTERED, use for independent work: {safe}.  "
                     f"NEW today, taught only in its own teach block: {new_id} — {new_name}.")
    lines += ["", "Once a group's own teach block has finished, that group's NEW skill counts as taught: later blocks should use it "
              "for consolidation (for example the Progressors practise the carry in the last block).",
              "", "Independent work must be at the group's OWN level (its mastered skill above), not easier. "
              "Fast finishers get more problems of the same mastered skill or check a partner's work, never a new skill.", ""]
    return "\n".join(lines)


def _materials_policy_section(ctx: OrchestrationContext) -> str:
    """Fixed rules for bundling sticks: who handles them, kit sizes, and what the prep list must say."""
    sp = ctx.stick_policy
    if not sp:
        return ""
    n, k = sp["beginner_children"], sp["pair_kits"]
    tb, tl = STICK_TEACHER_KIT
    pb, pl = STICK_PAIR_KIT
    total = STICK_TEACHER_KIT_TOTAL + k * STICK_PAIR_KIT_TOTAL
    return f"""
### STICK-BUNDLE (TLM-001) POLICY: follow exactly
- The teacher's demonstration is the main use of sticks. Each I Do that teaches with sticks is done by the teacher, to that group only, inside that group's own teach block: explain every step aloud and draw the same step on the board (tens as vertical lines, ones as dots).
- TEACHER DEMO KIT (always list it in prep_hi): {tb} bundles + {tl} loose sticks = {STICK_TEACHER_KIT_TOTAL} sticks. Every teacher demonstration with sticks must total at most {STICK_TEACHER_KIT_TOTAL}. The kit holds spare pre-made bundles: when 10 loose sticks must become a ten, the teacher (or one child at the teacher's kit) EXCHANGES them for a spare bundle. Never say "tie" or "make" a new bundle, and never ask for rubber bands in class.
- BEGINNER group ({n} children): hands-on in PAIRS. Pair kit = {pb} bundles + {pl} loose sticks = {STICK_PAIR_KIT_TOTAL} sticks, so {k} kits (children divided by 2, rounded up) = {k * pb} bundles + {k * pl} loose sticks. Every example or number the Beginners build with sticks must total at most {STICK_PAIR_KIT_TOTAL} (for the Beginners' skill: no carrying or borrowing), and so must the first two worksheet problems. They use sticks only for those first two problems, then DRAW, then use the grid. No free play: bundles are made before class, never during the lesson; sticks are counted back in at the end; the group monitor collects.
- PROGRESSOR group: NO kits for children. In the We Do, one child comes to the teacher's kit and does the one key step (adding: trading 10 loose sticks for a bundle; subtracting: opening a bundle into 10 loose sticks) while every other child draws tens as lines and ones as dots in a Tens | Ones frame ruled in the notebook, and circles 10 dots to make a new line (or crosses one line out to borrow). In the You Do the first problems may be drawn beside the grid; the last ones use numerals only.
- PROFICIENT group: no sticks and no kits. Use the written method on the board with the carry written in each column.
- prep_hi must list exactly the teacher demo kit and the {k} Beginner pair kits, and nothing else made of sticks. Total sticks to prepare: {STICK_TEACHER_KIT_TOTAL} + {k} x {STICK_PAIR_KIT_TOTAL} = {total}. Also say to rule a Tens | Ones frame on a sheet or the notebook cover for each pair.
- In the talking points write each example PLAINLY: NEVER explain the kit size or a stick limit there (prep_hi carries it). Choose examples that fit the kit and say nothing about the limit.
"""


GROUP_ORDER = ("beginner", "progressor", "proficient")           # furthest behind first: the tie-break


def choose_reteach_group(children_by_group: dict) -> str:
    """The group a re-teach is FOR: the one with the most children who made the mistake. A tie goes to the group furthest behind. If none of the
    children can be placed in a group (a level changed since the review), the Progressors, because today's skill is theirs."""
    best = max(children_by_group.values(), default=0)
    if best <= 0:
        return "progressor"
    return next(g for g in GROUP_ORDER if children_by_group.get(g, 0) == best)


def pick_priority_group(reteach_items: list, reteach_groups: Optional[list] = None) -> tuple:
    """(group taught first, why). With no re-teach it is the Beginners, as before. With one, it is the group whose children made the most of the
    mistakes: several items are added up by group. It used to be 'the Progressors' whatever group the children were in."""
    if reteach_groups is not None:                         # the teacher decided: of the groups being re-taught, the one with most children who made a mistake; none: the Beginners, as before
        if not reteach_groups:
            return "beginner", "Default: Beginners get first slot for prerequisite foundation."
        weights = {g: 0 for g in reteach_groups}
        for r in reteach_items:
            for g, n in (r.get("affected_by_group") or {}).items():
                if g in weights:
                    weights[g] += n
        best = max(weights.values())
        group = next(g for g in GROUP_ORDER if g in weights and weights[g] == best)
        return group, f"The teacher chose to re-teach the {group.title()} group, so their main block is a focused re-teach, and they are taught first."
    if not reteach_items:
        return "beginner", "Default: Beginners get first slot for prerequisite foundation."
    weights = {}
    for r in reteach_items:
        g = r.get("group", "progressor")
        weights[g] = weights.get(g, 0) + (r.get("affected_count") or 1)
    group = choose_reteach_group(weights)
    return group, f"The last review found mistakes mainly in the {group.title()} group, so they are taught first, after a short re-teach."


# THE SHAPE OF A RE-TEACH BLOCK. One place, so it can be tuned after the teachers' review (Part D of the review document: the wrong-then-right sequence, the timings).
RETEACH_MAIN_RULES = """For a RE-TEACH group the group's own teach block IS the re-teach: it is NOT the first lesson again, and there is NO separate re-teach block. Write its talking_points like this:
- i_do_hi: show the mistake FIRST, then the right way. Do one worked example the way a child with the mistake would do it (the wrong working or the wrong answer), say aloud what is wrong with it, then do the SAME sum again correctly (the same numbers, first the way the mistake does it, then the right way: that is the contrast).
- we_do_hi: the children FIND AND FIX the mistake: give them one or two wrong examples (the mistakes listed for the group) to correct with you, then one new example together.
- you_do_hi: do NOT write problems of your own. The group's worksheet IS its try on its own: send the group to the worksheet problems by NUMBER (for example 'वर्कशीट के सवाल 1 से 6 पहले हल करें', using the worksheet's own required count) and say where the teacher visits first. The system writes those problems under the You Do for the teacher, so a list of sums here would be a second, competing list with its own numbering.
- Never repeat a sum between the PARTS of the block: 47 + 36 and 36 + 47 are the SAME sum. The one sum an I Do uses twice is its own: the right working is of the SAME sum as the wrong working. The I Do, each wrong example in We Do and the new example in We Do use a sum of their own and, as far as you can, a different answer from each other, so that a child cannot answer by remembering a number from the board.
- Begin i_do_hi with a very short recall: 'कल हमने क्या सीखा था' (one or two sentences): it is NOT a second lecture. Use NEW numbers, never yesterday's script.
- When the wrong working has been shown and explained, ERASE it at the end of i_do_hi, so that only the right way stays on the board (no big red cross: children remember what they see most). Say so in the talking point.
- Pace for a block of about 27 minutes: recall 2, I Do 6, We Do 7, the show-me questions 4, You Do 8. Scale it to this block's length.
- In you_do_hi the teacher visits FIRST the children who made the mistake, quietly, as part of the normal round: never call out their names or roll numbers.
- If more than a quarter of the group shows a wrong answer in the show-me, the teacher re-teaches that step at once, with sticks, before You Do: it is not a few children's slip.
- Name no child. The check-for-understanding questions of this block aim at the listed mistakes.
- A group that is NOT being re-taught is simply taught its skill, as usual."""


def render_reteach_main(ctx) -> str:
    """YESTERDAY'S FEEDBACK when the teacher decided. Only counts and groups: never a child's roll number (the code stamps those into the block afterwards)."""
    groups = [g for g in GROUP_ORDER if g in (ctx.reteach_groups or [])]
    if not groups:
        return ("The teacher decided to MOVE ON with every group: there is NO re-teach block, and no group is re-taught from yesterday's mistakes: each group is taught its own skill as a NORMAL lesson "
                "(a group that is on yesterday's skill again is taught it as a normal lesson, not as a re-teach). "
                "(Any mistakes found at the last review are aimed at by the check-for-understanding questions.)")
    comp = {"beginner": ctx.beginner.target_competency, "progressor": ctx.selected_competency, "proficient": ctx.proficient.target_competency}
    out = ["The teacher decided at the review to RE-TEACH: " + ", ".join(g.upper() for g in groups) + ". There is NO separate re-teach block: for these groups the main TEACH block is the re-teach.\n"]
    for g in groups:
        skill_id = (ctx.group_skill_ids or {}).get(g) or comp[g].id
        out.append(f"### {g.upper()}: {skill_id} {comp[g].name_hi}")
        found = [(r, (r.get("affected_by_group") or {}).get(g, 0)) for r in ctx.reteach_competencies if r.get("competency_id") == skill_id]
        found = [(r, n) for r, n in found if n > 0]
        if found:
            out.append("Mistakes found at the last review in this group:")
            out.extend(f"- {r['misconception_id']}: {r['misconception_name_hi']} ({n} children)" for r, n in found)
        else:
            out.append("No specific mistake was recorded for this group: re-teach the skill's commonest mistakes from the MISCONCEPTION TAXONOMY above.")
        out.append("")
    out.append(RETEACH_MAIN_RULES)
    return "\n".join(out)


def range_note(number_range) -> str:
    """One sentence under the skill's number range: the knowledge base's maximum limits every number written for the skill AND the total of every addition (found on the second real block: the range said
    max 99, the model read it as a limit on the numbers added, and a worksheet problem was 79 + 21 = 100). Empty when the skill has no maximum."""
    try:
        mx = int((number_range or {}).get("max"))
    except (TypeError, ValueError, AttributeError):
        return ""
    extra = f" A two-digit skill never reaches 100: three-digit numbers belong to the Proficients' later skill, so 79 + 21 = 100 is NOT allowed here." if mx <= 99 else ""
    return f"(Today's skill stays inside this range: every number you write for it, and the TOTAL of every addition, is at most {mx}.{extra})"


def build_user_prompt(ctx: OrchestrationContext) -> str:
    """Assembles the user prompt with all L1 + L2 context injected."""
    
    # Priority group logic
    priority_group, priority_reason = pick_priority_group(ctx.reteach_competencies, ctx.reteach_groups)
    
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
    if ctx.reteach_groups is not None:                       # the teacher decided: a re-teach is the group's MAIN block
        reteach_text = render_reteach_main(ctx)
    elif ctx.reteach_competencies:
        reteach_text = "The last review's gaps require a 5-minute re-teaching segment:\n"
        for r in ctx.reteach_competencies:
            reteach_text += f"- {r['competency_id']}: {r['misconception_name_hi']} ({r['affected_count']} children, in the {r.get('group', 'progressor').upper()} group: the re-teach is FOR them)\n"
    else:
        reteach_text = "No re-teaching needed from the last review."
    
    # Build intervention section
    intervention_text = ""
    if ctx.intervention and ctx.intervention_mode == "preteach":
        mode_note = ("**How to use it:** No gaps were recorded yesterday, so there is NO re-teach block. "
                     "Use this template PROACTIVELY as the teaching model for the group whose target is today's "
                     "competency (Progressor): build their I Do / We Do around these steps so the listed "
                     "misconceptions are prevented, not just corrected later.\n")
    elif ctx.intervention and ctx.reteach_groups:
        mode_note = "**How to use it:** use this for the MAIN block of each re-teach group (see YESTERDAY'S FEEDBACK). There is no separate re-teach segment.\n"
    elif ctx.intervention:
        mode_note = "**How to use it:** use this for the re-teach segment described in PART C.\n"
    else:
        mode_note = ""

    if ctx.intervention:
        intervention_text = mode_note + f"""
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
    else:
        tlm_text += ("\nUse a TLM from this list wherever it helps the teaching, name it in the talking points, "
                     "and for every 'diy' TLM add a one-line preparation note to \"prep_hi\" "
                     "(what to make before class and how many).\n")
    
    # Build observation reminders
    obs_text = ""
    if ctx.observed_competencies:
        for oc in ctx.observed_competencies:
            obs_text += f"  - {oc['id']}: {oc['name_hi']} — for Roll Nos. {oc['target_roll_numbers']}\n"
    
    # Passages chosen in code from the content bank: the model must use them, not invent its own
    cfu_text = render_cfu_section(ctx.cfu_kb, ctx.cfu_detected) if ctx.cfu_kb else ""        # empty when CFU is switched off: the plan is then as before
    hindi_style_text = (
        "\n### HINDI STYLE FOR THE TEACHER'S WORDS\n"
        "- Write the teacher's first person without gender: use 'पढ़ता/पढ़ती हूँ' or 'हम पढ़ते हैं', never only the feminine forms, and write 'शिक्षक', not 'शिक्षिका'.\n"
        "- Use 'स्वतंत्र अभ्यास' for independent practice.\n"
        "- In place-value and number-reading problems, never print the numeral beside its number word: write 'छत्तीस लिखिए', not 'छत्तीस (36) लिखिए'. "
        "The system writes and checks every Hindi number word from its digits, so do not worry about spelling them.\n" + STYLE_PROMPT)
    passages_text = ""
    if ctx.group_passages:
        passages_text = "\n### FIXED READING PASSAGES (from the content bank: do NOT invent or change a passage)\n"
        for level, ps in ctx.group_passages.items():
            passages_text += (f"- {level} worksheet: passage_id {ps['id']}, title \"{ps['title']}\" ({ps['word_count']} words)\n"
                              f"  TEXT: {ps['text']}\n")
        passages_text += ("Rules: set each worksheet's passage_block to exactly the title and text above (the system will also overwrite it), "
                          "and write the comprehension questions about THAT passage only, using only facts stated in it.\n")
        banked = {lvl: ps["questions"] for lvl, ps in ctx.group_passages.items() if ps.get("questions")}
        if banked:
            passages_text += "\n### BANK QUESTIONS (checked against the passage: the system places them FIRST on the worksheet, word for word, with these answers)\n"
            for lvl, qs in banked.items():
                passages_text += f"- {lvl}:\n" + "".join(f"    {n}. {q['question_hi']}  ->  {q['answer_hi']}\n" for n, q in enumerate(qs, 1))
            passages_text += "Write only the REMAINING questions yourself, and do not repeat these.\n"
        passages_text += ("\n### KEEP LESSON AND WORKSHEET APART\n"
                          "- Never reuse in a worksheet a question, an example or an answer that you model in the I Do or We Do: model with a different part of the passage.\n"
                          "- Never reuse the anchor story in a worksheet. The Beginner worksheet stories must be NEW short stories, and the Beginner instruction must say the teacher tells each story aloud.\n")
        if ctx.independent_passages:
            passages_text += "\n### INDEPENDENT-PRACTICE PASSAGES (from the bank: the teacher writes these on the board; do NOT invent other texts)\n"
            for lvl, ps in ctx.independent_passages.items():
                qs = ps["questions"][:3]
                passages_text += (f"- {lvl} group, while the teacher is with another group: \"{ps['title']}\" ({ps['id']})\n  TEXT: {ps['text']}\n"
                                  + "".join(f"  Question {n}: {q['question_hi']}\n" for n, q in enumerate(qs, 1)))
            passages_text += ("Rules: in every teach block's other_groups_hi and in classroom_management.independent_activities_hi, send these groups to THEIR passage "
                              "by its title and tell them to answer its listed questions. Do not mention any other independent text.\n")

    # Compute rotation timing
    anchor_duration = 10
    setup_duration = 2
    reteach_duration = 0 if ctx.reteach_groups is not None else (5 if ctx.reteach_competencies else 0)      # a teacher's decision: no separate block, so no 5 minutes taken from the teaching time
    rt_marks = {g: (" — RE-TEACH (see YESTERDAY'S FEEDBACK)" if ctx.reteach_groups and g in ctx.reteach_groups else "") for g in ("beginner", "progressor", "proficient")}
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
    anchor_section = _anchor_prompt_section(ctx)
    independent_rules = _independent_rules_section(ctx)
    materials_policy = _materials_policy_section(ctx)
    week_notes_line = (f"**Curriculum note for this topic (state plan):** {ctx.week_notes}\n"
                       if ctx.week_notes else "")
    
    output_schema = _output_schema(ctx.domain_id)

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
{week_notes_line}
A/PA/NA Criteria:
```json
{json.dumps(ctx.selected_competency.apna_criteria, ensure_ascii=False, indent=2)}
```

Number range: {json.dumps(ctx.selected_competency.number_range, ensure_ascii=False) if ctx.selected_competency.number_range else 'N/A'}
{range_note(ctx.selected_competency.number_range)}
Problem types: {', '.join(ctx.selected_competency.problem_types) if ctx.selected_competency.problem_types else 'General'}

## THREE GROUPS

### शुरुआती (Beginner) — {ctx.beginner.count} children (Roll: {ctx.beginner.roll_numbers})
Working on PREREQUISITE: {ctx.beginner.target_competency.id} — {ctx.beginner.target_competency.name_hi}

### प्रगतिशील (Progressor) — {ctx.progressor.count} children (Roll: {ctx.progressor.roll_numbers})
Working on TODAY'S LAKSHYA with scaffolding: {ctx.progressor.target_competency.id} — {ctx.progressor.target_competency.name_hi}

### दक्ष (Proficient) — {ctx.proficient.count} children (Roll: {ctx.proficient.roll_numbers})
Working on EXTENSION: {ctx.proficient.target_competency.id} — {ctx.proficient.target_competency.name_hi}

{independent_rules}
## PREREQUISITE CHAIN (from L1)
{prereq_text}

## MISCONCEPTION TAXONOMY (from L1)
{misconception_text}

## YESTERDAY'S FEEDBACK
{reteach_text}

## RETRIEVED CONTENT (from L2)

{anchor_section}
### Intervention Template
{intervention_text}

### Available TLMs
{tlm_text}
{materials_policy}

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
- Block 1: TEACH {rotation_order[0]} ({priority_duration} min){rt_marks[rotation_order[0]]} — {priority_reason}
- Block 2: TEACH {rotation_order[1]} ({standard_duration} min){rt_marks[rotation_order[1]]}
- Block 3: TEACH {rotation_order[2]} ({standard_duration} min){rt_marks[rotation_order[2]]}
- Transitions: 2 min each
Each block: I Do → We Do → You Do with Hindi talking points.

### PART D: CLASSROOM MANAGEMENT
Rotation chart, peer monitors, transition scripts (Hindi), independent station activities (on PREVIOUSLY MASTERED content only).

### PART E: REVIEW PROMPTS
- Photo sample: leave photo_sample_rolls as empty lists. The system chooses which children to photograph
- Observation: {obs_text if obs_text else 'No observed-modality competencies today.'}
{'- ORF: Roll Nos. ' + str(ctx.orf_roll_numbers) + ' on passage ' + ctx.orf_passage_id if ctx.orf_scheduled else ''}
{passages_text}
{hindi_style_text}
{cfu_text}
{output_schema}
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
