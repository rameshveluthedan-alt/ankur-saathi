"""
Ankur Saathi — Progress Service
Dashboard data, B/P/P summary, level change recommendations, MLO export.
"""

import json
import csv
import io
from datetime import date

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'prompts'))
from vision_analysis import check_reassessment_flags


async def get_bpp_summary(db, teacher_id: str) -> list[dict]:
    """Get B/P/P distribution per domain for the Progress screen header."""
    rows = await db.fetch("""
        SELECT clp.domain_id, clp.bpp_level, COUNT(*) as count
        FROM child_lakshya_positions clp
        JOIN children c ON clp.child_id = c.id
        WHERE c.teacher_id = $1 AND c.is_active = TRUE
        GROUP BY clp.domain_id, clp.bpp_level
        ORDER BY clp.domain_id, clp.bpp_level
    """, teacher_id)
    
    # Pivot into per-domain summaries
    domains = {}
    for r in rows:
        d = r['domain_id']
        if d not in domains:
            domains[d] = {"domain_id": d, "beginner_count": 0, "progressor_count": 0, "proficient_count": 0}
        domains[d][f"{r['bpp_level']}_count"] = r['count']
    
    return list(domains.values())


async def get_children_progress(db, teacher_id: str) -> list[dict]:
    """Get per-child progress for the full Progress screen table."""
    rows = await db.fetch("""
        SELECT 
            c.roll_number, c.enrolled_grade,
            num.bpp_level as num_bpp, num.current_competency_id as num_comp,
            num_c.name_hi as num_comp_hi,
            COALESCE(GREATEST(num.last_assessed, num.level_changed_at), num.created_at)::date as num_as_of, num.source as num_source,
            lit.bpp_level as lit_bpp, lit.current_competency_id as lit_comp,
            lit_c.name_hi as lit_comp_hi,
            COALESCE(GREATEST(lit.last_assessed, lit.level_changed_at), lit.created_at)::date as lit_as_of, lit.source as lit_source
        FROM children c
        LEFT JOIN child_lakshya_positions num 
            ON num.child_id = c.id AND num.domain_id = 'numeracy'
        LEFT JOIN competencies num_c ON num_c.id = num.current_competency_id
        LEFT JOIN child_lakshya_positions lit 
            ON lit.child_id = c.id AND lit.domain_id = 'r1_literacy'
        LEFT JOIN competencies lit_c ON lit_c.id = lit.current_competency_id
        WHERE c.teacher_id = $1 AND c.is_active = TRUE
        ORDER BY c.roll_number
    """, teacher_id)
    
    return [
        {
            "roll_number": r['roll_number'],
            "enrolled_grade": r['enrolled_grade'],
            "numeracy_bpp": r['num_bpp'],
            "numeracy_competency_id": r['num_comp'],
            "numeracy_competency_name_hi": r['num_comp_hi'],
            "literacy_bpp": r['lit_bpp'],
            "literacy_competency_id": r['lit_comp'],
            "literacy_competency_name_hi": r['lit_comp_hi'],
            # when the level was last set (registration, baseline or a periodic round), so the teacher can see how old it is
            "numeracy_level_as_of": r['num_as_of'].isoformat() if r['num_as_of'] else None,
            "numeracy_level_source": r['num_source'],
            "literacy_level_as_of": r['lit_as_of'].isoformat() if r['lit_as_of'] else None,
            "literacy_level_source": r['lit_source'],
        }
        for r in rows
    ]


SUBJECTS = ("numeracy", "r1_literacy")
STATUS_KEY = {"achieved": "a", "partially_achieved": "pa", "not_achieved": "na"}


def _obj(v):
    return json.loads(v) if isinstance(v, str) else (v or {})


