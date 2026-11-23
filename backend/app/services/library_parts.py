"""
The block library, step 2 (21 Nov 2026): independent activities, anchor settings and anchor tasks (docs/drafts/BLOCK_LIBRARY_PLAN.md §2).
Teach and re-teach blocks are in library_pieces.py. Every piece is keyed by ONE skill (or one setting), never by a combination of skills, so the
assembler can serve any teacher's choices. No AI is called here: prompts and checks only.
"""
import json
import re

GROUP = "progressor"
_EXPR = re.compile(r"(\d{1,4})\s*([+\-−×x*])\s*(\d{1,4})")
RETRY = "## AN EARLIER ATTEMPT WAS REJECTED. Fix these:\n"


def _json_field(v):
    if isinstance(v, str):
        try:
            return json.loads(v)
        except ValueError:
            return None
    return v


def skill_header(skill: dict) -> str:
    rng = _json_field(skill.get("number_range"))
    return (f"## THE SKILL\n**Domain:** {skill['domain_id']}\n**Skill:** {skill['id']} — {skill['name_hi']} ({skill['name_en']})\n"
            f"**Grade level:** {skill['grade_level']}\nNumber range: {json.dumps(rng, ensure_ascii=False) if rng else 'N/A'}\n"
            f"Problem types: {', '.join(skill.get('problem_types') or []) or 'General'}\n")


def number_issues(text: str, skill: dict) -> list:
    """Sums in a text that break the skill's own rules: a carry in a 'without regrouping' skill, a borrow in a 'without borrowing' one, a total
    over a two-digit addition skill's 99, a number over the skill's range. The same rules the show-me check applies (app/services/cfu.py)."""
    from app.services.cfu import needs_borrow, needs_carry, skill_rules
    rules = skill_rules(skill.get("name_en"))
    rng = _json_field(skill.get("number_range")) or {}
    try:
        top = int(rng.get("max")) if isinstance(rng, dict) and rng.get("max") is not None else None
    except (TypeError, ValueError):
        top = None
    out = []
    for m in _EXPR.finditer(text or ""):
        a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
        if op == "+" and rules.get("no_carry") and needs_carry(a, b):
            out.append(f"{a} + {b} needs a carry, but the skill is without regrouping")
        if op in "-−" and rules.get("no_borrow") and needs_borrow(a, b):
            out.append(f"{a} - {b} needs a borrow, but the skill is without borrowing")
        if op == "+" and rules.get("max_result") and a + b > rules["max_result"]:
            out.append(f"{a} + {b} = {a + b} is over {rules['max_result']}")
        if top is not None and max(a, b) > top:
            out.append(f"{max(a, b)} is over the skill's range (max {top})")
    return sorted(set(out))


def _style_text(text: str, path: str = "independent") -> tuple:
    """The app's Hindi style on one text, placed where the style code treats it as the teacher's speech. (text, repairs, warnings)."""
    import hindi_style
    if path == "anchor":
        mini = {"anchor": {"narration_hi": text}}
        get = lambda m: m["anchor"]["narration_hi"]
    else:
        mini = {"classroom_management": {"independent_activities_hi": {GROUP: text}}}
        get = lambda m: m["classroom_management"]["independent_activities_hi"][GROUP]
    hindi_style.soften_plan(mini)
    n = hindi_style.neutral_quotes_in_plan(mini)
    warnings = hindi_style.check_teacher_text(mini)
    out = get(mini)
    m = hindi_style._SELF_CORRECTION.search(out)             # 'यानी', 'नहीं, बल्कि', 'के बजाय' (22 Nov): flagged for the reader
    if m:
        warnings.append(f"a possible self-correction ('{m.group(0)}') in the text")
    return out, ([f"{n} gendered 'मैं' quote(s) rewritten to 'हम'"] if n else []), warnings


def _retry(reasons):
    return ("\n" + RETRY + "\n".join(f"- {r}" for r in reasons)) if reasons else ""


# ── independent activities ────────────────────────────────────────────────────

def independent_key(skill_id: str, variant: int) -> str:
    return f"{skill_id}__{variant}"


INDEPENDENT_FORMAT = """
## WHAT TO WRITE: ONE INDEPENDENT-PRACTICE ACTIVITY FOR A LIBRARY
A group that has ALREADY been taught the skill above practises it ON ITS OWN while the teacher teaches another group. Write activity number
{variant} of 2 for this skill{other}. It is reused in many classes: no date, no child, no roll number, nothing about other groups.
- The children work without the teacher: the instructions must be clear enough to start alone, from the board, a sheet or a kit.
- A CORE part of about 7 minutes, then exactly 3 EXTRA parts of about 5 minutes each for groups with more time (the app chooses how many by
  the block's length). Every part practises THIS skill only, at its level, inside its number range and rules (for example, no carry in a
  'without regrouping' skill). Give the actual problems or items, not 'some problems'.
- Materials: only what a government school has or a teacher can make (the board, slates, notebooks, sticks, pebbles, cards); say how many.
- Plain Hindi, polite instructions to the teacher (लिखें, दें); words said to the children in quotes.

Return ONE JSON object, nothing else:
{{"title_hi": "...", "source": "board|sheet|kit", "materials_hi": ["..."], "board_hi": "what the teacher writes on the board before class, or an empty string",
  "core_hi": "the core part, as instructions", "extras_hi": ["extra 1", "extra 2", "extra 3"], "check_hi": "how the group checks its own work"}}
"""


