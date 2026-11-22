"""
A plan built by CODE from the recorded-block library (db/seeds/library; docs/drafts/BLOCK_LIBRARY_PLAN.md), with no AI call: for ANY teacher's
choices (any skill for any group, re-teach or move on, 45 / 60 / 90 minutes), because every piece is keyed by ONE group's own skill.

  * the layout is the app's own (prompts/session_shape.py via orchestrate.group_layout): the same minutes, order and pace as an AI plan;
  * each group's teach block and worksheet: its skill's piece at the nearest of the three lengths (a RE-TEACH piece for the group's commonest
    mistake when the teacher chose to re-teach it);
  * "what the other groups do meanwhile": each other group's own independent activity, with as many extras as the block has time for;
  * the anchor: the setting where the most of today's three skills have a task (rotated by the date), each group's task from its own skill.

The result has the same shape as an AI plan, so plan_service runs the same checks and repairs on it and the screens show it unchanged, with a
label that it is built from AI-drafted pieces not yet reviewed. Returns None when a piece is missing (the caller then falls back).
"""
import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3] / "db" / "seeds" / "library"
GROUPS = ("beginner", "progressor", "proficient")
GROUP_HI = {"beginner": "शुरुआती", "progressor": "प्रगतिशील", "proficient": "दक्ष"}
_INDEX = {}


def _load(root: Path = ROOT) -> dict:
    """The pieces that passed their checks, read once: {"teach": {(skill, length): content}, "reteach": {(mistake, length): content},
    "independent": {skill: [content, ...]}, "setting": {key: content}, "tasks": {skill: [task, ...]}}."""
    key = str(root)
    if key in _INDEX:
        return _INDEX[key]
    idx = {"teach": {}, "reteach": {}, "independent": {}, "setting": {}, "tasks": {}, "tasks_extra": {}}
    man_f = root / "MANIFEST.json"
    ok = {k for k, p in json.loads(man_f.read_text(encoding="utf-8"))["pieces"].items() if p.get("status") == "ok"} if man_f.is_file() else set()
    for kind in idx:
        d = root / kind
        for f in sorted(d.glob("*.json")) if d.is_dir() else []:
            rec = json.loads(f.read_text(encoding="utf-8"))
            if rec.get("key") not in ok:
                continue
            c = rec["content"]
            if kind == "teach":
                idx["teach"][(rec["skill_id"], rec["length"])] = c
            elif kind == "reteach":
                idx["reteach"][(rec["mode"], rec["length"])] = c
            elif kind == "independent":
                idx["independent"].setdefault(rec["skill_id"], []).append(c)
            elif kind == "setting":
                idx["setting"][rec["key"]] = c
            elif kind in ("tasks", "tasks_extra"):                          # the top-up's tasks join the skill's own
                idx["tasks"].setdefault(rec["skill_id"], []).extend(c.get("tasks") or [])
    _INDEX[key] = idx
    return idx


def version(root: Path = ROOT) -> str:
    """A short fingerprint of the library (its MANIFEST): the phone prepares its offline plans again when it changes."""
    import hashlib
    man = root / "MANIFEST.json"
    return hashlib.sha256(man.read_bytes()).hexdigest()[:12] if man.is_file() else "none"


def available(root: Path = ROOT) -> bool:
    return bool(_load(root)["teach"])


def nominal_length(minutes: int) -> str:
    """The library's three lengths (7 / 14 / 22) cover every slot: under 10 short, under 18 medium, else long."""
    return "short" if minutes < 10 else ("medium" if minutes < 18 else "long")


def _clock(m: int) -> str:
    return f"{m // 60}:{m % 60:02d}"


def _reteach_mistake(ctx, g: str, skill: str):
    """The mistake to re-teach for group g: the one most children of g made at the last check, in g's own skill."""
    best = None
    for it in ctx.reteach_competencies or []:
        n = (it.get("affected_by_group") or {}).get(g, 0)
        if it.get("competency_id") == skill and n > 0 and (best is None or n > best[1]):
            best = (it.get("misconception_id"), n)
    return best[0] if best else None


