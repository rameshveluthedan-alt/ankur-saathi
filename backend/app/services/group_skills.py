"""
Each group's skill for the day.

The app used to derive all three groups' skills from the ONE skill the teacher selects: the Beginners get its first hard prerequisite, the Progressors the skill itself, the Proficients the first skill that depends on it.
Real groups move on their own paths (Teaching at the Right Level: groups by learning level, each with its own goal, regrouped as children progress), and a group that repeats a skill while another moves on cannot be
expressed by one selected skill. So a teacher can now set the Beginners' and the Proficients' skill (the Progressors' skill is the day's skill), and the app PROPOSES each group's skill from what the teacher decided
at the last review.

A group's POSITION is read from the last plan it was part of: the skill it was taught (groups_snapshot) and the teacher's Advance / Re-teach / Not-sure decision recorded at the Review screen
(explainability.teacher_decision_<group>). Nothing new is stored. 'Moved on' is the teacher's judgement, and is NOT recorded as 'achieved': each child's own A/PA/NA results stay what they are.
"""
import json
import math
import os
from datetime import timedelta
from typing import Optional

LABELS = ("beginner", "progressor", "proficient")
DECISIONS = ("advance", "reteach", "not_sure")
HISTORY_DAYS = 14                      # how far back the last plan may be and still count as 'yesterday'
MIN_ASSESSED_FOR_RECOMMENDATION = 4    # under 4 children assessed the numbers are shown but nothing is recommended
GRADE_RANK = {"balvatika": 0, "grade_1": 1, "grade_2": 2, "grade_3": 3}


def fits_day(label: str, skill_grade: Optional[str], day_grade: Optional[str]) -> bool:
    """The Beginners are never AHEAD of the day's skill and the Proficients never BEHIND it, in grade (found on the click-through: with N0.1.1, Balvatika sorting, chosen for the day, the Beginners were given N2.3.2 because yesterday's
    review had said Advance). The comparison is by GRADE: a skill's sort_order is only its place inside its strand, so it cannot be compared across strands. The same grade, or a grade that is not known, fits."""
    a, b = GRADE_RANK.get(skill_grade), GRADE_RANK.get(day_grade)
    if a is None or b is None:
        return True
    return a <= b if label == "beginner" else a >= b if label == "proficient" else True


class GroupSkillError(ValueError):
    """A skill the teacher chose for a group cannot be used. The message is written for the teacher."""


def _obj(v):
    return json.loads(v) if isinstance(v, str) else (v or {})


async def _brief(db, competency_id: str) -> Optional[dict]:
    r = await db.fetchrow("SELECT id, name_en, name_hi, grade_level FROM competencies WHERE id = $1", competency_id)
    return dict(r) if r else None


async def next_options(db, competency_id: str, limit: int = 6) -> list:
    """The skills that depend on this one (it is their hard prerequisite), in curriculum order: the first is what the plan already uses as the Proficients' extension.
    The graph is a guide only (after 3-digit addition it points to perimeter), so the teacher can always choose another."""
    rows = await db.fetch("""
        SELECT c.id, c.name_en, c.name_hi, c.grade_level
        FROM competency_prerequisites cp JOIN competencies c ON c.id = cp.competency_id
        WHERE cp.prerequisite_id = $1 AND cp.prerequisite_type = 'hard'
        ORDER BY c.sort_order LIMIT $2
    """, competency_id, limit)
    return (await _curated_first(db, "proficient", competency_id, [dict(r) for r in rows]))[:limit]


def reteached_groups(plan_content) -> set:
    """The groups that RE-TAUGHT in a stored plan: the teacher's choice recorded in the plan (`reteach_groups`), a teach block marked `reteach` (the re-teach as the group's main block), or, in a plan made the old way, the separate
    re-teach block that names its group. (Found on the click-through: the plan of yesterday had a Progressor re-teach, and the screen showed no trace of it.)"""
    plan = _obj(plan_content)
    out = {g for g in (plan.get("reteach_groups") or []) if g in LABELS}
    for b in ((plan.get("rotation_schedule") or {}).get("blocks") or []):
        if isinstance(b, dict) and b.get("teach_group") in LABELS and ((b.get("type") == "teach" and b.get("reteach") is True) or b.get("type") == "reteach"):
            out.add(b["teach_group"])
    return out


