"""
Ankur Saathi — Dainik Yojana Orchestration Pipeline
Queries L1 (structured KB) + L2 (content bank) and assembles the Claude prompt.

This is the core function the FastAPI endpoint calls.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Optional

from hindi_style import STYLE_PROMPT          # the Hindi tone rules from Vaishnavi's review (prompts/hindi_style.py)
from cfu_prompt import render_cfu_section, rank_mistakes, CFU_RULES   # check-for-understanding show-me questions in every lesson (prompts/cfu_prompt.py, docs/CFU.md)
from session_shape import session_shape, group_slots, pace_text   # how the session's minutes are shared out (prompts/session_shape.py)


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
    similarity: Optional[float] = None            # semantic: cosine similarity between the skill's vector and the anchor's (1.0 = identical meaning)

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
    
    # Reading passages chosen in code from the content bank, per group (literacy only): {level: {id, title, text, attribution}}
    group_passages: dict = field(default_factory=dict)
    # Texts for each group's independent practice, from the bank: {level: {id, title, text, questions}}
    independent_passages: dict = field(default_factory=dict)
    writing_rules: str = ""          # the rules for groups taught a writing skill (backend/app/services/writing_sheets.py prompt_section)
    
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
    # {group: {competency_id, name_hi, name_en, mistakes: [dict]}}: each group's OWN skill and its recorded mistakes, for the show-me questions AND the worksheets (always set by the server; cfu_kb is the same dict, or None when CFU is off)
    group_mistakes: Optional[dict] = None
    # {group: 'reading' | 'fluency' | 'formation' | 'usage' | 'dictation' | 'composition' | 'observed'} (backend writing_sheets.group_kinds): a group whose kind is not 'reading' (or absent: maths) follows its own sheet section, not the 3 + N sheet
    sheet_kinds: Optional[dict] = None
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
        similarity=(float(row.get('similarity')) if row.get('similarity') is not None else None),
    )


_ANCHOR_COLS = "a.id, a.title_en, a.title_hi, a.theme, a.template_body, a.primary_competency_ids"
_ANCHOR_SPAN = ("COALESCE(array_length(a.primary_competency_ids, 1), 0) "
                "+ COALESCE(array_length(a.secondary_competency_ids, 1), 0)")


# ---- SEMANTIC TIER (24-25 Oct): where the curated ladder has nothing for the skill, choose the anchor NEAREST IN MEANING instead of "the most broadly applicable first".
# The query is the SKILL'S OWN STORED VECTOR (competencies.embedding, loaded by scripts/load_embeddings.py): the running app calls NO embedding service and needs no key.
# A switch, OFF by default: SEMANTIC_RETRIEVAL=on. Any problem (no pgvector, no vectors, an error) falls back to the SQL ladder; it can never raise or poison a transaction.
_SEMANTIC_SQL = f"""
    SELECT {_ANCHOR_COLS}, 1 - (a.embedding <=> c.embedding) AS similarity
    FROM anchor_activities a, competencies c
    WHERE c.id = $3 AND c.embedding IS NOT NULL AND a.embedding IS NOT NULL
      AND a.domain_id = $1 AND $2 = ANY(a.grade_range) AND a.is_active = TRUE
    ORDER BY a.embedding <=> c.embedding ASC, a.id
    LIMIT 1
