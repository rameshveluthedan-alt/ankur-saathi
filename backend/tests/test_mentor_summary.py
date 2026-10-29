"""
The mentor summary (29 Oct): one page for a block or cluster officer's visit, over the last 4 weeks. How the teacher works (plans made, reviews completed,
groups checked with evidence, the first judgment against the evidence), how the children moved (the groups at the start and the end, skills achieved,
groups taught the same skill again and again, children not checked), the most common mistakes with a matching activity, and talking points from FIXED
rules: one strength first, then up to two things to work on (in a set order), then a question. Counts and roll numbers only, never a name. Only the
period counts: a plan or a result from before it never shows.

    python tests/test_mentor_summary.py --env-file .env
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import asyncio
import json
import os
import sys
from datetime import date, timedelta

os.environ.setdefault("AUTH_MODE", "off")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(HERE, "..", "..", "prompts"), os.path.join(HERE, "..")]

failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


async def main():
    import _scratch
    from fastapi.testclient import TestClient
    from app.main import app
    from app.services import progress_service as ps
    db = await _scratch.connect()
    # rolls 1-4 Beginners, 5-10 Progressors, 11-12 Proficients
    levels = {r: ("beginner" if r <= 4 else "progressor" if r <= 10 else "proficient",) * 2 for r in range(1, 13)}
    teacher_id, school = await _scratch.make_class(db, levels, grade="grade_2")
    kids = {r["roll_number"]: r["id"] for r in await db.fetch("SELECT id, roll_number FROM children WHERE teacher_id = $1", teacher_id)}
    D = date.today() + timedelta(days=60)          # the officer's "today", far from any real data
    leaf = "N3.3.1"

    async def put_plan(day, groups, expl, domain="numeracy"):
        snap = {l: {"count": len(rolls), "rolls": rolls, "target": t} for l, (t, rolls) in groups.items()}
        await db.execute("""INSERT INTO daily_plans (teacher_id, plan_date, domain_id, selected_competency_id, plan_content, explainability, groups_snapshot)
                            VALUES ($1, $2, $5, 'N2.3.2', '{}'::jsonb, $3::jsonb, $4::jsonb)""", teacher_id, day, json.dumps(expl), json.dumps(snap), domain)

    async def ev(roll, skill, status, day, mistake=None):
        await db.execute("""INSERT INTO assessment_evidence (child_id, competency_id, teacher_id, channel, status, evidence_data, detected_misconception_ids, session_date)
                            VALUES ($1, $2, $3, 'observed', $4, '{}'::jsonb, $5, $6)""", kids[roll], skill, teacher_id, status, [mistake] if mistake else [], day)

    B, P, PR = [1, 2, 3, 4], [5, 6, 7, 8, 9, 10], [11, 12]
    try:
        empty = await ps.get_mentor_summary(db, teacher_id, D)
        check("nothing in the period: no strength to invent; the one true point is that nobody was checked; still the question", empty["points"]["strength"] is None
              and [w["kind"] for w in empty["points"]["work"]] == ["not_checked"] and empty["points"]["question"]
              and empty["practice"]["plan_days"] == 0, empty["points"])

        # BEFORE the period (day 30 back): a plan, a result and a mistake that must never count
        await put_plan(D - timedelta(days=30), {"progressor": ("N2.3.2", P)}, {"teacher_final_progressor": "advance"})
        await ev(9, "N2.3.2", "achieved", D - timedelta(days=30))
        await ev(1, "N2.3.1", "not_achieved", D - timedelta(days=30), "N2.3.2-M2")

        # IN the period: four days of plans
        d20, d10, d5, d1 = (D - timedelta(days=n) for n in (20, 10, 5, 1))
        await put_plan(d20, {"beginner": ("N2.3.1", B), "progressor": ("N2.3.2", P), "proficient": (leaf, PR)},
                       {"teacher_first_beginner": "reteach", "teacher_final_beginner": "reteach", "teacher_final_progressor": "reteach", "teacher_final_proficient": "advance"})
        await put_plan(d10, {"beginner": ("N1.1.1", B), "progressor": ("N2.3.2", P)}, {"teacher_first_progressor": "advance"})
        await put_plan(d5, {"beginner": ("N1.1.1", B), "progressor": ("N2.3.2", P)}, {"teacher_decision_progressor": "advance", "teacher_final_beginner": "advance"})        # an older record: teacher_decision_ only; a final for one group only
        await put_plan(d1, {"beginner": ("N2.3.1", [1, 2, 3]), "progressor": ("N2.3.2", [4] + P), "proficient": (leaf, PR)},
                       {"teacher_first_progressor": "advance", "teacher_first_proficient": "advance", "teacher_final_beginner": "advance", "teacher_final_progressor": "reteach", "teacher_final_proficient": "advance"})
        for day in (d20, d10, d5):                          # Hindi: the Beginners on one skill on exactly 3 days (the "stuck" rule's edge), on days that already have a plan
            await put_plan(day, {"beginner": ("L1.5.1", B)}, {}, domain="r1_literacy")
        for r in B:                                         # day 20: every Beginner made a mistake; the first judgment (re-teach) matches
            await ev(r, "N2.3.1", "not_achieved", d20, "N2.3.1-M1")
        await ev(11, leaf, "achieved", d20)
        for day in (d10, d5, d1):                           # the Progressors, three days: 3 of 4 made a mistake, but the first judgment was "advance"
            for r in (5, 6, 7):
                await ev(r, "N2.3.2", "partially_achieved", day, "N2.3.2-M1")
            await ev(8, "N2.3.2", "achieved", day)
        await ev(12, leaf, "not_achieved", d1)              # day 1: one Proficient checked, a very small group: not compared with the first judgment
        await ev(9, "N2.3.2", "achieved", d5)
        await ev(9, "N2.3.2", "achieved", d1)               # the same skill achieved twice counts once

        m = await ps.get_mentor_summary(db, teacher_id, D)
        p, g = m["practice"], m["progress"]
        print("the period")
        check("the last 4 weeks up to the officer's day", m["period"] == {"start": str(D - timedelta(days=27)), "end": str(D), "days": 28}, m["period"])
        check("the school's code (block and district beside it); no teacher name anywhere", m["school"]["school_code"] == school and "name" not in json.dumps(m["school"]))
        print("how the teacher works")
        check("plans made on 4 days (days, not plans: a day with both subjects counts once; the plan from before the period does not count)", p["plan_days"] == 4, p)
        check("reviews completed on 2 days: every group taught has a final decision (day 20, day 1); day 5 has a final for one group of two: not complete", p["review_days"] == 2, p)
        check("groups taught 13 times (10 in maths, 3 in Hindi), checked with evidence 6 times (day 20: the Beginners and the Proficients; the Progressors on days 10, 5, 1; the Proficients on day 1)", p["groups_taught"] == 13 and p["groups_checked"] == 6, p)
        check("the first judgment against the evidence: 4 groups could be compared (not the Proficients on day 1: one child checked is a very small group), it matched once (an older teacher_decision_ counts as a first judgment)",
              p["judgments_compared"] == 4 and p["judgments_matched"] == 1, p)
        print("how the children moved")
        check("the groups at the start of the period and at its end (from the plans' own group lists)", g["groups"]["numeracy"]["start"] == {"beginner": 4, "progressor": 6, "proficient": 2}
              and g["groups"]["numeracy"]["end"] == {"beginner": 3, "progressor": 7, "proficient": 2} and g["groups"]["numeracy"]["start_date"] == str(d20), g["groups"])
        check("skills achieved in the period: once per child and skill, nothing from before (roll 8, roll 9, roll 11)", g["skills_achieved"] == 3, g["skills_achieved"])
        check("taught the same skill on 3 or more days, most days first: the Progressors N2.3.2 on 4 (not 5: day 30 is outside), the Hindi Beginners L1.5.1 on exactly 3; the maths Beginners' two skills (2 days each) are not",
              [(x["domain_id"], x["level"], x["skill_id"], x["days"]) for x in g["stuck"]] == [("numeracy", "progressor", "N2.3.2", 4), ("r1_literacy", "beginner", "L1.5.1", 3)] and g["stuck"][0]["skill_name_hi"], g["stuck"])
        check("not checked for 2 weeks: the roll numbers of those with no result since day 13 (the class has 12)", g["not_checked"] == [1, 2, 3, 4, 10, 11] and g["class_size"] == 12, g["not_checked"])
        print("the mistakes")
        check("the most common first, by children (a child once per mistake); the one from before the period is not there", [(x["misconception_id"], x["children"]) for x in m["mistakes"]] == [("N2.3.1-M1", 4), ("N2.3.2-M1", 3)], m["mistakes"])
        act = m["mistakes"][1]["activity"]
        check("each with a matching activity from the content bank (the mistake's own first: INT-OP-005)", act and act["id"] == "INT-OP-005" and act["title_hi"], act)
        print("the talking points (fixed rules)")
        pts = m["points"]
        check("the strength comes first: days with a plan and days with a full review", pts["strength"] == "पिछले 4 हफ़्तों में 4 दिन योजना बनी और 2 दिन समीक्षा पूरी हुई।", pts["strength"])
        check("at most two things to work on, in the set order: the stuck group first, then the first judgment (evidence and not-checked also apply, but wait)", [w["kind"] for w in pts["work"]] == ["stuck", "judgment"], pts["work"])
        check("the stuck point names the group, the skill, the days, its most common mistake and the activity", pts["work"][0]["hi"].startswith("प्रगतिशील समूह में N2.3.2 4 दिन पढ़ाया गया।")
              and m["mistakes"][1]["name_hi"] in pts["work"][0]["hi"] and act["title_hi"] in pts["work"][0]["hi"], pts["work"][0]["hi"])
        check("the judgment point gives the numbers: 4 में से 1", pts["work"][1]["hi"].startswith("4 में से 1 बार ही पहला अनुमान जाँच से मेल खाया"), pts["work"][1]["hi"])
        check("and one question for the teacher", pts["question"].startswith("किन बच्चों को अभी सबसे ज़्यादा मदद चाहिए"))
        check("the rules are part of the answer (printed on the page)", m["rules"] == ps.MENTOR_RULES)

        print("the rules on their own")
        base_p = {"plan_days": 10, "review_days": 0, "groups_taught": 10, "groups_checked": 5, "judgments_compared": 2, "judgments_matched": 0}
        base_g = {"class_size": 20, "skills_achieved": 0, "stuck": [], "not_checked": [1, 2, 3, 4]}
        check("no review completed: the strength falls back to skills achieved, then to plans made", ps.mentor_points(base_p, {**base_g, "skills_achieved": 6}, [])["strength"] == "पिछले 4 हफ़्तों में बच्चों ने 6 कौशल हासिल किए।"
              and ps.mentor_points(base_p, base_g, [])["strength"] == "पिछले 4 हफ़्तों में 10 दिन योजना बनी।")
        check("exactly half the groups checked, fewer than 3 judgments compared, under a quarter not checked: nothing to work on", ps.mentor_points(base_p, base_g, [])["work"] == [])
        check("4 of 10 checked: the evidence point", [w["kind"] for w in ps.mentor_points({**base_p, "groups_checked": 4}, base_g, [])["work"]] == ["evidence"])
        check("a quarter of the class not checked: the not-checked point", [w["kind"] for w in ps.mentor_points(base_p, {**base_g, "not_checked": [1, 2, 3, 4, 5]}, [])["work"]] == ["not_checked"])
        check("a stuck group with no mistake recorded: the point without a mistake or activity", ps.mentor_points(base_p, {**base_g, "stuck": [{"level": "beginner", "skill_id": "N1.1.1", "days": 3}]}, [])["work"][0]["hi"] == "शुरुआती समूह में N1.1.1 3 दिन पढ़ाया गया।")

        print("\nthe route, and no names")
        with TestClient(app) as c:
            r = c.get(f"/api/progress/mentor/{teacher_id}?on={D}")
            check("GET /progress/mentor/{teacher}?on= gives the same summary", r.status_code == 200 and r.json()["practice"] == p and r.json()["points"] == pts, r.text[:200])
        src = open(os.path.join(HERE, "..", "app", "services", "progress_service.py"), encoding="utf-8").read()
        body = src[src.index("async def get_mentor_summary"):]
        check("the summary never reads the children's names (no child_names, no names_service)", "child_names" not in body and "names_service" not in body)
    finally:
        await _scratch.remove_class(db, teacher_id, school)
        await db.close()
    if failures:
        print(f"\nFAILED ({len(failures)})")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("\nOK: the mentor summary counts the last 4 weeks only, names no child, and its talking points follow the fixed rules")


if __name__ == "__main__":
    asyncio.run(main())
