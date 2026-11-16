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
from app.services import ai_budget, writing_sheets

from app.core.config import get_settings
from app.services.plan_service import get_current_groups, _pick_passage

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'prompts'))
from vision_analysis import (
    VISION_SYSTEM_PROMPT, build_vision_prompt,
    process_vision_results, today_group_result,
)


# Sonnet 5.5 thinks by default and thinking tokens share max_tokens with the answer.
# "between_tools" turns off up-front thinking (see plan_service.py for details).
# Revisit once we test with real worksheet photos: handwriting extraction may
# benefit from some thinking, in which case use adaptive + output_config effort.
CLAUDE_THINKING_BODY = {"thinking": {"type": "between_tools"}}


async def record_teacher_decisions(db, teacher_id: str, plan_date: date, domain_id: str, decisions: dict, stage: str = "first"):
    """
    Store the teacher's Advance/Re-teach/Not-sure decisions per group, at one of two stages of the Review:
      'first': her judgment BEFORE looking at the children's work (independent of the AI's reading), kept as teacher_first_<group>;
      'final': her decision AFTER looking at it (step 3, with today's evidence in front of her), kept as teacher_final_<group>.
    Either becomes the group's current decision, teacher_decision_<group>: what tomorrow's plan suggests from. The latest statement wins,
    so a review stopped after step 1 still has a decision.
    """
    stage_key = 'teacher_final_' if stage == 'final' else 'teacher_first_'
    for group_label, decision in decisions.items():
        if decision not in ('advance', 'reteach', 'not_sure'):
            continue
        for key in (f'teacher_decision_{group_label}', f'{stage_key}{group_label}'):
            await _store_decision(db, teacher_id, plan_date, domain_id, key, decision)
    return {"status": "recorded", "stage": stage, "decisions": decisions}


async def _store_decision(db, teacher_id: str, plan_date: date, domain_id: str, key: str, decision: str):
    """Write one decision key into the day's plan (its explainability): a session-level record, so it exists before any evidence does."""
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
        [key], decision)


async def record_observed_assessments(db, teacher_id: str, session_date: date, items: list[dict]):
    """
    Store teacher-observed A/PA/NA assessments.
    Channel: 'observed' — teacher taps judgment in real-time during teaching.
    """
    recorded = 0
    results, not_found = [], []           # per child: what was recorded and what it replaced (new / changed / unchanged); rolls not in the class
    for item in items:
        child = await db.fetchrow("""
            SELECT id FROM children 
            WHERE teacher_id = $1 AND roll_number = $2 AND is_active = TRUE
        """, teacher_id, item['roll_number'])
        
        if not child:
            not_found.append(item['roll_number'])          # never counted as saved
            continue

        previous = await db.fetchval("""
            SELECT status FROM assessment_evidence
            WHERE child_id = $1 AND competency_id = $2 AND session_date = $3 AND channel = 'observed'
            ORDER BY created_at DESC LIMIT 1
        """, child['id'], item['competency_id'], session_date)
        outcome = "new" if previous is None else ("unchanged" if previous == item['status'] else "changed")
        results.append({"roll_number": item['roll_number'], "status": item['status'], "previous": previous, "outcome": outcome})
        
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
    
    count = lambda o: sum(1 for r in results if r["outcome"] == o)
    return {"status": "recorded", "items_recorded": recorded, "results": results,
            "new": count("new"), "changed": count("changed"), "unchanged": count("unchanged"), "not_found": not_found}


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
    
    # Determine A/PA/NA from CWPM using the competency's criteria (the skill on today's plan; Grade 2 ORF only when none is given)
    skill = entry.get('competency_id') or 'L2.5.1'
    comp = await db.fetchrow("SELECT apna_criteria FROM competencies WHERE id = $1", skill)
    
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
        child['id'], skill, teacher_id, status,
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


class WrongGroupError(ValueError):
    """The photographed sheets belong to another group (their roll numbers say so): nothing is stored."""
    def __init__(self, message: str, suggested_level, rolls: list):
        super().__init__(message)
        self.message, self.suggested_level, self.rolls = message, suggested_level, rolls


GROUP_NAMES_HI = {"beginner": "● शुरुआती", "progressor": "▲ प्रगतिशील", "proficient": "■ दक्ष"}


