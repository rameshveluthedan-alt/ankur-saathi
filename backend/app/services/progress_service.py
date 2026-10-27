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
