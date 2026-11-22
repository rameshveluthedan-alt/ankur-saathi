"""
The recorded-block library: what a piece is, the prompt that asks for ONE piece, and the checks every piece must pass
(docs/drafts/BLOCK_LIBRARY_PLAN.md). Used by scripts/generate_library.py now, and later by the assembler that builds a plan from pieces.

Step 1 (21 Nov 2026): TEACH blocks (skill · normal · length). Re-teach blocks, independent activities and anchors follow the same pattern.

A teach piece is one group's teach block and its worksheet, written for ONE skill at the Progressor level of scaffolding, for a nominal length.
It is checked by wrapping it in a one-group plan and running the app's OWN checks on it (the same code that checks a live plan), so a piece in the
library has passed exactly what a live plan passes. No AI is called here.
"""
import copy
import hashlib
import json
import re
from dataclasses import asdict

from app.services import writing_sheets
from app.services.cfu import clean_plan_cfu
from app.services.hindi_numbers import repair_place_value

LENGTHS = {"short": 7, "medium": 14, "long": 22}          # nominal minutes; the assembler scales the pace to the actual slot
GROUP = "progressor"                                      # a piece is written at the Progressor level of scaffolding (plan §7, 1a)
FORMAT_VERSION = 1


def teach_key(skill_id: str, length: str) -> str:
    return f"{skill_id}__normal__{length}"


def reteach_key(mistake_id: str, length: str) -> str:
    """A re-teach block for ONE recorded mistake (its skill is in the mistake's ID: N2.3.2-M1)."""
    return f"{mistake_id}__{length}"


RETEACH_SECTION = """
## THIS BLOCK IS A RE-TEACH of ONE recorded mistake: {mid} {name}
Children in this group made this mistake at the last check. Write the block by the RE-TEACH RULES in the system instructions (the mistake first,
then the right way; find and fix; erase the wrong working; visit the children who made it quietly, never naming them). Aim the show-me questions
and core problems 2 and 3 of the worksheet at THIS mistake first (set diagnostic_for_misconception to {mid} on them).
"""


def piece_path(root, kind: str, key: str):
    return root / kind / f"{key}.json"


# ── the prompt ───────────────────────────────────────────────────────────────

TEACH_FORMAT = """
## WHAT TO WRITE: ONE TEACH BLOCK FOR A LIBRARY (not a whole plan)
Write ONE group's teach block and its worksheet, for the skill above, for a block of {minutes} minutes (pace: {pace}). It will be reused in many
classes, so: no date, no class, no child, no roll number, no anchor story, nothing about what other groups do. Follow every rule in the system
instructions that applies to one teach block and one worksheet (Hindi style, the show-me questions, the {sheet_rule}).

Return ONE JSON object, nothing else:
{{
  "talking_points": {{"i_do_hi": "...", "we_do_hi": "..."{we_do_note}, "you_do_hi": "..."}},
  "cfu": [3 show-me questions, in the format the system instructions give],
  "prep_hi": ["what the teacher prepares for THIS block (materials, what to write on the board); [] if nothing"],
  "worksheet": <WORKSHEET, in the format the system instructions give for this subject>
}}
"""