def wrong_group(read_rolls, worksheet_level: str, groups: list):
    """PURE. The rolls read from the sheets, the group chosen, the class's groups -> (the group they belong to, those rolls) when MOST of the rolls
    read are another group's (15 Nov: Progressor sheets sent as the Beginners'); else None. A sheet or two from another group is only flagged, as before."""
    rolls = [int(r) for r in read_rolls if str(r).strip().lstrip("-").isdigit()]
    member = {int(r): g["label"] for g in groups for r in g.get("roll_numbers") or []}
    known = [r for r in rolls if r in member]
    outside = [r for r in known if member[r] != worksheet_level]
    if not known or len(outside) * 2 <= len(known):
        return None
    counts = {}
    for r in outside:
        counts[member[r]] = counts.get(member[r], 0) + 1
    best = max(counts, key=lambda k: counts[k])
    return best, sorted(r for r in outside if member[r] == best)


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


async def call_vision(photo_bytes_list: list, vision_prompt: str, on_usage=None):
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
    usage = {"input_tokens": getattr(response.usage, "input_tokens", 0), "output_tokens": getattr(response.usage, "output_tokens", 0)}
    if on_usage:
        await on_usage(usage)               # metered the moment the reply arrives: it is paid for even if it cannot be read
    response_text = next((b.text for b in response.content if getattr(b, "type", None) == "text"), None)
    if response_text is None:
        raise ValueError(f"No text block found in Claude Vision's response. Block types received: {[getattr(b, 'type', '?') for b in response.content]}")
    return _extract_json_array(response_text), usage


async def save_analysis(db, teacher_id, session_date, domain_id: str, worksheet_level: str, competency_id: str, payload: dict) -> Optional[int]:
    """Keep the analysis a teacher just saw, so it can be opened again; returns its id (the screen uses it to "use the new photos").
    Never lets a storage problem break the analysis itself."""
    try:
        return await db.fetchval(
            """INSERT INTO review_analyses (teacher_id, session_date, domain_id, worksheet_level, competency_id, result)
               VALUES ($1, $2, $3, $4, $5, $6::jsonb) RETURNING id""",
            teacher_id, session_date, domain_id, worksheet_level, competency_id, json.dumps(payload, ensure_ascii=False, default=str))
    except Exception as e:                       # a database that has not loaded db/schema/06_review_analyses.sql yet
        print(f"   (analysis not saved for later: {type(e).__name__})")
        return None


async def get_latest_analyses(db, teacher_id, session_date, domain_id: str) -> list:
    """Every photo analysis done that day for the subject, newest first, so any of them can be reopened."""
    try:
        rows = await db.fetch(
            """SELECT id, worksheet_level, competency_id, created_at, result
               FROM review_analyses
               WHERE teacher_id = $1 AND session_date = $2 AND domain_id = $3
               ORDER BY created_at DESC LIMIT 12""", teacher_id, session_date, domain_id)
    except Exception as e:
        if e.__class__.__name__ != "UndefinedTableError":
            raise
        return []
    out = []
    for row in rows:
        res = row["result"]
        out.append({"id": row["id"], "worksheet_level": row["worksheet_level"], "competency_id": row["competency_id"],
                    "created_at": row["created_at"].isoformat(), "result": json.loads(res) if isinstance(res, str) else res})
    return out


# How a skill is assessed -> the capture channel the Review screen offers -> the evidence channel stored
CHANNEL_OF = {"written": "photo", "observed": "observed", "oral_reading": "orf"}
EVIDENCE_CHANNEL = {"photo": "written_photo", "observed": "observed", "orf": "oral_reading"}


async def get_review_channels(db, teacher_id, session_date, domain_id: str) -> dict:
    """
    Which way of capturing evidence today's skills need, per group. Each skill has its own assessment mode (a written
    sheet to photograph, something the teacher observes, or oral reading), so the Review screen offers only the channels
    today's groups actually use. Without a stored plan for the day it says so, and the screen offers everything.
    """
    plan = await db.fetchrow("SELECT groups_snapshot, plan_content FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2 AND domain_id = $3",
                             teacher_id, session_date, domain_id)
    if not plan or not plan["groups_snapshot"]:
        return {"has_plan": False, "levels": [], "channels": {}}
    snap = plan["groups_snapshot"]
    snap = json.loads(snap) if isinstance(snap, str) else snap
    # reading aloud needs a text the children have NOT read today (a text practised in class would show a faster pace than the child has):
    # the day's own passages (worksheet and independent practice) are skipped
    content = plan["plan_content"]
    content = json.loads(content) if isinstance(content, str) else (content or {})
    read_today = set((content.get("passages_used") or {}).values()) | {p.get("id") for p in (content.get("independent_passages") or {}).values() if isinstance(p, dict)}
    levels, channels = [], {}
    for level in ("beginner", "progressor", "proficient"):
        g = snap.get(level) or {}
        comp, rolls = g.get("target"), g.get("rolls") or []
        if not comp or not rolls:
            continue
        row = await db.fetchrow("SELECT name_hi, name_en, assessment_modality FROM competencies WHERE id = $1", comp)
        if not row:
            continue
        ch = CHANNEL_OF.get(row["assessment_modality"], "photo")
        entry = {"level": level, "competency_id": comp, "name_hi": row["name_hi"], "name_en": row["name_en"],
                 "modality": row["assessment_modality"], "channel": ch, "rolls": sorted(rolls)}
        if ch == "orf":                   # the text to read aloud: the bank's choice for the skill (or its grade), rotating by day, never one read today
            picked, _match = await _pick_passage(db, comp, session_date, read_today)
            if picked:
                entry["passage"] = {"id": picked["id"], "title": picked["title_hi"], "text": picked["passage_hi"], "word_count": picked["word_count"]}
        levels.append(entry)
        channels.setdefault(ch, []).append(level)
    return {"has_plan": True, "levels": levels, "channels": channels}


