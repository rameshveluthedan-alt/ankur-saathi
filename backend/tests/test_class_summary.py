"""
The class summary (29 Oct): the teacher's own page for planning next week, over the last 4 weeks, per subject: the groups now and the skills achieved;
what each group was taught, on how many days, with the final decisions; the children to look at (stuck on the group's skill after 3+ days, not checked
for 2 weeks, "not achieved" on 2+ days); the most common mistakes with the children who made them and an activity; and each group's next step (the
Plan screen's own suggestion). Roll numbers only: the server reads no names (the phone adds them). Only the period counts.

    python tests/test_class_summary.py --env-file .env
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
    levels = {r: ("beginner" if r <= 4 else "progressor" if r <= 10 else "proficient",) * 2 for r in range(1, 13)}
    teacher_id, school = await _scratch.make_class(db, levels, grade="grade_2")
    kids = {r["roll_number"]: r["id"] for r in await db.fetch("SELECT id, roll_number FROM children WHERE teacher_id = $1", teacher_id)}
    D = date.today() + timedelta(days=80)
    leaf = "N3.3.1"

    async def put_plan(day, groups, expl):
        snap = {l: {"count": len(rolls), "rolls": rolls, "target": t} for l, (t, rolls) in groups.items()}
        await db.execute("""INSERT INTO daily_plans (teacher_id, plan_date, domain_id, selected_competency_id, plan_content, explainability, groups_snapshot)
                            VALUES ($1, $2, 'numeracy', 'N2.3.2', '{}'::jsonb, $3::jsonb, $4::jsonb)""", teacher_id, day, json.dumps(expl), json.dumps(snap))

    async def ev(roll, skill, status, day, mistake=None):
        await db.execute("""INSERT INTO assessment_evidence (child_id, competency_id, teacher_id, channel, status, evidence_data, detected_misconception_ids, session_date)
                            VALUES ($1, $2, $3, 'observed', $4, '{}'::jsonb, $5, $6)""", kids[roll], skill, teacher_id, status, [mistake] if mistake else [], day)

    B, P, PR = [1, 2, 3, 4], [5, 6, 7, 8, 9, 10], [11, 12]
    d30, d20, d10, d5, d1 = (D - timedelta(days=n) for n in (30, 20, 10, 5, 0))       # the last plan is TODAY's: its review gives the next step
    try:
        # before the period: a plan and results that must never count
        await put_plan(d30, {"progressor": ("N2.3.2", P)}, {"teacher_final_progressor": "advance"})
        await ev(9, "N2.3.2", "achieved", d30)
        await ev(5, "N2.3.2", "not_achieved", d30)
        # the period
        await put_plan(d20, {"beginner": ("N2.3.1", B), "progressor": ("N2.3.2", P), "proficient": (leaf, PR)},
                       {"teacher_final_beginner": "reteach", "teacher_final_progressor": "reteach", "teacher_final_proficient": "advance"})
        await put_plan(d10, {"beginner": ("N2.3.1", B), "progressor": ("N2.3.2", P)}, {"teacher_final_progressor": "reteach"})
        await put_plan(d5, {"beginner": ("N1.1.1", B), "progressor": ("N2.3.2", P)}, {"teacher_decision_progressor": "not_sure"})      # an older record: teacher_decision_ only
        await put_plan(d1, {"beginner": ("N2.3.1", [1, 2, 3]), "progressor": ("N2.3.2", P)},
                       {"teacher_final_beginner": "advance", "teacher_decision_beginner": "advance", "teacher_final_progressor": "advance", "teacher_decision_progressor": "reteach"})
        await ev(1, "N2.3.1", "achieved", d10)
        await ev(2, "N2.3.1", "achieved", d10)
        await ev(2, "N2.3.1", "not_achieved", d1, "N2.3.1-M1")         # newest result not achieved: still to look at
        await ev(2, "N2.3.1", "not_achieved", d1)                      # twice on the same day: still one day of "not achieved"
        for r in (5, 6):
            await ev(r, "N2.3.2", "not_achieved", d10, "N2.3.2-M1")
            await ev(r, "N2.3.2", "not_achieved", d5)
        await ev(7, "N2.3.2", "achieved", d1)
        await ev(8, "N2.3.2", "partially_achieved", d1)
        await ev(11, "L1.5.1", "achieved", d5)                          # a Hindi skill

        s = await ps.get_class_summary(db, teacher_id, D)
        num, lit = s["subjects"].get("numeracy", {}), s["subjects"].get("r1_literacy", {})
        print("the period and the class now")
        check("the last 4 weeks up to the teacher's day", s["period"] == {"start": str(D - timedelta(days=27)), "end": str(D), "days": 28}, s["period"])
        check("the groups now, per subject (the children's current levels)", num.get("groups_now") == {"beginner": 4, "progressor": 6, "proficient": 2} and lit.get("groups_now") == {"beginner": 4, "progressor": 6, "proficient": 2}, num.get("groups_now"))
        check("skills achieved in the period, per subject, once per child and skill, nothing from before (maths: rolls 1, 2, 7; Hindi: roll 11)", num.get("skills_achieved") == 3 and lit.get("skills_achieved") == 1, (num.get("skills_achieved"), lit.get("skills_achieved")))
        print("what was taught")
        check("each group's skills, Beginners first, most days first; the days in the period only (N2.3.2: 4, not 5)",
              [(t["level"], t["skill_id"], t["days"]) for t in num["taught"]] == [("beginner", "N2.3.1", 3), ("beginner", "N1.1.1", 1), ("progressor", "N2.3.2", 4), ("proficient", leaf, 1)], num["taught"])
        fin = {(t["level"], t["skill_id"]): t["finals"] for t in num["taught"]}
        check("the final decisions per skill (an older teacher_decision_ counts when there is no final)", fin[("progressor", "N2.3.2")] == {"advance": 1, "reteach": 2, "not_sure": 1}
              and fin[("beginner", "N2.3.1")] == {"advance": 1, "reteach": 1, "not_sure": 0} and fin[("beginner", "N1.1.1")] == {"advance": 0, "reteach": 0, "not_sure": 0}, fin)
        check("a subject with no plans still shows its groups, with nothing taught", lit.get("taught") == [] and lit.get("stuck") == [])
        print("the children to look at")
        check("stuck after 3+ days: the children of the group (as on its last day) whose newest result on the skill is not achieved, or who have none",
              [(x["level"], x["skill_id"], x["days"], x["rolls"]) for x in num["stuck"]] == [("beginner", "N2.3.1", 3, [2, 3]), ("progressor", "N2.3.2", 4, [5, 6, 8, 9, 10])], num["stuck"])
        check("not checked for 2 weeks: roll numbers", s["not_checked"] == [3, 4, 9, 10, 12], s["not_checked"])
        check("\"not achieved\" on 2 or more days in the period (roll 2: twice on one day is one day; roll 5's day from before the period does not count)",
              s["not_achieved_again"] == [{"roll": 5, "days": 2, "skills": ["N2.3.2"]}, {"roll": 6, "days": 2, "skills": ["N2.3.2"]}], s["not_achieved_again"])
        print("the mistakes")
        check("the most common first, with the children's roll numbers and an activity", [(m["misconception_id"], m["children"], m["rolls"]) for m in s["mistakes"]] == [("N2.3.2-M1", 2, [5, 6]), ("N2.3.1-M1", 1, [2])]
              and s["mistakes"][0]["activity"] and s["mistakes"][0]["activity"]["id"] == "INT-OP-005", s["mistakes"])
        print("the next step")
        nx = num["next"]
        check("the Progressors: the last review (today's) said re-teach, so the same skill", nx.get("progressor", {}).get("skill_id") == "N2.3.2" and nx["progressor"]["reason"] == "reteach", nx.get("progressor"))
        check("the Beginners: advance, so the next skill on from N2.3.1 (with its name)", nx.get("beginner", {}).get("reason") == "advance" and nx["beginner"]["skill_id"] not in (None, "N2.3.1") and nx["beginner"]["skill_name_hi"], nx.get("beginner"))
        check("the rules are part of the answer (printed on the page)", s["rules"] == ps.CLASS_RULES)

        print("\nthe route, and no names")
        views = lambda: db.fetchval("SELECT COUNT(*) FROM auth_events WHERE teacher_id = $1 AND event = 'class_summary_view'", teacher_id)
        before = await views()
        with TestClient(app) as c:
            r = c.get(f"/api/progress/class-summary/{teacher_id}?on={D}")
            check("GET /progress/class-summary/{teacher}?on= gives the same summary", r.status_code == 200 and r.json()["subjects"]["numeracy"]["stuck"] == num["stuck"], r.text[:200])
            c.get(f"/api/progress/class-summary/{teacher_id}?on={D}")
        check("each opening is logged (the page is shown with names, as the class report's export is): two openings, two entries", await views() - before == 2, await views() - before)
        src = open(os.path.join(HERE, "..", "app", "services", "progress_service.py"), encoding="utf-8").read()
        body = src[src.index("async def get_class_summary"):src.index("GROUP_HI = {")]
        check("the summary never reads the children's names (no child_names, no names_service)", "child_names" not in body and "names_service" not in body)
    finally:
        await db.execute("DELETE FROM auth_events WHERE teacher_id = $1", teacher_id)
        await _scratch.remove_class(db, teacher_id, school)
        await db.close()
    if failures:
        print(f"\nFAILED ({len(failures)})")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("\nOK: the class summary counts the last 4 weeks only, names the children to look at by roll number, and gives each group's next step")


if __name__ == "__main__":
    asyncio.run(main())