async def previous_positions(db, teacher_id: str, domain_id: str, plan_date) -> Optional[dict]:
    """Where each group was at the last plan before plan_date (within HISTORY_DAYS): the skill it was taught and the teacher's decision about it, if any."""
    row = await db.fetchrow("""
        SELECT plan_date, selected_competency_id, groups_snapshot, explainability, plan_content
        FROM daily_plans
        WHERE teacher_id = $1 AND domain_id = $2 AND plan_date < $3 AND plan_date >= $4
        ORDER BY plan_date DESC LIMIT 1
    """, teacher_id, domain_id, plan_date, plan_date - timedelta(days=HISTORY_DAYS))
    if not row:
        return None
    snap, expl = _obj(row["groups_snapshot"]), _obj(row["explainability"])
    retaught = reteached_groups(row["plan_content"])
    groups = {}
    for label in LABELS:
        target = (snap.get(label) or {}).get("target")
        if target:
            d = expl.get(f"teacher_decision_{label}")
            groups[label] = {"target": target, "decision": d if d in DECISIONS else None, "rolls": list((snap.get(label) or {}).get("rolls") or []), "reteached": label in retaught}
    return {"plan_date": row["plan_date"], "selected_competency_id": row["selected_competency_id"], "groups": groups}


def recommend(assessed: int, with_mistakes: int) -> dict:
    """The app's recommendation for ONE group (decided 21 Oct): recommend a re-teach when at least a THIRD of the children ASSESSED, rounded up, made a mistake (6 assessed: 2; 7: 3; 4: 2), so up to two thirds can still
    move on. Under MIN_ASSESSED_FOR_RECOMMENDATION children assessed the numbers are shown but nothing is recommended (a very small group), and with nobody assessed there is nothing to say. The teacher decides."""
    needed = math.ceil(assessed / 3) if assessed else 0
    very_small = 0 < assessed < MIN_ASSESSED_FOR_RECOMMENDATION
    return {"assessed": assessed, "with_mistakes": with_mistakes, "needed": needed, "very_small": very_small,
            "recommend": bool(assessed) and not very_small and with_mistakes >= needed}


async def review_evidence(db, teacher_id: str, review_date, groups: dict) -> dict:
    """What the last review found, for each group: of the children who were in the group (the roll numbers saved with the plan) and were ASSESSED on the skill the group was taught on review_date, how many made a recognised mistake,
    which children (roll numbers: the teacher's own screen, never the AI) and which mistakes. A child counts once however many sheets were read. groups: {label: {'target': id, 'rolls': [...]}}."""
    out = {}
    for label, g in groups.items():
        rolls = {str(r) for r in (g.get("rolls") or [])}
        rows = await db.fetch("""
            SELECT e.child_id, c.roll_number, e.detected_misconception_ids
            FROM assessment_evidence e JOIN children c ON c.id = e.child_id
            WHERE e.teacher_id = $1 AND e.competency_id = $2 AND e.session_date = $3
        """, teacher_id, g["target"], review_date)
        children = {}
        for r in rows:
            if str(r["roll_number"]) not in rolls:
                continue
            c = children.setdefault(r["child_id"], {"roll": r["roll_number"], "ids": set()})
            c["ids"].update(r["detected_misconception_ids"] or [])
        wrong = [c for c in children.values() if c["ids"]]
        counts = {}
        for c in wrong:
            for i in c["ids"]:
                counts[i] = counts.get(i, 0) + 1
        names = {r["id"]: r["name_hi"] for r in await db.fetch("SELECT id, name_hi FROM misconceptions WHERE id = ANY($1::text[])", list(counts))} if counts else {}
        out[label] = {**recommend(len(children), len(wrong)), "rolls": sorted(c["roll"] for c in wrong),
                      "mistakes": sorted(({"misconception_id": i, "name_hi": names.get(i), "children": n} for i, n in counts.items()), key=lambda m: (-m["children"], m["misconception_id"]))}
    return out