async def get_review_coverage(db, teacher_id, session_date, domain_id: str, worksheet_level: str, sample_size=None, absent=None, channel: str = "photo") -> dict:
    """Who in the group has been analysed today and who is still to do, so nobody is photographed twice."""
    plan = await db.fetchrow("SELECT groups_snapshot FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2 AND domain_id = $3",
                             teacher_id, session_date, domain_id)
    competency = None
    if plan and plan["groups_snapshot"]:
        snap = plan["groups_snapshot"]
        snap = json.loads(snap) if isinstance(snap, str) else snap
        competency = (snap.get(worksheet_level) or {}).get("target")
    groups = await get_current_groups(db, teacher_id, domain_id)
    group_rolls = sorted(next((g["roll_numbers"] for g in groups if g["label"] == worksheet_level), []))
    analysed, recorded = [], {}
    if competency:
        rows = await db.fetch(
            """SELECT DISTINCT ON (c.roll_number) c.roll_number, e.status, e.evidence_data
               FROM assessment_evidence e JOIN children c ON c.id = e.child_id
               WHERE e.teacher_id = $1 AND e.competency_id = $2 AND e.session_date = $3 AND e.channel = $4
               ORDER BY c.roll_number, e.created_at DESC""",
            teacher_id, competency, session_date, EVIDENCE_CHANNEL.get(channel, "written_photo"))
        analysed = sorted(x["roll_number"] for x in rows)
        for x in rows:                       # what the screen shows on each child's row: the newest status, and for reading aloud the two numbers entered
            entry = {"status": x["status"]}
            data = x["evidence_data"]
            data = json.loads(data) if isinstance(data, str) else (data or {})
            if channel == "orf" and isinstance(data, dict) and data.get("cwpm") is not None:
                entry.update({"cwpm": data.get("cwpm"), "errors": data.get("error_count", 0)})
            recorded[x["roll_number"]] = entry
    from app.services.sampling import sample_for_group, rotation_sample, margin_points, READ_ALOUD_PER_DAY
    sug = sample_for_group(group_rolls, session_date, worksheet_level, competency or "", sample_size, absent)
    rotation = channel == "orf"
    if rotation:
        # reading aloud: 3-4 children a day in turn, those heard least recently on this skill first (14 Nov), not the photo sample
        last = {}
        if competency and group_rolls:
            for x in await db.fetch(
                    """SELECT c.roll_number, max(e.session_date) AS last FROM assessment_evidence e JOIN children c ON c.id = e.child_id
                       WHERE e.teacher_id = $1 AND e.competency_id = $2 AND e.channel = 'oral_reading' AND e.session_date < $3
                       GROUP BY c.roll_number""", teacher_id, competency, session_date):
                last[x["roll_number"]] = x["last"].toordinal()
        n = min(len(group_rolls), READ_ALOUD_PER_DAY if sample_size is None else max(0, int(sample_size)))
        chosen = rotation_sample(group_rolls, last, n, absent)
        sug = {"mode": "all" if n >= len(group_rolls) else "sample", "size": len(chosen), "group_size": len(group_rolls), "rolls": chosen,
               "margin_points": margin_points(len(chosen), len(group_rolls))}
    labels = {}
    if group_rolls:
        try:
            for ch in await db.fetch("SELECT roll_number, enrolled_grade, school_roll FROM children WHERE teacher_id = $1 AND roll_number = ANY($2::smallint[])", teacher_id, group_rolls):
                if ch["school_roll"] is not None and ch["school_roll"] != ch["roll_number"]:
                    g = "BV" if ch["enrolled_grade"] == "balvatika" else "G" + ch["enrolled_grade"].split("_")[-1]
                    labels[ch["roll_number"]] = f"{g}·{ch['school_roll']}"
        except Exception as e:                       # a database that has not loaded db/schema/07_register.sql yet: no labels, nothing else changes
            if e.__class__.__name__ != "UndefinedColumnError":
                raise
    return {"worksheet_level": worksheet_level, "competency_id": competency, "group_rolls": group_rolls, "labels": labels,
            "analysed_rolls": [x for x in analysed if x in group_rolls], "other_analysed_rolls": [x for x in analysed if x not in group_rolls],
            "pending_rolls": [x for x in group_rolls if x not in analysed],
            "recorded": {str(r): v for r, v in recorded.items() if r in group_rolls},
            # a large group need not be done in full: these children, spread evenly over the roll list, give a rough picture of the group
            "sample": {"mode": sug["mode"], "size": sug["size"], "group_size": sug["group_size"], "rolls": sug["rolls"],
                       "done": [x for x in sug["rolls"] if x in analysed], "left": [x for x in sug["rolls"] if x not in analysed],
                       "margin_points": sug["margin_points"], "absent": sorted({int(a) for a in (absent or [])}),
                       # reading aloud only: today's children in turn; the rest of the group on later days ("आज 4 बच्चे · बाकी अगले दिनों में")
                       **({"rotation": True, "later": max(0, sug["group_size"] - sug["size"])} if rotation else {})}}