def teach_prompt(skill: dict, mistakes: list, length: str, pace_text: str, kind_rules: str, retry_reasons: list = None, reteach: dict = None) -> str:
    """The per-piece user message. skill: {id, name_en, name_hi, grade_level, assessment_modality, apna_criteria, number_range, problem_types,
    domain_id}. mistakes: the skill's recorded mistakes (dicts), most important first. kind_rules: writing_sheets.prompt_section for this skill
    (empty for a maths or reading sheet)."""
    minutes = LENGTHS[length]
    short = minutes < 10
    kind = writing_sheets.sheet_kind(skill["id"], skill["domain_id"])

    def _j(v):                                           # the database keeps some of these as JSON text
        if isinstance(v, str):
            try:
                return json.loads(v)
            except ValueError:
                return v
        return v

    sheet_rule = ("3 + N sheet: 3 core problems and 3 extras (6 problems), required_count 3" if kind in (None, "reading")
                  else f"{kind.upper()} sheet as its section below says")
    lines = [
        f"## THE SKILL\n**Domain:** {skill['domain_id']}\n**Skill:** {skill['id']} — {skill['name_hi']} ({skill['name_en']})\n"
        f"**Grade level:** {skill['grade_level']}\n**Assessment modality:** {skill['assessment_modality']}\n"
        f"A/PA/NA criteria: {json.dumps(_j(skill.get('apna_criteria')), ensure_ascii=False)}\n"
        f"Number range: {json.dumps(_j(skill.get('number_range')), ensure_ascii=False) if skill.get('number_range') else 'N/A'}\n"
        f"Problem types: {', '.join(skill.get('problem_types') or []) or 'General'}",
        "\n## THIS SKILL'S RECORDED MISTAKES (most important first; use only these IDs, in the show-me questions and on core problems 2 and 3)",
    ]
    if mistakes:
        for n, m in enumerate(mistakes[:4], 1):
            lines.append(f"  {n}. {m['id']} {m.get('name_hi') or ''}\n     pattern: {m.get('error_pattern')}\n     how to detect: {m.get('diagnostic_indicator')}\n"
                         f"     right: {m.get('example_correct') or '-'} | wrong: {m.get('example_incorrect') or '-'}")
    else:
        lines.append("  No mistakes are recorded for this skill: STILL write the 3 show-me questions, testing the skill's key idea; leave listen_for as [] and fill shows_hi.")
    if kind_rules:
        lines.append("\n" + kind_rules)
    if reteach:
        lines.append(RETEACH_SECTION.format(mid=reteach["id"], name=reteach.get("name_hi") or ""))
    lines.append(TEACH_FORMAT.format(minutes=minutes, pace=pace_text, sheet_rule=sheet_rule,
                                     we_do_note=(' (a block under 10 minutes has NO We Do: leave "we_do_hi" as "")' if short else "")))
    if retry_reasons:
        lines.append("## AN EARLIER ATTEMPT WAS REJECTED. Fix these:\n" + "\n".join(f"- {r}" for r in retry_reasons))
    return "\n".join(lines)


def prompt_version(system_text: str, user_template: str = TEACH_FORMAT) -> str:
    return hashlib.sha256((system_text + "\n" + user_template).encode("utf-8")).hexdigest()[:12]


# ── the checks ───────────────────────────────────────────────────────────────

_PLAIN = re.compile(r"^\s*(\d{1,4})\s*([+\-−×x*])\s*(\d{1,4})\s*(?:=\s*_*\s*)?$")


def compute_answer_keys(ws: dict) -> list:
    """For every plain 'a + b', 'a - b' or 'a × b' problem, the answer is computed by CODE and written over the model's (roadmap: code-computed
    answer keys). Word problems and anything else are left alone. Returns one line per answer changed."""
    log = []
    for p in (ws or {}).get("problems") or []:
        if not isinstance(p, dict):
            continue
        m = _PLAIN.match(str(p.get("problem_hi") or ""))
        if not m:
            continue
        a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
        val = a + b if op == "+" else (a - b if op in "-−" else a * b)
        if val < 0:
            continue
        if str(p.get("answer", "")).strip() != str(val):
            log.append(f"problem {p.get('number')}: answer {p.get('answer')!r} -> {val} (computed)")
            p["answer"] = str(val)
    return log