def _independent_text(piece: dict, extras: int) -> str:
    parts = [str(piece.get("core_hi") or "").strip()] + [str(e).strip() for e in (piece.get("extras_hi") or [])[:extras]]
    return " ".join(p for p in parts if p)


def _pick_setting(idx: dict, domain: str, skills: dict, day_ordinal: int, avoid: str = None):
    """(setting key, {group: task}): the setting with tasks for the most of today's skills; ties rotate by the day, and yesterday's is avoided."""
    tasks_by = {g: {t["setting"]: t for t in idx["tasks"].get(s, [])} for g, s in skills.items()}
    cands = [k for k in sorted(idx["setting"]) if k.startswith(domain + "__")]
    if not cands:
        return None, {}
    scored = sorted(((sum(1 for g in skills if k in tasks_by[g]), k) for k in cands), key=lambda x: -x[0])
    top = [k for n, k in scored if n == scored[0][0]]
    if avoid in top and len(top) > 1:
        top.remove(avoid)
    key = top[day_ordinal % len(top)]
    return key, {g: tasks_by[g][key] for g in skills if key in tasks_by[g]}


def assemble(ctx, plan_date=None, avoid_setting: str = None, root: Path = ROOT):
    """A plan (dict, in the AI plan's shape) for this context, or None when the library lacks a piece it needs."""
    from orchestrate import group_layout
    from session_shape import worksheet_extras
    idx = _load(root)
    if not idx["teach"]:
        return None
    shape, rotation, lay = group_layout(ctx)
    skills = {g: (ctx.group_skill_ids or {}).get(g) for g in GROUPS}
    if not all(skills.values()):
        return None
    used = []
    teach, reteach_of = {}, {}
    for g in GROUPS:
        length = nominal_length(lay[g]["minutes"])
        piece, key = None, None
        if g in (ctx.reteach_groups or []):
            mid = _reteach_mistake(ctx, g, skills[g])
            if mid and (mid, length) in idx["reteach"]:
                piece, key = idx["reteach"][(mid, length)], f"{mid}__{length}"
                reteach_of[g] = mid
        if piece is None:
            piece, key = idx["teach"].get((skills[g], length)), f"{skills[g]}__normal__{length}"
        if piece is None:
            return None
        teach[g] = copy.deepcopy(piece)
        used.append(key)
    indep = {g: (idx["independent"].get(skills[g]) or [None])[(plan_date.toordinal() if plan_date else 0) % max(1, len(idx["independent"].get(skills[g]) or [1]))]
             for g in GROUPS}
    if not all(indep.values()):
        return None

    # the anchor
    day = plan_date.toordinal() if plan_date else 0
    setting_key, tasks = _pick_setting(idx, ctx.domain_id, skills, day, avoid_setting)
    setting = idx["setting"].get(setting_key) or {}
    anchor = {"title_hi": setting.get("title_hi") or "", "narration_hi": setting.get("narration_hi") or "",
              "opening_question_hi": setting.get("opening_question_hi") or "", "closing_question_hi": setting.get("closing_question_hi") or ""}
    for g in GROUPS:
        t = tasks.get(g)
        anchor[f"{g}_participation_hi"] = (t["task_hi"] if t else
                                           f"इस समूह के बच्चे बोर्ड की चीज़ों से अपना अभ्यास करें: {str(indep[g].get('title_hi') or '').strip()}।")
    if setting.get("board_hi"):
        anchor["narration_hi"] = f"बोर्ड पर बनाएँ: {setting['board_hi']} {anchor['narration_hi']}".strip()

    # the session, block by block
    blocks, t = [{"type": "anchor", "time_start": _clock(0), "duration_minutes": shape["anchor"]}], shape["anchor"]
    if shape["setup"]:
        blocks.append({"type": "setup", "time_start": _clock(t), "duration_minutes": shape["setup"],
                       "script_hi": "सब बच्चे अपने-अपने समूह में बैठें। जिस समूह के साथ शिक्षक नहीं हैं, वह बोर्ड पर लिखा अपना काम शुरू करे।"})
        t += shape["setup"]
    trans = list(shape["transition_list"])
    for i, g in enumerate(rotation):
        mins = lay[g]["minutes"]
        others = [o for o in rotation if o != g]
        extras = max(0, min(3, (mins - 7) // 5))
        other_txt = " · ".join(f"{GROUP_HI[o]} समूह: {_independent_text(indep[o], extras)}" for o in others)
        tp = teach[g].get("talking_points") or {}
        blocks.append({"type": "teach", "teach_group": g, "time_start": _clock(t), "duration_minutes": mins, "other_groups_hi": other_txt,
                       "talking_points": {"i_do_hi": tp.get("i_do_hi") or "", "we_do_hi": tp.get("we_do_hi") or "", "you_do_hi": tp.get("you_do_hi") or ""},
                       "cfu": teach[g].get("cfu") or []})
        t += mins
        if i < len(rotation) - 1 and trans:
            m = trans.pop(0)
            blocks.append({"type": "transition", "time_start": _clock(t), "duration_minutes": m,
                           "script_hi": "अपना काम रोकें। अगला समूह शिक्षक के पास आएँ; बाकी समूह अपनी जगह पर अपना काम जारी रखें।"})
            t += m

    # the worksheets: a 3 + N sheet keeps the core and the extras this session has time for; other sheets as made
    extras_n = worksheet_extras(ctx.available_minutes)
    worksheets = {}
    for g in GROUPS:
        ws = copy.deepcopy(teach[g].get("worksheet") or {})
        if not ws.get("sheet_kind") and (ctx.sheet_kinds or {}).get(g) in (None, "reading") and isinstance(ws.get("problems"), list):
            ws["problems"] = ws["problems"][:3 + extras_n]
            ws["required_count"] = min(3, len(ws["problems"]))
        worksheets[g] = ws

    prep = []
    for src in [teach[g].get("prep_hi") or [] for g in GROUPS] + [setting.get("materials_hi") or []] + [indep[g].get("materials_hi") or [] for g in GROUPS]:
        for line in src:
            if str(line).strip() and line not in prep:
                prep.append(line)

    plan = {
        "prep_hi": prep,
        "anchor": anchor,
        "rotation_schedule": {"total_minutes": t, "blocks": blocks},
        "worksheets": worksheets,
        "classroom_management": {"independent_activities_hi": {g: _independent_text(indep[g], 3) for g in GROUPS}},
        "review_prompts": {"photo_sample_rolls": {g: [] for g in GROUPS}},
        "explainability": {"items": [
            {"id": "library", "title_hi": "यह योजना कैसे बनी", "title_en": "How this plan was made",
             "body_hi": "यह योजना तैयार हिस्सों के पुस्तकालय से कोड ने बनाई है (AI से नहीं): हर समूह का पाठ उसी के कौशल के लिए लिखा गया है। "
                        "ये हिस्से AI ने तैयार किए हैं और अभी शिक्षा विशेषज्ञ की समीक्षा बाकी है।",
             "body_en": "This plan was put together by code from a library of ready-made pieces (no AI call today): each group's lesson was written for its own "
                        "skill. The pieces were drafted by AI and are not yet reviewed by the education lead."},
            {"id": "groups", "title_hi": "ये तीन समूह क्यों", "title_en": "Why these three groups",
             "body_hi": "हर बच्चा अपने पिछले नतीजों के हिसाब से समूह में है; हर समूह अपने कौशल पर काम करता है।",
             "body_en": "Each child is in a group by their last results; each group works on its own skill."}]},
        "library": {"setting": setting_key, "pieces": used + [f"{skills[g]}__independent" for g in GROUPS], "reteach": reteach_of,
                    "review_status": "ai_drafted"},
    }
    return plan