async def get_today(db, teacher_id: str, on: date) -> dict:
    """What the teacher recorded ON THIS DAY (`on`, the phone's own date), per subject, for the Progress screen:

    subjects[domain] = {"has_plan": bool, "by_level": {label: {skill_id, a, pa, na, assessed, group_size, decision, conflict, advance_no_next}}}
        from that day's plan (each group's skill and children) and that day's results only. A child counts ONCE: the newest result of the day
        on the group's skill, whichever way it was recorded (photo, observation, reading aloud). `decision` is the one recorded at that day's
        review; `conflict` and `advance_no_next` follow the same rules as the Plan screen's group panel (services/group_skills.py).
    children[roll][domain] = {"skill_id", "status"} | None, plus {"cwpm", "errors"} when the result came from reading aloud
        the child's result that day on the skill of today's plan for the child's group; if none on that skill, the newest result of the day in
        that subject. A child's LEVEL never changes on this: it is only what was recorded.
    """
    from app.services import group_skills as gs
    rows = await db.fetch("""
        SELECT c.roll_number, e.competency_id, e.status, e.channel, e.evidence_data, s.domain_id
        FROM assessment_evidence e
        JOIN children c ON c.id = e.child_id
        JOIN competencies k ON k.id = e.competency_id
        JOIN subdomains s ON s.id = k.subdomain_id
        WHERE e.teacher_id = $1 AND e.session_date = $2 AND c.is_active = TRUE
        ORDER BY e.created_at DESC
    """, teacher_id, on)
    def result(r):                                # one child's result; a reading-aloud score also carries the two numbers the teacher entered
        out = {"skill_id": r["competency_id"], "status": r["status"]}
        if r["channel"] == "oral_reading":
            d = _obj(r["evidence_data"])
            out.update(cwpm=d.get("cwpm"), errors=d.get("error_count"))
        return out
    newest = {}                                   # (roll, domain, skill) -> result: the first row seen is the newest
    newest_any = {}                               # (roll, domain) -> result: the newest of the day in that subject
    for r in rows:
        newest.setdefault((str(r["roll_number"]), r["domain_id"], r["competency_id"]), result(r))
        newest_any.setdefault((str(r["roll_number"]), r["domain_id"]), result(r))

    sizes = {}                                    # the current groups, for a day with no plan
    for r in await db.fetch("""SELECT clp.domain_id, clp.bpp_level, COUNT(*) AS n FROM child_lakshya_positions clp JOIN children c ON c.id = clp.child_id
                               WHERE c.teacher_id = $1 AND c.is_active = TRUE GROUP BY 1, 2""", teacher_id):
        sizes[(r["domain_id"], r["bpp_level"])] = r["n"]

    subjects, children = {}, {}
    for domain in SUBJECTS:
        plan = await db.fetchrow("SELECT groups_snapshot, explainability FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2 AND domain_id = $3",
                                 teacher_id, on, domain)
        snap, expl = (_obj(plan["groups_snapshot"]), _obj(plan["explainability"])) if plan else ({}, {})
        groups = {l: {"target": (snap.get(l) or {}).get("target"), "rolls": [str(x) for x in ((snap.get(l) or {}).get("rolls") or [])]} for l in gs.LABELS}
        evidence = await gs.review_evidence(db, teacher_id, on, {l: g for l, g in groups.items() if g["target"]}) if plan else {}
        by_level = {}
        for label in gs.LABELS:
            g = groups[label]
            counts = {"a": 0, "pa": 0, "na": 0}
            for roll in g["rolls"]:
                res = newest.get((roll, domain, g["target"]))
                if res:
                    counts[STATUS_KEY[res["status"]]] += 1
            d = expl.get(f"teacher_decision_{label}")
            decision = d if d in gs.DECISIONS else None
            ev = evidence.get(label) or {}
            by_level[label] = {
                "skill_id": g["target"], **counts, "assessed": sum(counts.values()),
                "group_size": len(g["rolls"]) or ((snap.get(label) or {}).get("count") if plan else sizes.get((domain, label), 0)) or 0,
                "decision": decision,
                "recommend": bool(ev.get("recommend")),                                     # the evidence suggests a re-teach (a third or more made a mistake)
                "very_small": bool(ev.get("very_small")),                                   # too few children checked for the app to suggest anything
                "conflict": decision == "advance" and bool(ev.get("recommend")),          # chose to move on although the evidence recommends a re-teach
                "advance_no_next": decision == "advance" and bool(g["target"]) and not await gs.next_options(db, g["target"]),
            }
        subjects[domain] = {"has_plan": bool(plan), "by_level": by_level}
        for label, g in groups.items():
            for roll in g["rolls"]:
                res = newest.get((roll, domain, g["target"]))
                if res:
                    children.setdefault(roll, {})[domain] = res
        for (roll, dom), v in newest_any.items():
            if dom == domain and domain not in children.get(roll, {}):
                children.setdefault(roll, {})[domain] = v
    return {"date": on.isoformat(), "subjects": subjects, "children": children}