def independent_prompt(skill: dict, variant: int, retry_reasons: list = None) -> str:
    other = (": make it DIFFERENT from activity 1 (another kind of task: if activity 1 used the board, use cards, a kit or a game)" if variant == 2 else "")
    return skill_header(skill) + INDEPENDENT_FORMAT.format(variant=variant, other=other) + _retry(retry_reasons)


def check_independent_piece(piece: dict, skill: dict) -> dict:
    fatal, warnings, repairs = [], [], []
    for k in ("title_hi", "core_hi"):
        if not str(piece.get(k) or "").strip():
            fatal.append(f"{k} is missing")
    extras = piece.get("extras_hi")
    if not isinstance(extras, list) or len([e for e in extras if str(e).strip()]) < 3:
        fatal.append("extras_hi must have 3 parts")
    if fatal:
        return {"ok": False, "fatal": fatal, "warnings": warnings, "repairs": repairs}
    nums = number_issues("\n".join([str(piece.get("core_hi")), str(piece.get("board_hi") or "")] + [str(e) for e in extras]), skill)
    if nums:
        fatal.append("numbers that break the skill's rules: " + "; ".join(nums))
    piece["core_hi"], r, w = _style_text(str(piece["core_hi"]))
    repairs += r
    warnings += w
    for i, e in enumerate(extras):
        extras[i], r, w = _style_text(str(e))
        repairs += r
        warnings += w
    return {"ok": not fatal, "fatal": fatal, "warnings": warnings, "repairs": repairs}


# ── anchor settings ───────────────────────────────────────────────────────────

ANCHOR_THEMES = {
    "numeracy": ["village market", "school garden", "bus journey", "wedding preparations", "village fair", "farm harvest", "kitchen and cooking",
                 "school sports day", "post office", "shop counting stock", "festival sweets", "cricket match", "rain and puddles", "building a hut",
                 "milk collection", "bangle stall", "tailor's shop", "bird watching", "tree planting", "classroom library", "water from the well",
                 "kite making", "train station", "fishing pond", "school canteen"],
    "r1_literacy": ["village market", "school garden", "a letter from grandmother", "the lost kitten", "festival day", "rainy season", "the village well",
                    "a visit to the doctor", "the friendly elephant", "school morning assembly", "the clever crow", "harvest time", "the bus ride",
                    "a new classmate", "the kite contest", "the honey bees", "the old banyan tree", "making rotis", "the river bank", "the fair",
                    "the class picnic", "the moon at night", "the cricket match", "the post office", "the tailor's shop"],
}


def setting_key(domain: str, theme: str) -> str:
    return f"{domain}__{re.sub(r'[^a-z0-9]+', '_', theme.lower()).strip('_')}"


SETTING_FORMAT = """
## WHAT TO WRITE: ONE ANCHOR SETTING FOR A LIBRARY ({domain})
The anchor is the whole-class opening (5-10 minutes) that ALL three groups share before they split. Write the SETTING only: the story world,
what the teacher draws or writes on the board, the narration, an opening and a closing question. Each group's own task inside it is written
separately, for its own skill, so do NOT write tasks for groups here. Theme: "{theme}". Indian village or small-town life, familiar to children
of Classes 1-3; no brand names.
- The board picture must leave room for the numbers or words that tasks will use (for maths: items with prices or counts the teacher can
  change; for Hindi: a short scene with things to read and name).
- Plain spoken Hindi; the narration is said to the children, in 2-3 short sentences; never a gendered 'मैं' verb ('आज हम ...').

Return ONE JSON object, nothing else:
{{"title_hi": "...", "title_en": "...", "theme": "{theme}", "board_hi": "what to draw or write", "narration_hi": "...",
  "opening_question_hi": "...", "closing_question_hi": "...", "materials_hi": ["..."]}}
"""


def setting_prompt(domain: str, theme: str, retry_reasons: list = None) -> str:
    return SETTING_FORMAT.format(domain=domain, theme=theme) + _retry(retry_reasons)


def check_setting_piece(piece: dict) -> dict:
    fatal = [f"{k} is missing" for k in ("title_hi", "board_hi", "narration_hi", "opening_question_hi", "closing_question_hi")
             if not str(piece.get(k) or "").strip()]
    if fatal:
        return {"ok": False, "fatal": fatal, "warnings": [], "repairs": []}
    repairs, warnings = [], []
    for k in ("narration_hi", "opening_question_hi", "closing_question_hi"):
        piece[k], r, w = _style_text(str(piece[k]), "anchor")
        repairs += r
        warnings += w
    return {"ok": True, "fatal": [], "warnings": warnings, "repairs": repairs}


# ── anchor tasks ──────────────────────────────────────────────────────────────

def tasks_key(domain: str, skill_id: str) -> str:
    """One piece holds a skill's tasks in its chosen settings (one call per skill); the assembler reads them per (setting, skill)."""
    return f"{domain}__{skill_id}"