async def propose(db, teacher_id: str, domain_id: str, plan_date) -> dict:
    """What each group's skill could be on plan_date, from the teacher's decisions at the last review:
    advance -> the next skill on from the one it was taught; re-teach or not sure -> the same skill again; no decision -> nothing proposed (the plan derives the skill as before), EXCEPT when the evidence recommends a re-teach
    (reason 'recommended': at least a third of those assessed made a mistake). Each group also carries what the last review found (`evidence`), the app's `recommendation` ('reteach', 'very_small' or None), and `conflict` (the teacher chose
    Advance although the evidence recommends a re-teach). Each group also gets the alternatives the graph offers, because the teacher decides."""
    prev = await previous_positions(db, teacher_id, domain_id, plan_date)
    if not prev:
        return {"has_history": False, "previous_date": None, "groups": {}}
    out = {}
    evidence = await review_evidence(db, teacher_id, prev["plan_date"], prev["groups"])
    for label, g in prev["groups"].items():
        target, decision = g["target"], g["decision"]
        ev = evidence[label]
        recommendation = "reteach" if ev["recommend"] else ("very_small" if ev["very_small"] else None)
        entry = {"previous_target": await _brief(db, target), "previous_decision": decision, "proposed": None, "reason": "no_decision", "alternatives": [],
                 "evidence": ev, "recommendation": recommendation, "conflict": False, "previous_reteach": bool(g.get("reteached"))}
        if decision == "advance":
            opts = await next_options(db, target)
            entry["alternatives"] = opts
            if opts:
                entry["proposed"], entry["reason"] = opts[0], "advance"
            else:                                      # nothing depends on it: the group stays on it
                entry["proposed"], entry["reason"] = entry["previous_target"], "advance_no_next"
        elif decision in ("reteach", "not_sure"):
            entry["proposed"], entry["reason"] = entry["previous_target"], decision
        elif ev["recommend"]:                         # no decision was recorded: the evidence suggests staying (the teacher can change it)
            entry["proposed"], entry["reason"] = entry["previous_target"], "recommended"
        entry["conflict"] = decision == "advance" and ev["recommend"]      # the teacher chose to move on although the evidence suggests a re-teach: the screen asks, once
        out[label] = entry
    return {"has_history": True, "previous_date": str(prev["plan_date"]), "groups": out}


async def related_skills(db, competency_id: str, direction: str, limit: int = 40) -> list:
    """The skills reached through HARD prerequisite links, nearest first. 'below': the skill's prerequisites, and theirs (the foundations a group can work on). 'above': the skills that depend on it, and those that depend on
    those (where a group can go next). For N2.3.2: 8 foundations, 4 skills that build on it."""
    if direction == "below":
        first = "SELECT prerequisite_id AS id, 1 AS depth FROM competency_prerequisites WHERE competency_id = $1 AND prerequisite_type = 'hard'"
        step = "SELECT cp.prerequisite_id, r.depth + 1 FROM competency_prerequisites cp JOIN r ON cp.competency_id = r.id WHERE cp.prerequisite_type = 'hard' AND r.depth < 8"
    else:
        first = "SELECT competency_id AS id, 1 AS depth FROM competency_prerequisites WHERE prerequisite_id = $1 AND prerequisite_type = 'hard'"
        step = "SELECT cp.competency_id, r.depth + 1 FROM competency_prerequisites cp JOIN r ON cp.prerequisite_id = r.id WHERE cp.prerequisite_type = 'hard' AND r.depth < 8"
    rows = await db.fetch(f"""
        WITH RECURSIVE r(id, depth) AS ({first} UNION {step})
        SELECT c.id, c.name_en, c.name_hi, c.grade_level FROM r JOIN competencies c ON c.id = r.id
        WHERE c.id <> $1 GROUP BY c.id, c.name_en, c.name_hi, c.grade_level, c.sort_order
        ORDER BY MIN(r.depth), c.sort_order LIMIT $2
    """, competency_id, limit)
    return [dict(r) for r in rows]