async def get_reassessment_flags(db, teacher_id: str) -> dict:
    """Children whose daily work no longer matches their level, per subject. A flag changes nothing: levels change only through an assessment."""
    return {
        "numeracy": await check_reassessment_flags(db, teacher_id, 'numeracy'),
        "r1_literacy": await check_reassessment_flags(db, teacher_id, 'r1_literacy'),
    }


async def export_mlo_report_csv(db, teacher_id: str) -> str:
    """Generate CSV export for MLO (Block/District officer) reporting."""
    children = await get_children_progress(db, teacher_id)
    
    teacher = await db.fetchrow("""
        SELECT s.school_code, s.block_name, s.district_name
        FROM teachers t JOIN schools s ON t.school_id = s.id
        WHERE t.id = $1
    """, teacher_id)
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        'School Code', 'Block', 'District',
        'Roll No', 'Enrolled Grade',
        'Numeracy Level', 'Numeracy Competency',
        'Literacy Level', 'Literacy Competency',
    ])
    
    for c in children:
        writer.writerow([
            teacher['school_code'] if teacher else '',
            teacher['block_name'] if teacher else '',
            teacher['district_name'] if teacher else '',
            c['roll_number'], c['enrolled_grade'],
            c['numeracy_bpp'] or '', c['numeracy_competency_id'] or '',
            c['literacy_bpp'] or '', c['literacy_competency_id'] or '',
        ])
    
    return output.getvalue()


async def export_class_report_csv(db, teacher_id: str) -> str:
    """The teacher's OWN class report, with names. It is separate from the officer (MLO) report, which has roll numbers only."""
    from app.services import names_service
    children = await get_children_progress(db, teacher_id)
    names = await names_service.names_for_teacher(db, teacher_id)
    school_rolls = {}
    try:
        school_rolls = {r["roll_number"]: r["school_roll"] for r in await db.fetch("SELECT roll_number, school_roll FROM children WHERE teacher_id = $1", teacher_id)}
    except Exception as e:
        if e.__class__.__name__ != "UndefinedColumnError":
            raise
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(['Class No', 'Grade', 'School Roll', 'Name', 'Numeracy Level', 'Numeracy Skill', 'Literacy Level', 'Literacy Skill'])
    for c in children:
        w.writerow([c['roll_number'], c['enrolled_grade'], school_rolls.get(c['roll_number']) or '', names.get(c['roll_number'], ''),
                    c['numeracy_bpp'] or '', (c['numeracy_competency_id'] or '') + ' ' + (c['numeracy_competency_name_hi'] or ''),
                    c['literacy_bpp'] or '', (c['literacy_competency_id'] or '') + ' ' + (c['literacy_competency_name_hi'] or '')])
    return out.getvalue()


# ── The mentor summary: one page for a block or cluster officer's visit (counts and roll numbers only, never a name) ──
# The rules that turn the numbers into talking points. STARTING VALUES, for Vaishnavi to review: what counts as "stuck", "not checked", and when
# the first judgment is worth talking about are teaching decisions, not code. They are printed on the page, so an officer can see where each point comes from.
MENTOR_RULES = {
    "window_days": 28,            # the period: the last 4 weeks
    "stuck_days": 3,              # a group taught the same skill on 3 or more days: a place where the teacher may need help
    "not_checked_days": 14,       # a child with no result for 2 weeks
    "not_checked_share": 0.25,    # ...worth a talking point when a quarter of the class or more
    "evidence_share": 0.5,        # fewer than half of the groups taught were checked with evidence: worth a talking point
    "match_share": 0.5,           # the first judgment matched the evidence less than half the time...
    "match_min": 3,               # ...out of at least 3 groups where the evidence could suggest something
}


def _first_of(expl: dict, label: str):
    v = expl.get(f"teacher_first_{label}") or expl.get(f"teacher_decision_{label}")          # older records have only teacher_decision_
    return v if v in ("advance", "reteach", "not_sure") else None