TASKS_FORMAT = """
## WHAT TO WRITE: THIS SKILL'S TASKS IN ANCHOR SETTINGS, FOR A LIBRARY
Below are the anchor settings of this subject (the whole-class opening that three groups share). Choose the {n} settings where THIS skill fits
most naturally, and for each write the task a group working on this skill does inside it during the anchor (2-3 minutes, the whole group
together, answered aloud or on slates). The task uses the setting's board picture and practises ONLY this skill, inside its number range and
rules. Give the actual numbers or words. Plain Hindi; polite instructions to the teacher; words to the children in quotes; never a gendered 'मैं' verb.

SETTINGS (key: title - board):
{settings}

Return ONE JSON object, nothing else:
{{"tasks": [{{"setting": "<a key from the list>", "task_hi": "...", "answer_hi": "the right answer(s), short"}}, ... exactly {n} ...]}}
"""


def tasks_prompt(skill: dict, settings: dict, n: int = 3, retry_reasons: list = None) -> str:
    listing = "\n".join(f"- {k}: {v.get('title_hi')} - {str(v.get('board_hi') or '')[:160]}" for k, v in settings.items())
    return skill_header(skill) + TASKS_FORMAT.format(n=n, settings=listing) + _retry(retry_reasons)


def check_tasks_piece(piece: dict, skill: dict, settings: dict, n: int = 3) -> dict:
    """piece = {"tasks": [...]}: each task in a known setting, with text and an answer, inside the skill's rules; at least n kept (one per setting)."""
    warnings, repairs, kept = [], [], []
    tasks = piece.get("tasks") if isinstance(piece.get("tasks"), list) else []
    for t in tasks:
        if not isinstance(t, dict) or t.get("setting") not in settings or not str(t.get("task_hi") or "").strip() or not str(t.get("answer_hi") or "").strip():
            warnings.append(f"a task dropped: unknown setting or missing text ({str(t)[:80]})")
            continue
        nums = number_issues(t["task_hi"] + " " + str(t["answer_hi"]), skill)
        if nums:
            warnings.append(f"the task in {t['setting']} dropped: " + "; ".join(nums))
            continue
        if t["setting"] in [k["setting"] for k in kept]:
            continue
        t["task_hi"], r, w = _style_text(t["task_hi"], "anchor")
        repairs += r
        warnings += w
        kept.append(t)
    piece["tasks"] = kept
    fatal = [] if len(kept) >= n else [f"only {len(kept)} usable task(s), {n} are needed"]
    return {"ok": not fatal, "fatal": fatal, "warnings": warnings, "repairs": repairs}


# ── anchor-task top-up: tasks in SETTINGS GIVEN by the code (21 Nov) ─────────
# Each skill first chose its own 3 settings, so for about half of the usual skill trios no setting had a task for all three groups. The code finds,
# for each trio, the setting that best fits the Progressors' skill and asks the other skills for a task in exactly that setting.

def tasks_extra_key(domain: str, skill_id: str) -> str:
    return f"{domain}__{skill_id}__extra"


EXTRA_FORMAT = """
## WHAT TO WRITE: THIS SKILL'S TASK IN EACH OF THESE ANCHOR SETTINGS, FOR A LIBRARY
The anchor is the whole-class opening that three groups share. Write the task a group working on THIS skill does inside EACH setting below,
during the anchor (2-3 minutes, the whole group together, answered aloud or on slates). The task uses the setting's board picture and practises
ONLY this skill, inside its number range and rules. Give the actual numbers or words. Plain Hindi; polite instructions to the teacher; words to the
children in quotes; never a gendered 'मैं' verb.

SETTINGS (key: title - board):
{settings}

Return ONE JSON object, nothing else:
{{"tasks": [{{"setting": "<the key>", "task_hi": "...", "answer_hi": "the right answer(s), short"}}, ... one for EACH setting above ...]}}
"""


def tasks_extra_prompt(skill: dict, settings: dict, retry_reasons: list = None) -> str:
    listing = "\n".join(f"- {k}: {v.get('title_hi')} - {str(v.get('board_hi') or '')[:160]}" for k, v in settings.items())
    return skill_header(skill) + EXTRA_FORMAT.format(settings=listing) + _retry(retry_reasons)


def trio_needs(trios: list, tasks_by_skill: dict) -> dict:
    """{skill: set of settings it needs a task in} so that each trio (beginner, progressor, proficient skill ids) has ONE setting with a task for all
    three. tasks_by_skill: {skill: set of settings it already has}. The setting chosen is the Progressors' setting already shared with most of the trio."""
    needs = {}
    for b, p, f in trios:
        have = {s: tasks_by_skill.get(s, set()) | needs.get(s, set()) for s in (b, p, f)}
        if have[b] & have[p] & have[f]:
            continue
        cands = sorted(have[p], key=lambda k: (-(k in have[b]) - (k in have[f]), k))
        if not cands:
            continue
        pick = cands[0]
        for s in (b, f):
            if pick not in have[s]:
                needs.setdefault(s, set()).add(pick)
    return needs