PRE_JUDGMENTS = ("advance", "reteach", "not_sure")


def pre_judgment_or_none(value):
    """The teacher's first judgment for a photographed group, or None. Since 14 Nov there is no first-judgment step, and the screen sent '': the database
    accepts only advance / reteach / not_sure or NULL, so the save failed AFTER the AI call had been paid for (found in the photo test, 15 Nov)."""
    return value if value in PRE_JUDGMENTS else None


async def analyse_worksheet_photos(
    db,
    teacher_id: str,
    session_date: date,
    domain_id: str,
    competency_id: str,
    worksheet_level: str,
    photo_bytes_list: list[bytes],
    teacher_pre_judgment: Optional[str] = None,
    on_duplicate: str = "skip",
    replace_rolls: Optional[list] = None,
) -> dict:
    """
    Full Claude Vision analysis pipeline:
    1. Build the Vision prompt with L1 misconception context
    2. Send photos to Claude Vision
    3. Process results into DB updates
    4. Check for discrepancies with teacher's judgment
    """
    teacher_pre_judgment = pre_judgment_or_none(teacher_pre_judgment)
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
    worksheet_data = {}
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
    if worksheet_data.get("practice"):
        # a reading-aloud or observed group's sheet is practice (services/writing_sheets.py): its check is the one-minute reading or watching the children,
        # never a photo. Refused BEFORE any AI call.
        if worksheet_data.get("sheet_kind") == "observed":
            raise LookupError(
                "This group's worksheet is practice: the skill is checked by watching the children do it, not from a photo. "
                "Mark A / PA / NA instead (Observe and record)."
            )
        raise LookupError(
            "This group's worksheet is reading-aloud practice: it is not checked from a photo. "
            "Record the one-minute reading instead (Reading aloud)."
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
        writing=writing_sheets.vision_spec(worksheet_data),       # a writing sheet: marked against its checklist or the dictated sentences
    )
    
    await ai_budget.check(db, teacher_id, "vision")        # over the AI limit: raises AICapReached (the route answers 429); a photo analysis cannot be faked
    async def meter(usage):
        await ai_budget.record(db, teacher_id, "vision", get_settings().claude_vision_model, usage)

    vision_results, _usage = await call_vision(photo_bytes_list, vision_prompt, on_usage=meter)

    # The AI is told never to use names, but a name written on a notebook page can still slip into its free text.
    # Remove any class member's name from what it said before it is stored. (Names are NEVER sent to the AI: the request above is built
    # without them. This only cleans the reply.)
    try:
        from app.services import names_service
        names_service.scrub_names(vision_results, await names_service.names_for_teacher(db, teacher_id))
    except Exception as e:
        print(f"   (name scrub skipped: {type(e).__name__})")
    
    # Sheets of another group (most of the roll numbers say so): nothing is stored, and the teacher is told which group's card to choose
    try:
        from vision_analysis import _dedupe_batch
        entries, _ = _dedupe_batch(vision_results)
    except Exception:
        entries = vision_results.get("children", []) if isinstance(vision_results, dict) else []
    wg = wrong_group([e.get("roll_number") for e in entries if isinstance(e, dict)], worksheet_level, groups)
    if wg:
        level, rolls = wg
        raise WrongGroupError(
            f"ये वर्कशीट {GROUP_NAMES_HI.get(level, level)} समूह के बच्चों की लगती हैं (रोल {', '.join(str(r) for r in rolls)}), आपने {GROUP_NAMES_HI.get(worksheet_level, worksheet_level)} चुना था। "
            f"कुछ भी दर्ज नहीं हुआ। ऊपर {GROUP_NAMES_HI.get(level, level)} का कार्ड चुनकर यही फ़ोटो दोबारा भेजें। "
            f"(These sheets look like the {level} group's; nothing was saved. Choose that group's card and send the photos again.)", level, rolls)

    # Process into DB updates
    summary = await process_vision_results(
        db, teacher_id, session_date, competency_id,
        vision_results, teacher_pre_judgment, required_count=required_count,
        problems=problems, on_duplicate=on_duplicate, replace_rolls=replace_rolls, expected_rolls=group_rolls,
    )
    # what each mistake means (the knowledge base's names, reviewed): the screen shows it beside the code
    summary["misconception_names"] = {m["id"]: {"hi": m.get("name_hi") or "", "en": m.get("name_en") or ""} for m in misconceptions if m.get("id")}
    summary["today_group"] = await today_group_result(db, teacher_id, session_date, competency_id, group_rolls)     # the whole group today, not only this round
    return summary