async def get_mentor_summary(db, teacher_id: str, end: date) -> dict:
    """What an officer needs for a mentoring visit, over the last MENTOR_RULES['window_days'] days up to `end` (the phone's date):
    how the teacher works (plans made, reviews completed, groups checked with evidence, the first judgment against the evidence), how the children moved
    (the groups at the start and the end of the period, skills achieved, groups taught the same skill again and again, children not checked), the most
    common mistakes with a matching activity, and talking points from fixed rules (one strength first, then up to two things to work on, then a question).
    Counts and roll numbers only: no names are read here."""
    from datetime import timedelta
    from app.services import group_skills as gs
    R = MENTOR_RULES
    start = end - timedelta(days=R["window_days"] - 1)
    school = await db.fetchrow("""SELECT s.school_code, s.block_name, s.district_name FROM teachers t JOIN schools s ON s.id = t.school_id WHERE t.id = $1""", teacher_id)
    plans = await db.fetch("""SELECT plan_date, domain_id, groups_snapshot, explainability FROM daily_plans
                              WHERE teacher_id = $1 AND plan_date BETWEEN $2 AND $3 ORDER BY plan_date""", teacher_id, start, end)
    plan_days = sorted({r["plan_date"] for r in plans})
    review_days, taught, checked, compared, matched = set(), 0, 0, 0, 0
    runs = {}                                     # (domain, label, skill) -> days taught
    groups_at = {}                                # domain -> {"start": {label: n}, "end": {label: n}}
    for r in plans:
        snap, expl = _obj(r["groups_snapshot"]), _obj(r["explainability"])
        groups = {l: {"target": (snap.get(l) or {}).get("target"), "rolls": (snap.get(l) or {}).get("rolls") or []} for l in gs.LABELS}
        live = {l: g for l, g in groups.items() if g["target"] and g["rolls"]}
        sizes = {l: len(g["rolls"]) for l, g in groups.items() if g["rolls"]}
        if sizes:
            at = groups_at.setdefault(r["domain_id"], {"start": sizes, "start_date": r["plan_date"].isoformat()})
            at["end"], at["end_date"] = sizes, r["plan_date"].isoformat()
        if live and all(expl.get(f"teacher_final_{l}") in gs.DECISIONS for l in live):
            review_days.add(r["plan_date"])
        evidence = await gs.review_evidence(db, teacher_id, r["plan_date"], live) if live else {}
        for l, g in live.items():
            taught += 1
            runs[(r["domain_id"], l, g["target"])] = runs.get((r["domain_id"], l, g["target"]), 0) + 1
            n = await db.fetchval("""SELECT COUNT(DISTINCT e.child_id) FROM assessment_evidence e JOIN children c ON c.id = e.child_id
                                     WHERE e.teacher_id = $1 AND e.competency_id = $2 AND e.session_date = $3 AND c.roll_number = ANY($4::smallint[])""",
                                  teacher_id, g["target"], r["plan_date"], [int(x) for x in g["rolls"]])
            if n:
                checked += 1
            ev, first = evidence.get(l) or {}, _first_of(expl, l)
            if first and n and not ev.get("very_small"):          # very_small: fewer than MIN_ASSESSED_FOR_RECOMMENDATION children, nothing to compare with
                compared += 1
                matched += 1 if (first == "advance") != bool(ev.get("recommend")) else 0       # advance and no re-teach suggested, or re-teach/not sure and suggested

    names = {r["id"]: r["name_hi"] for r in await db.fetch("SELECT id, name_hi FROM competencies WHERE id = ANY($1::text[])", list({k[2] for k in runs}))} if runs else {}
    stuck = sorted(({"domain_id": d, "level": l, "skill_id": k, "skill_name_hi": names.get(k), "days": n} for (d, l, k), n in runs.items() if n >= R["stuck_days"]),
                   key=lambda x: (-x["days"], x["skill_id"]))

    achieved = await db.fetchval("""SELECT COUNT(*) FROM (SELECT DISTINCT e.child_id, e.competency_id FROM assessment_evidence e JOIN children c ON c.id = e.child_id
                                    WHERE e.teacher_id = $1 AND e.status = 'achieved' AND e.session_date BETWEEN $2 AND $3 AND c.is_active) x""", teacher_id, start, end)
    class_size = await db.fetchval("SELECT COUNT(*) FROM children WHERE teacher_id = $1 AND is_active", teacher_id)
    not_checked = await _not_checked(db, teacher_id, end, R["not_checked_days"])

    mistakes = await _common_mistakes(db, teacher_id, start, end)

    practice = {"plan_days": len(plan_days), "review_days": len(review_days), "groups_taught": taught, "groups_checked": checked,
                "judgments_compared": compared, "judgments_matched": matched}
    progress = {"class_size": class_size, "groups": groups_at, "skills_achieved": achieved, "stuck": stuck, "not_checked": not_checked}
    return {"period": {"start": start.isoformat(), "end": end.isoformat(), "days": R["window_days"]},
            "school": {"school_code": school["school_code"], "block": school["block_name"], "district": school["district_name"]} if school else None,
            "practice": practice, "progress": progress, "mistakes": mistakes, "rules": dict(R),
            "points": mentor_points(practice, progress, mistakes)}