"""


def semantic_enabled() -> bool:
    return os.environ.get("SEMANTIC_RETRIEVAL", "off").strip().lower() in ("on", "1", "true", "yes")


async def _vectors_ready(db) -> bool:
    """True when the skills and the anchors both have a vector column. Uses catalog lookups that do not raise (a failed query inside a transaction would poison it)."""
    return bool(await db.fetchval("""
        SELECT to_regtype('vector') IS NOT NULL AND (
            SELECT count(*) FROM pg_attribute a JOIN pg_class c ON c.oid = a.attrelid
            WHERE c.relname IN ('competencies', 'anchor_activities') AND c.relkind = 'r' AND a.attname = 'embedding'
              AND NOT a.attisdropped AND a.atttypid = to_regtype('vector')::oid) = 2"""))


async def _semantic_anchor(db, domain_id: str, grade_level: str, competency_id: str) -> Optional[AnchorTemplate]:
    """The anchor valid for this domain and grade whose vector is nearest to the skill's. None if the switch is off, the vectors are not there, or anything goes wrong. Deterministic: ties go to the lower id."""
    if not semantic_enabled():
        return None
    try:
        if not await _vectors_ready(db):
            return None
        async with db.transaction():                    # a SAVEPOINT when already inside a transaction: a failure here cannot poison it
            row = await db.fetchrow(_SEMANTIC_SQL, domain_id, grade_level, competency_id)
    except Exception as e:
        print(f"   Semantic retrieval skipped ({type(e).__name__}): the ladder continues")
        return None
    return _anchor_from_row(row, "semantic") if row else None


async def fetch_anchor_activity(
    db, domain_id: str, grade_level: str,
    competency_id: str
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
      2b. semantic   - ONLY when SEMANTIC_RETRIEVAL=on and the vectors are loaded: the anchor valid for this
                       grade whose meaning is NEAREST to today's skill (cosine similarity of stored vectors).
                       Replaces tiers 3 and 4, the weak ones; tiers 1 and 2 (curated) always come first.
      3. topic_area  - the anchor is written for other competencies in the same topic area
                       (subdomain); prefers the same grade, then the NEAREST competency in
                       the learning sequence (sort_order), then more overlap, then id
      4. loose       - any anchor valid for this grade; the most broadly applicable first
      5. none        - nothing is valid for this grade: returns None
    """
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

    # Tier 2b: semantic (a switch, off by default): nearest in meaning, instead of the two weak tiers below
    sem = await _semantic_anchor(db, domain_id, grade_level, competency_id)
    if sem:
        return sem

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

def build_system_prompt(domain_id: Optional[str] = None, cfu: bool = False) -> str:
    """The system prompt. With a domain_id (what the server sends since prompt v2, step 2) it carries EVERYTHING that is the same from plan
    to plan for that subject: the role, the Hindi style, the show-me rules (when CFU is on), the re-teach rules and the output format. The
    server marks it for prompt caching (build_system_blocks), so repeated plans read it from the cache. The per-plan facts stay in the
    user prompt (build_user_prompt). Without a domain_id: the role only (v1)."""
    if not domain_id:
        return _SYSTEM_ROLE
    parts = [_SYSTEM_ROLE, HINDI_STYLE_SECTION]
    if cfu:
        parts.append(CFU_RULES)
    parts.append("\n## RE-TEACH RULES (use them only when YESTERDAY'S FEEDBACK in the context says the teacher decided to RE-TEACH a group)\n" + RETEACH_MAIN_RULES)
    parts.append(_output_schema(domain_id))
    return "\n".join(parts)


def build_system_blocks(domain_id: str, cfu: bool = False) -> list:
    """The system prompt as the Messages API's list of blocks, the fixed text marked for prompt caching (it must be byte-identical between
    plans to be read from the cache: nothing per-plan may go in it)."""
    return [{"type": "text", "text": build_system_prompt(domain_id, cfu), "cache_control": {"type": "ephemeral"}}]


HINDI_STYLE_SECTION = (
    "\n### HINDI STYLE FOR THE TEACHER'S WORDS\n"
    "- Write the teacher's lines (I Do, We Do, You Do, the script, the CFU questions) as short polite instructions to the teacher, as NCERT's teacher notes do: "
    "'बोर्ड पर लिखें: ...', 'बच्चों से पूछें', 'हर वाक्य दो बार बोलें'. Never the teacher's first person ('मैं ... लिखता/लिखती हूँ', 'मैं बोलूँगा'): the gender "
    "is unknown and paired forms are slow to read in class. What the children do: 'बच्चे कॉपी में लिखें'. Words said to the children go in quotes. In the anchor, "
    "spoken to the children, use 'हम' ('आज हम ... करेंगे'), 'देखो' or 'मेरे पास', never a gendered 'मैं' verb. Write 'शिक्षक', not 'शिक्षिका'.\n"
    "- This holds INSIDE QUOTES too: when the teacher demonstrates aloud, write 'देखिए, अब हम रंग से छाँटते हैं', never 'मैं ... छाँटूँगा', "
    "'मैं ... छाँटूँगी' or 'मैं ... छाँट रही हूँ'. (A sentence written on the board for the children to read may have 'मैं'.)\n"
    "- Write each line once, in its final form: never correct yourself inside a script ('चुपके से... यानी शांति से'): write only 'शांति से'. "
    "Plain Hindi words, not English ones in Devanagari (not 'टंग ट्विस्टर': 'जीभ घुमाने वाला वाक्य').\n"
    "- Name Hindi marks correctly: ै is 'ऐ की मात्रा' (two strokes), े 'ए की मात्रा' (one stroke), ं 'बिंदी' (अनुस्वार), ँ 'चंद्रबिंदु', ः 'विसर्ग'. "
    "Never call ै or े a बिंदी.\n"
    "- Use 'स्वतंत्र अभ्यास' for independent practice.\n"
    "- In place-value and number-reading problems, never print the numeral beside its number word: write 'छत्तीस लिखिए', not 'छत्तीस (36) लिखिए'. "
    "The system writes and checks every Hindi number word from its digits, so do not worry about spelling them.\n"
    "- An example in a problem must never be an answer on the sheet: write 'क्रम की संख्याएँ लिखें', not 'जैसे 3, 1, 2' when the answer is 3, 1, 2.\n"
    "- When sorting or comparing objects, आकार means SIZE (बड़ा/छोटा) and आकृति means SHAPE (गोल, तिकोना, चौकोर, तारा): round things apart from "
    "square ones is 'आकृति का नियम', never 'आकार'; big apart from small is 'आकार का नियम'. Check that each show-me question's expected answer "
    "follows the rule the question names.\n"
    "- A group addressed in an instruction takes the respectful plural, like the whole class: 'शुरुआती समूह अपनी जगह जाएँ', 'प्रगतिशील समूह मेरे "
    "पास आएँ', 'दक्ष समूह छाँटें और बताएँ' (never 'जाए', 'आए', 'छाँटे').\n" + STYLE_PROMPT)


_SYSTEM_ROLE = """You are the Ankur Saathi orchestration engine. You generate a complete Dainik Yojana (daily teaching plan) for an Indian FLN classroom using a station rotation model.