async def allowed_skills(db, teacher_id: str, domain_id: str, plan_date, competency_id: str) -> dict:
    """What a teacher may choose for the Beginners and for the Proficients when the day's skill is competency_id. The Beginners work on today's skill or a FOUNDATION of it; the Proficients on today's skill or one that BUILDS on it;
    and a group may stay where it was yesterday, or take the suggestion from the review, UNLESS that is on the wrong side of the day's skill in grade (fits_day): the Beginners are never ahead of it and the Proficients never behind it.
    (A Grade 3 skill for the Beginners, or a Balvatika skill for the Proficients, is not a choice: both were tried on the first screen.)"""
    below = {x["id"] for x in await related_skills(db, competency_id, "below", 200)}
    above = {x["id"] for x in await related_skills(db, competency_id, "above", 200)}
    for label, bucket in (("beginner", below), ("proficient", above)):          # the reviewer's pick is always a choice, even where the graph does not connect it
        pick = await curated_pick(db, label, competency_id)
        if pick:
            bucket.add(pick)
    day = await _brief(db, competency_id)
    prop = (await propose(db, teacher_id, domain_id, plan_date))["groups"]
    out = {}
    for label, related in (("beginner", below), ("proficient", above)):
        allowed = {competency_id} | related
        g = prop.get(label)
        if g:
            for k in ("previous_target", "proposed"):
                if g.get(k) and fits_day(label, g[k].get("grade_level"), (day or {}).get("grade_level")):
                    allowed.add(g[k]["id"])
        out[label] = allowed
    return out


async def check_reteach_same_skill(db, teacher_id: str, domain_id: str, plan_date, reteach_groups, skills_today: dict) -> None:
    """A re-teach is the SAME skill as yesterday. Where there is a yesterday, a group chosen for re-teach must be on the skill it was taught then. (No yesterday: nothing to compare, and nothing is refused.)"""
    if not reteach_groups:
        return
    prev = await previous_positions(db, teacher_id, domain_id, plan_date)
    for g in reteach_groups:
        was = ((prev or {}).get("groups") or {}).get(g)
        if was and skills_today.get(g) != was["target"]:
            raise GroupSkillError(f"एक दोहराव वही कौशल है जो कल था। {g} कल {was['target']} पर था, आज {skills_today.get(g)} पर है। (A re-teach is the same skill as yesterday: the {g.title()} group was on {was['target']}, and today is on {skills_today.get(g)}.)")


async def clean_group_skills(db, domain_id: str, competency_id: str, group_skills: Optional[dict], allowed: Optional[dict] = None) -> dict:
    """The skills a teacher chose for the Beginners and the Proficients, checked: {'beginner': id, 'proficient': id} (only those given). The Progressors' skill is the day's skill (competency_id):
    giving a different one for them is refused, so the two cannot disagree."""
    out = {}
    for label, cid in (group_skills or {}).items():
        if label == "progressor":
            if cid and cid != competency_id:
                raise GroupSkillError("The Progressors' skill is the day's skill: choose it as the skill for the day.")
            continue
        if label not in ("beginner", "proficient"):
            raise GroupSkillError(f"Unknown group {label!r}.")
        if not cid:
            continue
        ok = await db.fetchval("SELECT 1 FROM competencies c JOIN subdomains s ON s.id = c.subdomain_id WHERE c.id = $1 AND s.domain_id = $2", cid, domain_id)
        if not ok:
            raise GroupSkillError(f"Skill {cid!r} is not a skill of this subject.")
        if allowed is not None and cid not in allowed.get(label, ()):
            raise GroupSkillError(f"{cid} इस समूह के लिए आज उचित कौशल नहीं है: आज का कौशल, उसका आधार कौशल (शुरुआती) या उस पर बने आगे के कौशल (दक्ष), या समूह का कल का कौशल चुनें; शुरुआती समूह आज के कौशल से आगे और दक्ष समूह उससे पीछे नहीं हो सकता। "
                                  f"({cid} is not a sensible skill for the {label.title()} group today: choose today's skill, a foundation of it (Beginners) or a skill that builds on it (Proficients), or the group's skill from yesterday; the Beginners cannot be ahead of today's skill, nor the Proficients behind it.)")
        out[label] = cid
    return out


def clean_reteach_groups(reteach_groups) -> Optional[list]:
    """The groups the teacher chose to re-teach, checked. None means the teacher was not asked (an older app): the plan keeps the old way. An empty list means 'move on with every group'."""
    if reteach_groups is None:
        return None
    if not isinstance(reteach_groups, (list, tuple)):
        raise GroupSkillError("reteach_groups must be a list of groups.")
    out = []
    for g in reteach_groups:
        if g not in LABELS:
            raise GroupSkillError(f"Unknown group {g!r}.")
        if g not in out:
            out.append(g)
    return out