async def _not_checked(db, teacher_id: str, end: date, days: int) -> list:
    """The roll numbers of the active children with no result at all in the last `days` days up to `end`."""
    from datetime import timedelta
    return [r["roll_number"] for r in await db.fetch("""SELECT c.roll_number FROM children c WHERE c.teacher_id = $1 AND c.is_active AND NOT EXISTS (
                SELECT 1 FROM assessment_evidence e WHERE e.child_id = c.id AND e.session_date BETWEEN $2 AND $3) ORDER BY c.roll_number""", teacher_id, end - timedelta(days=days - 1), end)]


async def _common_mistakes(db, teacher_id: str, start: date, end: date, limit: int = 3) -> list:
    """The most common mistakes between start and end: the children with each (a child once per mistake; their roll numbers), the mistake's name, and a
    matching activity from the content bank (the mistake's own templates first)."""
    rows = await db.fetch("""SELECT m_id, COUNT(DISTINCT e.child_id) AS n, ARRAY_AGG(DISTINCT c.roll_number ORDER BY c.roll_number) AS rolls
                             FROM assessment_evidence e JOIN children c ON c.id = e.child_id, UNNEST(e.detected_misconception_ids) AS m_id
                             WHERE e.teacher_id = $1 AND e.session_date BETWEEN $2 AND $3 AND c.is_active GROUP BY m_id ORDER BY n DESC, m_id LIMIT $4""", teacher_id, start, end, limit)
    out = []
    for r in rows:
        m = await db.fetchrow("SELECT id, competency_id, name_hi, intervention_template_ids FROM misconceptions WHERE id = $1", r["m_id"])
        if not m:
            continue
        act = await db.fetchrow("""SELECT id, title_hi FROM intervention_templates WHERE is_active IS NOT FALSE AND (id = ANY($1::text[]) OR $2 = ANY(misconception_ids))
                                   ORDER BY (id = ANY($1::text[])) DESC, id LIMIT 1""", list(m["intervention_template_ids"] or []), m["id"])
        out.append({"misconception_id": m["id"], "skill_id": m["competency_id"], "name_hi": m["name_hi"], "children": r["n"], "rolls": list(r["rolls"]),
                    "activity": {"id": act["id"], "title_hi": act["title_hi"]} if act else None})
    return out


# ── The class summary: the teacher's own page for planning next week (roll numbers here; the teacher's phone adds the names it holds) ──
# STARTING VALUES, for Vaishnavi to review (teaching decisions, printed on the page): a child to look at is one stuck on the group's skill after 3+ days of
# teaching, one not checked for 2 weeks, or one marked "not achieved" on 2 or more days in the period.
CLASS_RULES = {"window_days": 28, "stuck_days": 3, "not_checked_days": 14, "na_days": 2}