Your role: Generate structured, differentiated teaching plans. Every competency, prerequisite, misconception, and assessment criterion you reference MUST come from the structured context provided. Do not invent curriculum content from training data.

HOW TO WRITE THE PLAN:
1. The teacher decides. Write suggestions a teacher can follow, warmly; never orders about the teacher's own judgment.
2. Each group at its own level: the Beginners work on their prerequisite skill, the Progressors on today's skill with scaffolding, the Proficients go further. Each group's skill and its own mistakes are listed in MISTAKES PER GROUP.
3. A group is taught a NEW skill only in its own teach block. Before that, its independent work is on skills it has already mastered (INDEPENDENT-WORK RULES).
4. How a skill is checked follows its assessment modality: "written" → the worksheet's 3 core problems (photographed after class); "observed" → the teacher watches the group's You Do task (its sheet's own section says what to watch); "oral_reading" → reading aloud, heard and scored by the teacher. Never ask for a photo of an observed skill's practice sheet.
5. All teacher-facing text in Hindi, in the style below. English only where the format asks for it (the *_en fields).
6. The plan must work offline once it is on the phone: never send the teacher to a website, a video or a file.
7. Children are named nowhere: the context gives only counts, and the system adds the roll numbers the teacher needs.

Output format: Return a JSON object with the structure specified in the OUTPUT FORMAT section below. The facts for today's plan (the class, the skills, the groups, the retrieved content, PART A to PART E) are in the user message: wherever these instructions name a section of the context (PART C, the INDEPENDENT-WORK RULES, YESTERDAY'S FEEDBACK, a STICK-BUNDLE POLICY, the WRITING WORKSHEETS section), it is there."""



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
    "independent_activities_hi": {"beginner": "...", "progressor": "...", "proficient": "..."}
  },
  "review_prompts": {
    "photo_sample_rolls": {"beginner": [], "progressor": [], "proficient": []}
  },
  "explainability": {
    "items": [
      {"title_hi": "...", "title_en": "...", "body_hi": "1-2 sentences", "body_en": "1-2 sentences"}
    ]
  }
}

Rules:
- "blocks" must list EVERY segment in time order: anchor, setup ONLY if PART C lists one, a reteach block ONLY if PART C lists one, then the three teach blocks with a transition between them. Use EXACTLY the durations given in PART C: they add up to the session.
- Pace of EVERY teach block (not only a re-teach): PART C gives each block its parts and their minutes. Write the talking points to fit them: an I Do the teacher can finish in its minutes, not a second lesson. A part PART C does not list is left out (with no recall part, say yesterday's point in one sentence at the start of the I Do; with no We Do, the I Do ends with one quick question to the group). The app shows these minutes on the plan.
- "explainability.items" must have 3-4 items covering: why these three groups; why this rotation order; which mistakes to watch; and any assumption specific to today's plan. Do NOT write an item about the retrieved content (anchor, intervention, TLMs) or about the weekly plan: the system adds that item itself, from the facts.
- Independent stations must follow the INDEPENDENT-WORK RULES above. For numeracy, other_groups_hi and every independent activity must NAME the actual practice: two or three example problems at that group's own level (for example 'जैसे 47 + 28, 56 + 35'), never just 'the problems on the board' without saying which; every example obeys the number range of its skill.
- Numbers, prices and names in every group's anchor task must match the board you describe in narration_hi (same item, same price). If a group needs larger numbers, add new items to the board.
- Each group's anchor task must use ONLY that group's own skills (see INDEPENDENT-WORK RULES): no other operations (for example no subtraction or 'how much is left' in an addition lesson). Do not repeat the group's name at the start of the task text, because the screen already shows it.
- MATERIALS other than the TLM-001 sticks: for any hands-on activity, work out the largest total used and make "prep_hi" match it. Give a kit to every group that uses it, size each kit to the largest example, and count the kits from the group sizes above (children divided by children per kit, rounded up). Kits are reused between groups taught at different times, so prepare for the largest need, not the sum. If a STICK-BUNDLE POLICY section is present, it governs the sticks.
- THE 3 + N SHEET (maths sheets, and reading sheets; a sheet whose group has its own section in the context, WRITING WORKSHEETS or a fluency or observed sheet, follows that section instead). Every such worksheet has exactly 3 CORE problems (numbers 1, 2, 3), then exactly the number of EXTRA problems that PART B gives, for children who finish early: never more. "required_count" is 3 on every such sheet, for every group.
- The 3 core problems are the SIGNAL: from them alone the teacher (and the photo analysis) must be able to tell who has the skill and which mistake the others make. Design them in this order: problem 1, the skill in its plainest form; problem 2, built to reveal the FIRST mistake listed for this group's skill (set its diagnostic_for_misconception); problem 3, built to reveal the SECOND listed mistake or, if the skill has only one, the hardest case the skill allows (for a carry sheet: a ones-column sum of exactly 10, or of 15 or more where the range allows). When the group's skill has recorded mistakes, at least 2 of the 3 core problems carry a diagnostic_for_misconception, and NO extra problem does.
- The extras practise the same skill with new numbers (no new difficulty, no new kind of problem).
- The You Do talking point of every group with a 3 + N sheet says to copy and solve problems 1-3 first, and that the rest are extras for those who finish (for example 'पहले वर्कशीट के सवाल 1 से 3 हल करें; जो जल्दी ख़त्म करें, वे बाकी सवाल करें।'). Every statement about a sheet must match: 3 core, then its extras.
- WORKSHEET PROBLEMS MUST BE NEW: none may repeat an example solved in the I Do or We Do talking points (use different numbers). On one sheet no two problems may have the same answer, and the sums must vary: for carry sheets vary the ones-column sum (include one that is exactly 10 and, where the skill allows, one of 15 or more).
- In explainability, refer to worksheet problems by their NUMBER (for example "Progressor problems 1-3"), never by the numbers inside them: the system may replace a problem's numbers after you write.
- instructions_hi and instructions_en must NOT say how many problems are required: the sheet prints that banner itself. Put a word problem's full text in problem_hi only and leave word_problem_text null. On the Progressor sheet the grid problems get a carry cell automatically, so you may tell children to write the carry there.
- All text fields are PLAIN TEXT: no markdown (no **bold**, no # headings). To show a list inside one field, put each item on its own line starting with "• ".
- Every worksheet problem needs an "answer". Use "diagnostic_for_misconception" (an ID listed for THAT sheet's group in MISTAKES PER GROUP, or null) on problems designed to reveal that error. Never put one group's mistake on another group's sheet: each group is checked against its own skill's mistakes.
- A 3 + N sheet has exactly 3 + the extras PART B gives (at most 6 problems, so each sheet fits ONE A4 page); any other sheet at most 8.
- Every problem must have ONE checkable answer (the photo analysis compares against the answer key). Do NOT include open-ended items such as "make your own problem".
- Compute every answer. State which columns carry only after verifying by computing, and never ask for something impossible (e.g. a carry in every column of a 3-digit sum). In a skill whose number range ends at 99, the TOTAL of every sum on the sheet also stays at 99 or less.
- Size each independent activity to the length of the teach block it runs beside (PART C gives the minutes), and say what fast finishers do. Never write a length other than PART C's (no 'about 25 minutes' in a 13-minute block).
- A You Do of 5 minutes or less STARTS the group's task: ask only for what fits (for example the first sentence of the writing task, or one reading of the passage and problem 1), and say that the group finishes the rest at its own place in the next block. Never pack several tasks into a short You Do. Do not label an activity shorter than the block.
"""