async def replace_from_saved(db, teacher_id: str, analysis_id: int, rolls: list) -> dict:
    """
    "Use the new photos" for children already marked today (16 Nov): the AI read their new sheets in an earlier round, which kept the readings
    (result.pending) when it skipped them. They replace the earlier results now, with NO new AI call. The earlier round's card stops offering them.
    Returns a result like a photo round's, with the whole group's day (today_group).
    """
    row = await db.fetchrow("""SELECT id, session_date, domain_id, worksheet_level, competency_id, result FROM review_analyses
                               WHERE id = $1 AND teacher_id = $2""", int(analysis_id), teacher_id)
    if not row:
        raise LookupError("That photo analysis was not found. Open today's analysis again.")
    res = row["result"]
    res = json.loads(res) if isinstance(res, str) else dict(res or {})
    pending = res.get("pending") or {}
    wanted = [int(r) for r in rolls or []]
    entries = [pending[str(r)] for r in wanted if str(r) in pending]
    if not entries:
        raise LookupError("The new photos of these children are no longer available. Take their photos again.")
    plan = await db.fetchrow("SELECT plan_content FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2 AND domain_id = $3",
                             teacher_id, row["session_date"], row["domain_id"])
    plan_data = (plan["plan_content"] if isinstance(plan["plan_content"], dict) else json.loads(plan["plan_content"])) if plan and plan["plan_content"] else {}
    ws = (plan_data.get("worksheets") or {}).get(row["worksheet_level"]) or {}
    try:
        required_count = int(ws["required_count"]) if ws.get("required_count") else None
    except (TypeError, ValueError):
        required_count = None
    groups = await get_current_groups(db, teacher_id, row["domain_id"])
    group_rolls = next((g['roll_numbers'] for g in groups if g['label'] == row["worksheet_level"]), [])
    summary = await process_vision_results(db, teacher_id, row["session_date"], row["competency_id"], entries, None, required_count=required_count,
                                           problems=ws.get("problems") or [], on_duplicate="replace", expected_rolls=group_rolls)
    names = await db.fetch("SELECT id, name_hi, name_en FROM misconceptions WHERE competency_id = $1", row["competency_id"])
    summary["misconception_names"] = {m["id"]: {"hi": m["name_hi"] or "", "en": m["name_en"] or ""} for m in names}
    summary["today_group"] = await today_group_result(db, teacher_id, row["session_date"], row["competency_id"], group_rolls)
    # the earlier round no longer offers these children
    done = {str(r) for r in wanted}
    res["pending"] = {k: v for k, v in pending.items() if k not in done}
    res["skipped_duplicates"] = [d for d in res.get("skipped_duplicates") or [] if str(d.get("roll_number")) not in done]
    await db.execute("UPDATE review_analyses SET result = $1::jsonb WHERE id = $2", json.dumps(res, ensure_ascii=False, default=str), row["id"])
    summary["_where"] = {"session_date": row["session_date"], "domain_id": row["domain_id"], "worksheet_level": row["worksheet_level"], "competency_id": row["competency_id"]}
    return summary