async def curated_bridge(db, skill_id: str) -> Optional[dict]:
    """The reviewer-APPROVED bridge for this skill, if there is one: {'predecessor_id', 'successor_id'} (either may be None: that side follows the rule). The table may not exist yet
    (a deploy before the loader has run): then there is none and nothing breaks. (to_regclass does not raise, so it cannot poison a transaction the way a failed query would.)
    THE SWITCH: SKILL_BRIDGES=off (also 0, false, no) ignores the table altogether, like CFU_ENABLED: if a wrong row were ever approved, the bridges can be turned off in one command, without a deploy."""
    if os.environ.get("SKILL_BRIDGES", "on").strip().lower() in ("off", "0", "false", "no"):
        return None
    if not await db.fetchval("SELECT to_regclass('skill_bridges') IS NOT NULL"):
        return None
    row = await db.fetchrow("SELECT predecessor_id, successor_id FROM skill_bridges WHERE skill_id = $1 AND approved", skill_id)
    return dict(row) if row else None


async def curated_pick(db, label: str, skill_id: str) -> Optional[str]:
    """The reviewer's skill for this group when the day's skill is skill_id (the Beginners' predecessor, the Proficients' successor), or None. The skill itself means 'stay on it'.
    Ignored when it would break the grade rule (the Beginners AHEAD of the day's skill, the Proficients BEHIND it): the loader refuses such a row, and this is the belt to its braces."""
    cb = await curated_bridge(db, skill_id)
    pick = (cb or {}).get("predecessor_id" if label == "beginner" else "successor_id")
    if not pick:
        return None
    if pick == skill_id:
        return skill_id
    grades = {r["id"]: r["grade_level"] for r in await db.fetch("SELECT id, grade_level FROM competencies WHERE id = ANY($1::text[])", [skill_id, pick])}
    return pick if pick in grades and fits_day(label, grades[pick], grades.get(skill_id)) else None


async def _curated_first(db, label: str, skill_id: str, listing: list) -> list:
    """A list of candidate skills with the reviewer's pick moved to the front (added if the graph does not offer it). The day's skill itself is never listed here."""
    pick = await curated_pick(db, label, skill_id)
    if not pick or pick == skill_id:
        return listing
    brief = await _brief(db, pick)
    return ([brief] if brief else []) + [x for x in listing if x["id"] != pick]


async def derived_beginner_id(db, competency_id: str) -> str:
    """The Beginners' skill when the teacher selects competency_id and chooses nothing else: its first hard prerequisite (by id), or the skill itself if it has none.
    The plan and the screen's panel BOTH use this, so they cannot disagree. A reviewer-approved bridge (skill_bridges) comes FIRST."""
    pick = await curated_pick(db, "beginner", competency_id)
    if pick:
        return pick
    row = await db.fetchrow("""
        SELECT prerequisite_id FROM competency_prerequisites
        WHERE competency_id = $1 AND prerequisite_type = 'hard'
        ORDER BY prerequisite_id LIMIT 1
    """, competency_id)
    return row["prerequisite_id"] if row else competency_id


async def derived_proficient_id(db, competency_id: str) -> str:
    """The Proficients' skill: the first skill (in curriculum order) that depends on this one, or the skill itself if nothing does. A reviewer-approved bridge (skill_bridges) comes FIRST."""
    pick = await curated_pick(db, "proficient", competency_id)
    if pick:
        return pick
    row = await db.fetchrow("""
        SELECT cp.competency_id AS id FROM competency_prerequisites cp
        JOIN competencies c ON c.id = cp.competency_id
        WHERE cp.prerequisite_id = $1 AND cp.prerequisite_type = 'hard'
        ORDER BY c.sort_order LIMIT 1
    """, competency_id)
    return row["id"] if row else competency_id


async def ladder(db, competency_id: str) -> Optional[dict]:
    """The three groups' skills the plan DERIVES when the teacher selects competency_id (None if there is no such skill). The Progressors always get the skill itself."""
    sel = await _brief(db, competency_id)
    if not sel:
        return None
    b, x = await derived_beginner_id(db, competency_id), await derived_proficient_id(db, competency_id)
    return {"beginner": sel if b == competency_id else await _brief(db, b), "progressor": sel, "proficient": sel if x == competency_id else await _brief(db, x),
            "options": {"beginner": await _curated_first(db, "beginner", competency_id, await related_skills(db, competency_id, "below", 40)),
                        "proficient": await _curated_first(db, "proficient", competency_id, await related_skills(db, competency_id, "above", 40))}}