_SCHEMA_WORKSHEET_NUMERACY = """
<WORKSHEET> for numeracy:
{
  "instructions_hi": "...", "instructions_en": "...", "required_count": 3,
  "example_block": {"problem_hi": "21 + 15 = ___", "answer": "36", "show_pv_grid": true, "pv_columns": 2,
                    "row1_t": "2", "row1_o": "1", "row2_t": "1", "row2_o": "5", "answer_t": "3", "answer_o": "6"}
                   or null,
  "problems": [
    {"number": 1, "problem_hi": "23 + 14", "answer": "37", "row_type": "grid",
     "show_pv_grid": true, "pv_columns": 2, "pv_row2": true, "diagnostic_for_misconception": null}
  ]
}
Numeracy worksheet rules (scaffolding fades with level):
- beginner: example_block REQUIRED (a worked example of the prerequisite skill). The core 1-3 and every extra: row_type "grid" with show_pv_grid true, pv_columns 2, pv_row2 true. problem_hi has NO "= ___" (the grid is the answer).
- progressor: example_block REQUIRED, and it must show the carry (e.g. 27 + 15 = 42). Core 1-2 row_type "grid" (same fields as above); core 3 row_type "plain" with problem_hi like "19 + 43 = ___", so the group moves off the grid within the core. Extras row_type "plain"; when there are 3 extras the last may be a word problem (row_type null, "answer_type": "wide").
- proficient: example_block null. Core 1-3 row_type "plain" (problem_hi like "57 + 36 = ___"), each with a different carry pattern. Extras: at least one word problem (row_type null, "answer_type": "wide"), the rest "plain".
- Stay inside the number range given in the context. If a number has 3 digits, use pv_columns 3 and add row1_h, row2_h, answer_h to example_block.
"""