async def get_class_summary(db, teacher_id: str, end: date) -> dict:
    """The teacher's class over the last CLASS_RULES['window_days'] days up to `end` (the phone's date), per subject: the groups now and the skills achieved;
    what each group was taught, on how many days, and the final decisions; the children to look at (stuck on the group's skill, not checked, "not achieved"
    again and again); the most common mistakes with the children who made them and an activity; and the next step for each group (the same suggestion the
    Plan screen makes, from the last review). Roll numbers only: the server reads no names; the page adds them on the teacher's phone."""
    from datetime import timedelta
    from app.services import group_skills as gs
    R = CLASS_RULES
    start = end - timedelta(days=R["window_days"] - 1)
    now = {d["domain_id"]: {l: d[f"{l}_count"] for l in gs.LABELS} for d in await get_bpp_summary(db, teacher_id)}
    plans = await db.fetch("""SELECT plan_date, domain_id, groups_snapshot, explainability FROM daily_plans
                              WHERE teacher_id = $1 AND plan_date BETWEEN $2 AND $3 ORDER BY plan_date""", teacher_id, start, end)
    runs = {}                                     # (domain, label, skill) -> {"days", "finals": {decision: n}, "rolls": the group on its last day}
    for r in plans:
        snap, expl = _obj(r["groups_snapshot"]), _obj(r["explainability"])
        for l in gs.LABELS:
            g = snap.get(l) or {}
            if not g.get("target") or not g.get("rolls"):
                continue
            run = runs.setdefault((r["domain_id"], l, g["target"]), {"days": 0, "finals": {"advance": 0, "reteach": 0, "not_sure": 0}, "rolls": []})
            run["days"] += 1
            run["rolls"] = sorted(int(x) for x in g["rolls"])
            final = expl.get(f"teacher_final_{l}") or expl.get(f"teacher_decision_{l}")          # older records have only teacher_decision_
            if final in run["finals"]:
                run["finals"][final] += 1
    names = {r["id"]: r["name_hi"] for r in await db.fetch("SELECT id, name_hi FROM competencies WHERE id = ANY($1::text[])", list({k[2] for k in runs}))} if runs else {}

    subjects = {}
    for domain in SUBJECTS:
        taught, stuck = [], []
        for (d, l, k), run in runs.items():
            if d != domain:
                continue
            taught.append({"level": l, "skill_id": k, "skill_name_hi": names.get(k), "days": run["days"], "finals": run["finals"]})
            if run["days"] >= R["stuck_days"]:
                # the children of the group (on its last day with this skill) whose newest result on the skill in the period is not "achieved", or who have none
                done = {x["roll_number"] for x in await db.fetch("""SELECT DISTINCT ON (c.roll_number) c.roll_number, e.status FROM assessment_evidence e JOIN children c ON c.id = e.child_id
                                                                    WHERE e.teacher_id = $1 AND e.competency_id = $2 AND e.session_date BETWEEN $3 AND $4
                                                                    ORDER BY c.roll_number, e.session_date DESC, e.created_at DESC""", teacher_id, k, start, end) if x["status"] == "achieved"}
                rolls = [x for x in run["rolls"] if x not in done]
                if rolls:
                    stuck.append({"level": l, "skill_id": k, "skill_name_hi": names.get(k), "days": run["days"], "rolls": rolls})
        order = {l: i for i, l in enumerate(gs.LABELS)}
        taught.sort(key=lambda x: (order[x["level"]], -x["days"], x["skill_id"]))
        stuck.sort(key=lambda x: (order[x["level"]], x["skill_id"]))
        achieved = await db.fetchval("""SELECT COUNT(*) FROM (SELECT DISTINCT e.child_id, e.competency_id FROM assessment_evidence e JOIN children c ON c.id = e.child_id
                                        JOIN competencies k ON k.id = e.competency_id JOIN subdomains s ON s.id = k.subdomain_id
                                        WHERE e.teacher_id = $1 AND e.status = 'achieved' AND e.session_date BETWEEN $2 AND $3 AND c.is_active AND s.domain_id = $4) x""",
                                     teacher_id, start, end, domain)
        prop = (await gs.propose(db, teacher_id, domain, end + timedelta(days=1)))["groups"]
        nxt = {l: {"skill_id": (g.get("proposed") or {}).get("id"), "skill_name_hi": (g.get("proposed") or {}).get("name_hi"), "reason": g.get("reason")} for l, g in prop.items()}
        if taught or any((now.get(domain) or {}).values()):
            subjects[domain] = {"groups_now": now.get(domain) or {}, "skills_achieved": achieved, "taught": taught, "stuck": stuck, "next": nxt}

    na = await db.fetch("""SELECT c.roll_number, COUNT(DISTINCT e.session_date) AS days, ARRAY_AGG(DISTINCT e.competency_id ORDER BY e.competency_id) AS skills
                           FROM assessment_evidence e JOIN children c ON c.id = e.child_id
                           WHERE e.teacher_id = $1 AND e.status = 'not_achieved' AND e.session_date BETWEEN $2 AND $3 AND c.is_active
                           GROUP BY c.roll_number HAVING COUNT(DISTINCT e.session_date) >= $4 ORDER BY c.roll_number""", teacher_id, start, end, R["na_days"])
    return {"period": {"start": start.isoformat(), "end": end.isoformat(), "days": R["window_days"]}, "subjects": subjects,
            "not_checked": await _not_checked(db, teacher_id, end, R["not_checked_days"]),
            "not_achieved_again": [{"roll": r["roll_number"], "days": r["days"], "skills": list(r["skills"])} for r in na],
            "mistakes": await _common_mistakes(db, teacher_id, start, end), "rules": dict(R)}