def check_teach_piece(piece: dict, skill: dict, mistakes: list, length: str, plan_service, reteach: dict = None) -> dict:
    """Run the app's own checks on a teach piece (changed in place where the checks repair). Returns {ok, fatal: [...], warnings: [...],
    repairs: [...]}. fatal = the piece cannot be used (it is generated again once, with these reasons). plan_service is passed in (it imports
    this module's caller chain; passing it avoids an import cycle)."""
    import hindi_style
    fatal, warnings, repairs = [], [], []
    minutes = LENGTHS[length]
    tp = piece.get("talking_points") if isinstance(piece.get("talking_points"), dict) else {}
    ws = piece.get("worksheet") if isinstance(piece.get("worksheet"), dict) else None
    for k in (("i_do_hi", "you_do_hi") if minutes < 10 else ("i_do_hi", "we_do_hi", "you_do_hi")):
        if not str(tp.get(k) or "").strip():
            fatal.append(f"talking_points.{k} is missing")
    if not ws or not (ws.get("problems") or ws.get("observe")):
        fatal.append("the worksheet is missing or has no problems")
    if fatal:
        return {"ok": False, "fatal": fatal, "warnings": warnings, "repairs": repairs}

    domain = skill["domain_id"]
    block = {"type": "teach", "teach_group": GROUP, "duration_minutes": minutes, "talking_points": tp, "cfu": piece.get("cfu") or []}
    mini = {"rotation_schedule": {"blocks": [block]}, "worksheets": {GROUP: ws}, "prep_hi": piece.get("prep_hi") or [],
            "review_prompts": {}, "explainability": {"items": []}}
    gsk = {GROUP: skill["id"]}
    kb = {GROUP: {"competency_id": skill["id"], "name_hi": skill["name_hi"], "name_en": skill["name_en"],
                  "criteria_type": None, "mistakes": [m if isinstance(m, dict) else asdict(m) for m in mistakes]}}
    repairs += [f"sheet: {l}" for l in writing_sheets.apply_writing_sheets(mini, gsk, domain)]
    hindi_style.soften_plan(mini)
    nq = hindi_style.neutral_quotes_in_plan(mini)
    if nq:
        repairs.append(f"{nq} gendered 'मैं' quote(s) rewritten to 'हम'")
    if domain == "numeracy":
        repairs += [f"worksheet: {l}" for l in plan_service.repair_worksheet_numbers(mini)]
        repairs += [f"place value: {l}" for l in repair_place_value(mini)]
        repairs += [f"answer key: {l}" for l in compute_answer_keys(mini["worksheets"][GROUP])]
    repairs += [f"example: {l}" for l in plan_service.drop_answer_examples(mini)]
    repairs += [f"diagnostic: {l}" for l in plan_service.clean_worksheet_diagnostics(mini, kb)]
    lines, stats = clean_plan_cfu(mini, kb, {GROUP: 2})
    st = stats.get(GROUP) or {}
    if st.get("kept", 0) < 2:
        fatal.append(f"only {st.get('kept', 0)} show-me question(s) passed the checks (2 are needed): " + "; ".join(l for l in lines if " dropped" in l)[:600])
    hindi_style.soften_plan(mini)
    hindi_style.neutral_quotes_in_plan(mini)
    warnings += hindi_style.check_teacher_text(mini)
    warnings += hindi_style.check_size_shape(mini, [skill["id"]])
    kinds = writing_sheets.group_kinds(gsk, domain)
    shape = [w for w in plan_service.validate_plan_shape(mini, domain, extras=3, sheet_kinds=kinds)
             if GROUP in w and "teach blocks should cover" not in w and not w.startswith("anchor.")]    # a piece has no anchor
    warnings += shape
    warnings += writing_sheets.check_writing_sheets(mini, gsk, domain)
    text = json.dumps(mini, ensure_ascii=False)
    if "यानी" in text:
        warnings.append("a possible self-correction ('यानी') in the text")
    # write the checked parts back into the piece
    piece["talking_points"] = block["talking_points"]
    piece["cfu"] = block.get("cfu") or []
    piece["worksheet"] = mini["worksheets"][GROUP]
    piece["prep_hi"] = mini.get("prep_hi") or []
    if any(w for w in warnings if "required_count" in w or "problems missing" in w):
        fatal.append("the worksheet's shape is wrong: " + "; ".join(w for w in warnings if "required_count" in w or "problems missing" in w))
    if reteach and not fatal:
        core = [p.get("diagnostic_for_misconception") for p in (piece["worksheet"].get("problems") or [])[:3] if isinstance(p, dict)]
        if reteach["id"] not in core:
            warnings.append(f"re-teach: no core problem reveals {reteach['id']}")
        if not any((x.get("misconception_id") == reteach["id"]) for q in piece["cfu"] for x in (q.get("listen_for") or [])):
            warnings.append(f"re-teach: no show-me question listens for {reteach['id']}")
    return {"ok": not fatal, "fatal": fatal, "warnings": warnings, "repairs": repairs}


def record(key: str, kind: str, skill_id: str, length: str, content: dict, checks: dict, model: str, pversion: str, cost: float, created: str, mode: str = "normal") -> dict:
    """The file written for one piece (docs/drafts/BLOCK_LIBRARY_PLAN.md §4)."""
    return {"format": FORMAT_VERSION, "piece": kind, "key": key, "skill_id": skill_id, "mode": mode, "length": length,
            "minutes": LENGTHS[length], "content": copy.deepcopy(content), "checks": checks, "model": model, "prompt_version": pversion,
            "created": created, "cost_usd": round(cost, 4), "review_status": "ai_drafted", "reviewed_by": None, "review_notes": None}