_SCHEMA_WORKSHEET_LITERACY = """
<WORKSHEET> for literacy:
{
  "instructions_hi": "...", "instructions_en": "...", "required_count": 3,
  "example_block": {"problem_hi": "मात्रा जोड़ने का उदाहरण:", "example_text": "क + ो = को"} or null,
  "passage_block": {"title": "...", "text": "short passage at grade level"} or null,
  "sheet_kind": "reading|formation|dictation|composition" (only when the WRITING WORKSHEETS section names this group),
  "writing_task": {"topic_hi": "...", "lines": 8} (composition only), "checklist": [{"item_hi": "...", "item_en": "..."}] (composition only),
  "dictation_sentences": ["...", "..."] (dictation only: for the teacher, never printed),
  "problems": [
    {"number": 1, "problem_hi": "...", "answer": "...", "row_type": "plain" or null,
     "answer_type": "box|lines", "answer_lines": <int, only for lines>,
     "show_letter_grid": false, "diagnostic_for_misconception": null}
  ]
}
Literacy worksheet rules:
- beginner: example_block REQUIRED, passage_block null. Q1 may be a letter-tracing item: show_letter_grid true, target_letter "क", letter_grid_cells [{"prefilled": true, "text": "क"}, {"prefilled": false}, ...]. Short-answer items use row_type "plain" (grouped three per row); writing items use row_type null with answer_type "lines".
- A READING sheet is a 3 + N sheet: the first 3 questions are the core (required_count 3), then the extras PART B gives. When BANK QUESTIONS are given for the group's passage, the system places them first, word for word, and they ARE the core: write only the extras.
- progressor (a READING skill): passage_block REQUIRED, example_block null. Short comprehension or matra items row_type "plain"; longer answers row_type null with answer_type "lines".
- proficient (a READING skill): passage_block REQUIRED, example_block null. All items row_type null with answer_type "lines".
- Do not number the passage as a question.
- A group taught a WRITING skill follows the WRITING WORKSHEETS section of the context instead (no passage).
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
    elif a.match_quality == "semantic":
        note = (f"**Match quality: SEMANTIC.** No template in the bank was written for today's competency {today} or for one linked to it in "
                f"the prerequisite graph. This one (written for {designed}) was chosen because its everyday setting is the NEAREST IN MEANING to {today}. "
                f"Keep its story setting and format, but rewrite each group's task so it practises that group's own competency today, and change any "
                f"numbers or objects that do not fit. In explainability, say the anchor was chosen by closeness of meaning (a semantic match), "
                f"not written for this skill.\n")
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
- you_do_hi: do NOT write problems of your own. The group's worksheet IS its try on its own: send the group to the worksheet problems by NUMBER (for example 'वर्कशीट के सवाल 1 से 3 पहले हल करें', using the worksheet's own required count) and say where the teacher visits first. The system writes those problems under the You Do for the teacher, so a list of sums here would be a second, competing list with its own numbering.
- Never repeat a sum between the PARTS of the block: 47 + 36 and 36 + 47 are the SAME sum. The one sum an I Do uses twice is its own: the right working is of the SAME sum as the wrong working. The I Do, each wrong example in We Do and the new example in We Do use a sum of their own and, as far as you can, a different answer from each other, so that a child cannot answer by remembering a number from the board.
- Begin i_do_hi with a very short recall: 'कल हमने क्या सीखा था' (one or two sentences): it is NOT a second lecture. Use NEW numbers, never yesterday's script.
- When the wrong working has been shown and explained, ERASE it at the end of i_do_hi, so that only the right way stays on the board (no big red cross: children remember what they see most). Say so in the talking point.
- Pace for a block of about 27 minutes: recall 2, I Do 6, We Do 7, the show-me questions 4, You Do 8. Follow the pace PART C gives for this block; where it has no recall part, the recall is one sentence at the start of the I Do.
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
            out.append("No specific mistake was recorded for this group: re-teach the skill's commonest mistakes from this group's list in MISTAKES PER GROUP above.")
        out.append("")
    out.append("Write these groups' blocks by the RE-TEACH RULES in the system instructions.")
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


def group_layout(ctx: OrchestrationContext) -> tuple:
    """(shape, rotation_order, {group: {minutes, pace, cfu, note}}): the session's layout for THIS plan, so the prompt, the show-me
    check and the screen's pace use the same numbers. The rotation starts with the priority group (a re-teach group first); at 45 minutes
    the block LENGTHS go by need, a re-taught group taking the longest (prompts/session_shape.py)."""
    shape = session_shape(ctx.available_minutes, separate_reteach=ctx.reteach_groups is None and bool(ctx.reteach_competencies))   # a teacher's decision: no separate block, so no 5 minutes taken from the teaching time
    priority_group, _ = pick_priority_group(ctx.reteach_competencies, ctx.reteach_groups)
    rotation_order = [priority_group] + [g for g in ("beginner", "progressor", "proficient") if g != priority_group]
    slot_of = group_slots(shape, rotation_order, ctx.reteach_groups)
    lay = {g: {"minutes": shape["blocks"][i], "pace": shape["pace"][i], "cfu": shape["cfu"][i], "note": shape["notes"][i]} for g, i in slot_of.items()}
    return shape, rotation_order, lay


def build_user_prompt(ctx: OrchestrationContext) -> str:
    """Assembles the user prompt with all L1 + L2 context injected."""
    
    # Priority group logic
    priority_group, priority_reason = pick_priority_group(ctx.reteach_competencies, ctx.reteach_groups)
    
    # Each group's OWN mistakes, ONE list for the show-me questions and the worksheets (prompt v2, step 4; it replaces the MISCONCEPTION
    # TAXONOMY, which listed only the Progressors' skill). A context made without group_mistakes (an old caller) falls back to that one list.
    group_mistakes = ctx.group_mistakes or {"progressor": {"competency_id": ctx.selected_competency.id, "name_hi": ctx.selected_competency.name_hi,
                                                           "name_en": ctx.selected_competency.name_en, "mistakes": [asdict(m) for m in ctx.misconceptions]}}
    mistakes_text = render_cfu_section(group_mistakes, ctx.cfu_detected, rules=False)
    top_ids = {g: [m["id"] for m in rank_mistakes(kb.get("mistakes") or [], ctx.cfu_detected or {})[:3]] for g, kb in group_mistakes.items()}

    def _sheet_line(g, how):
        kind = (ctx.sheet_kinds or {}).get(g)
        if kind and kind != "reading":
            return f"a {kind.upper()} sheet: follow its own section in this context (not the 3 + N sheet)"
        return f"3 core + {shape['extras']} extra, {how}; {_diag_line(g)}"

    def _diag_line(g):
        ids = (top_ids.get(g) or [])[:2]
        if len(ids) == 2:
            return f"core problem 2 reveals this group's OWN mistake {ids[0]}, core problem 3 reveals {ids[1]}"
        if ids:
            return f"core problem 2 reveals this group's OWN mistake {ids[0]}; core problem 3 is the hardest case the skill allows"
        return "no mistakes are recorded for this group's skill: diagnostic_for_misconception stays null"

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
    
    # Passages chosen in code from the content bank: the model must use them, not invent its own
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

    passages_text += ctx.writing_rules or ""          # writing groups: their sheet rules override the passage rules above

    # Rotation timing: one function (prompts/session_shape.py), shared with the show-me check and the screen (group_layout)
    shape, rotation_order, lay = group_layout(ctx)
    anchor_duration, setup_duration, reteach_duration = shape["anchor"], shape["setup"], shape["reteach"]
    rt_marks = {g: (" — RE-TEACH (see YESTERDAY'S FEEDBACK)" if ctx.reteach_groups and g in ctx.reteach_groups else "") for g in ("beginner", "progressor", "proficient")}
    part_c_blocks = "\n".join(
        f"- Block {n}: TEACH {g} ({lay[g]['minutes']} min){rt_marks[g]}{(' — ' + priority_reason) if n == 1 else ''}\n"
        f"  pace: {pace_text(lay[g]['pace'])}; write 3 show-me questions in the block's \"cfu\" list (the app keeps {lay[g]['cfu']})" + (f"; {lay[g]['note']}" if lay[g]['note'] else "")
        for n, g in enumerate(rotation_order, 1))
    transitions_line = ("- Transitions: " + " min, then ".join(str(t) for t in shape["transition_list"]) + " min"
                        if len(set(shape["transition_list"])) > 1 else f"- Transitions: {shape['transition_list'][0]} min each")
    
    # Top misconception IDs for worksheet design
    anchor_section = _anchor_prompt_section(ctx)
    independent_rules = _independent_rules_section(ctx)
    materials_policy = _materials_policy_section(ctx)
    week_notes_line = (f"**Curriculum note for this topic (state plan):** {ctx.week_notes}\n"
                       if ctx.week_notes else "")
    

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

### शुरुआती (Beginner) — {ctx.beginner.count} children
Working on PREREQUISITE: {ctx.beginner.target_competency.id} — {ctx.beginner.target_competency.name_hi}

### प्रगतिशील (Progressor) — {ctx.progressor.count} children
Working on TODAY'S LAKSHYA with scaffolding: {ctx.progressor.target_competency.id} — {ctx.progressor.target_competency.name_hi}

### दक्ष (Proficient) — {ctx.proficient.count} children
Working on EXTENSION: {ctx.proficient.target_competency.id} — {ctx.proficient.target_competency.name_hi}

{independent_rules}
## PREREQUISITE CHAIN (from L1)
{prereq_text}

{mistakes_text}

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

### PART B: THREE WORKSHEETS (a 3 + N sheet today: 3 core + {shape["extras"]} extra = {shape["sheet_total"]} problems, for a {ctx.available_minutes}-minute session)
- शुरुआती: {ctx.beginner.target_competency.name_hi} — {_sheet_line("beginner", "with visual scaffolding")}
- प्रगतिशील: {ctx.selected_competency.name_hi} — {_sheet_line("progressor", "scaffolding faded")}
- दक्ष: {ctx.proficient.target_competency.name_hi} — {_sheet_line("proficient", "extension, including a word problem among the extras")}
Include answer keys and, on the core problems, the mistake each one reveals.

### PART C: ROTATION SCHEDULE ({ctx.available_minutes} min total)
- Anchor: {anchor_duration} min
{f'- Setup: {setup_duration} min' if setup_duration else '- No setup block today: go straight from the anchor to Block 1.'}
{f'- Re-teach: {reteach_duration} min' if reteach_duration else ''}
{part_c_blocks}
{transitions_line}
Each block: the parts its pace lists, in that order, with Hindi talking points. The minutes above add up to the session.

### PART D: CLASSROOM MANAGEMENT
Rotation chart, transition scripts (Hindi), independent station activities (on PREVIOUSLY MASTERED content only).

### PART E: REVIEW PROMPTS
- Photo sample: leave photo_sample_rolls as empty lists. The system chooses which children to photograph and which children read aloud, and writes the observation reminders.
{passages_text}
Return ONE JSON object in the OUTPUT FORMAT given in the system instructions, following every rule there.
"""
    
    return prompt


# ============================================================================
# PROMPT PREVIEW — for testing without Claude API
# ============================================================================

def preview_prompt(ctx: OrchestrationContext) -> dict:
    """Returns both prompts for inspection without calling Claude."""
    return {
        "system_prompt": build_system_prompt(ctx.domain_id, cfu=bool(ctx.cfu_kb)),
        "user_prompt": build_user_prompt(ctx),
        "estimated_tokens": len(build_user_prompt(ctx).split()) * 1.3,  # rough estimate
    }