GROUP_HI = {"beginner": "शुरुआती", "progressor": "प्रगतिशील", "proficient": "दक्ष"}


def mentor_points(practice: dict, progress: dict, mistakes: list) -> dict:
    """The talking points, from fixed rules (MENTOR_RULES): the same numbers always give the same points. One strength, always first; then up to two
    things to work on, in this order of priority: a group stuck on a skill (with its most common mistake and an activity), the first judgment often
    differing from the evidence, groups decided without evidence, many children not checked; then one question for the teacher.
    NOTE: the wording is the app's working wording, for Vaishnavi's review (with the rule values)."""
    R = MENTOR_RULES
    p, g = practice, progress
    if p["review_days"]:
        strength = f"पिछले {R['window_days'] // 7} हफ़्तों में {p['plan_days']} दिन योजना बनी और {p['review_days']} दिन समीक्षा पूरी हुई।"
    elif g["skills_achieved"]:
        strength = f"पिछले {R['window_days'] // 7} हफ़्तों में बच्चों ने {g['skills_achieved']} कौशल हासिल किए।"
    elif p["plan_days"]:
        strength = f"पिछले {R['window_days'] // 7} हफ़्तों में {p['plan_days']} दिन योजना बनी।"
    else:
        strength = None                           # nothing in the period: the page says so instead of a point
    work = []
    for st in g["stuck"][:1]:
        m = next((x for x in mistakes if x["skill_id"] == st["skill_id"]), None)
        line = f"{GROUP_HI.get(st['level'], st['level'])} समूह में {st['skill_id']} {st['days']} दिन पढ़ाया गया।"
        if m:
            line += f" सबसे आम गलती: “{m['name_hi']}”" + (f"; सुझाई गई गतिविधि: “{m['activity']['title_hi']}”।" if m["activity"] else "।")
        work.append({"kind": "stuck", "hi": line})
    if p["judgments_compared"] >= R["match_min"] and p["judgments_matched"] / p["judgments_compared"] < R["match_share"]:
        work.append({"kind": "judgment", "hi": f"{p['judgments_compared']} में से {p['judgments_matched']} बार ही पहला अनुमान जाँच से मेल खाया: बात करें कि बच्चों का काम देखने से पहले वे समूह को कैसे आँकते हैं।"})
    if p["groups_taught"] and p["groups_checked"] / p["groups_taught"] < R["evidence_share"]:
        work.append({"kind": "evidence", "hi": f"{p['groups_taught']} में से {p['groups_checked']} बार ही समूह के बच्चों का काम जाँचा गया: हर समूह के कुछ बच्चों का काम देखकर निर्णय लेने पर बात करें।"})
    if g["class_size"] and len(g["not_checked"]) / g["class_size"] >= R["not_checked_share"]:
        work.append({"kind": "not_checked", "hi": f"{len(g['not_checked'])} बच्चों का काम {R['not_checked_days'] // 7} हफ़्ते से नहीं जाँचा गया।"})
    return {"strength": strength, "work": work[:2], "question": "किन बच्चों को अभी सबसे ज़्यादा मदद चाहिए, और आपको किस बात में मदद चाहिए?"}
