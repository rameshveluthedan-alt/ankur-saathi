"""
What the Progress screen shows about TODAY: per group, the A/PA/NA counts of today's sample, the decision recorded at today's review, and the two rare lines
(the decision disagrees with the evidence; advanced but there is no next skill); per child, today's result. Only today counts: a different day's plan, decision
or result never shows. Also the reading-aloud save: it is scored on the skill it was given, and an unknown roll number is a failed save.

    python tests/test_progress_today.py --env-file .env
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
    from app.services import progress_service as ps, group_skills as gs
    db = await _scratch.connect()
    # rolls 1-4 Beginners, 5-6 Progressors, 7-8 Proficients
    levels = {1: "beginner", 2: "beginner", 3: "beginner", 4: "beginner", 5: "progressor", 6: "progressor", 7: "proficient", 8: "proficient"}
    teacher_id, school = await _scratch.make_class(db, {r: (lv, lv) for r, lv in levels.items()}, grade="grade_2")
    kids = {r["roll_number"]: r["id"] for r in await db.fetch("SELECT id, roll_number FROM children WHERE teacher_id = $1", teacher_id)}
    D = date.today() + timedelta(days=40)          # "today" for the test, far from any real data
    Y = D - timedelta(days=1)                       # yesterday
    leaf = await db.fetchval("""SELECT c.id FROM competencies c JOIN subdomains s ON s.id = c.subdomain_id
                                WHERE s.domain_id = 'numeracy' AND NOT EXISTS (SELECT 1 FROM competency_prerequisites p WHERE p.prerequisite_id = c.id)
                                  AND NOT EXISTS (SELECT 1 FROM skill_bridges b WHERE b.skill_id = c.id AND b.approved AND b.successor_id IS NOT NULL)
                                ORDER BY c.id LIMIT 1""")
    rolls = {"beginner": [1, 2, 3, 4], "progressor": [5, 6], "proficient": [7, 8]}

    async def put_plan(day, targets, decisions):
        snap = {l: {"count": len(rolls[l]), "rolls": rolls[l], "target": t} for l, t in targets.items()}
        await db.execute("""INSERT INTO daily_plans (teacher_id, plan_date, domain_id, selected_competency_id, plan_content, explainability, groups_snapshot)
                            VALUES ($1, $2, 'numeracy', 'N2.3.2', '{}'::jsonb, $3::jsonb, $4::jsonb)
                            ON CONFLICT (teacher_id, plan_date, domain_id) DO UPDATE SET explainability = EXCLUDED.explainability, groups_snapshot = EXCLUDED.groups_snapshot""",
                         teacher_id, day, json.dumps({f"teacher_decision_{l}": d for l, d in decisions.items()}), json.dumps(snap))

    async def ev(roll, skill, status, day, channel="observed", mistake=False, minutes=0):
        await db.execute("""INSERT INTO assessment_evidence (child_id, competency_id, teacher_id, channel, status, evidence_data, detected_misconception_ids, session_date, created_at)
                            VALUES ($1, $2, $3, $4, $5, '{}'::jsonb, $6, $7, NOW() + make_interval(mins => $8))""",
                         kids[roll], skill, teacher_id, channel, status, ["M_TEST"] if mistake else [], day, minutes)

    try:
        check(f"a skill with no next skill exists for the 'advanced, no next skill' case ({leaf})", bool(leaf) and not await gs.next_options(db, leaf))

        # YESTERDAY: different decisions and different results, which must never show today
        await put_plan(Y, {"beginner": "N2.3.1", "progressor": "N2.3.2", "proficient": leaf}, {"beginner": "reteach", "progressor": "reteach", "proficient": "not_sure"})
        await ev(1, "N2.3.1", "not_achieved", Y)
        await ev(5, "N2.3.2", "achieved", Y)             # roll 5 is assessed ONLY yesterday
        await ev(6, "N2.3.2", "not_achieved", Y)

        # TODAY
        await put_plan(D, {"beginner": "N2.3.1", "progressor": "N2.3.2", "proficient": leaf}, {"beginner": "advance", "proficient": "advance"})
        await ev(1, "N2.3.1", "achieved", D)
        await ev(2, "N2.3.1", "partially_achieved", D, channel="written_photo", mistake=True)
        await ev(2, "N2.3.1", "achieved", D, minutes=5)    # a later observation of the same child replaces the photo: counted once, as A
        await ev(3, "N2.3.1", "not_achieved", D, mistake=True)
        await ev(4, "N2.3.1", "not_achieved", D, mistake=True)
        await ev(6, "N1.1.1", "achieved", D)                # roll 6 is assessed today, but not on the group's skill
        await ev(7, leaf, "achieved", D)

        t = await ps.get_today(db, teacher_id, D)
        num = t["subjects"]["numeracy"]
        b, p, f = (num["by_level"][l] for l in ("beginner", "progressor", "proficient"))

        print("\nthe per-group summary of today")
        check("today has a plan, and each group carries its skill from TODAY's plan", num["has_plan"] and b["skill_id"] == "N2.3.1" and p["skill_id"] == "N2.3.2" and f["skill_id"] == leaf, num)
        check("the Beginners: A 2, PA 0, NA 2 (roll 2 counted once, by its newest result), assessed 4 of 4", (b["a"], b["pa"], b["na"], b["assessed"], b["group_size"]) == (2, 0, 2, 4, 4), b)
        check("for every group A + PA + NA equals assessed", all(g["a"] + g["pa"] + g["na"] == g["assessed"] for g in num["by_level"].values()), num["by_level"])
        check("the decision is TODAY's: the Beginners advance (yesterday they were to re-teach)", b["decision"] == "advance")
        check("the Progressors had a decision yesterday but none today: no decision is shown", p["decision"] is None, p)
        check("the Progressors were assessed only yesterday (and one off their skill today): assessed 0 today", p["assessed"] == 0 and p["a"] == p["pa"] == p["na"] == 0, p)
        check("advance although the evidence recommends a re-teach (3 of 4 made a mistake): conflict is set", b["conflict"] is True)
        check("advance where the evidence agrees: no conflict", f["conflict"] is False, f)
        check(f"the Proficients advanced on {leaf}, which has no next skill: advance_no_next is set", f["advance_no_next"] is True, f)
        check("the Beginners' skill has a next skill: advance_no_next is not set", b["advance_no_next"] is False)
        check("a group with no decision has neither rare line", p["conflict"] is False and p["advance_no_next"] is False)

        print("\neach child's result today")
        kid = t["children"]
        check("roll 1: today's A on today's skill (yesterday's NA never shows)", kid.get("1", {}).get("numeracy") == {"skill_id": "N2.3.1", "status": "achieved"}, kid.get("1"))
        check("roll 2: the newest result of the day (A), not the earlier photo (PA)", kid["2"]["numeracy"]["status"] == "achieved")
        check("roll 5 was assessed only yesterday: nothing today", "numeracy" not in kid.get("5", {}), kid.get("5"))
        check("roll 6 was assessed today only off the group's skill: the newest of the day is shown", kid.get("6", {}).get("numeracy") == {"skill_id": "N1.1.1", "status": "achieved"}, kid.get("6"))
        check("roll 8 was not assessed today: nothing", "8" not in kid)
        check("a subject with no plan today: has_plan is false, no decisions, nothing assessed", (not t["subjects"]["r1_literacy"]["has_plan"]) and all(g["assessed"] == 0 and g["decision"] is None for g in t["subjects"]["r1_literacy"]["by_level"].values()))
        ty = await ps.get_today(db, teacher_id, Y)
        check("asked for yesterday, it gives yesterday's own decisions and results (the day is a real filter)", ty["subjects"]["numeracy"]["by_level"]["beginner"]["decision"] == "reteach" and ty["children"]["5"]["numeracy"]["status"] == "achieved")

        print("\nthe dashboard and the reading-aloud save")
        with TestClient(app) as c:
            r = c.get(f"/api/progress/dashboard/{teacher_id}?on={D}")
            j = r.json() if r.status_code == 200 else {}
            check("GET /progress/dashboard?on= carries today per subject, with the day it is about", r.status_code == 200 and j.get("today", {}).get("date") == str(D) and j["today"]["numeracy"]["by_level"]["beginner"]["a"] == 2, r.text[:200])
            row1 = next((x for x in j.get("children", []) if x["roll_number"] == 1), {})
            row8 = next((x for x in j.get("children", []) if x["roll_number"] == 8), {})
            check("each child row carries numeracy_today / literacy_today (None when nothing was recorded today)", row1.get("numeracy_today") == {"skill_id": "N2.3.1", "status": "achieved"} and row1.get("literacy_today") is None and row8.get("numeracy_today") is None, row1)
            check("the dashboard still has what it had before", all(k in j for k in ("bpp_summary", "children", "reassessment_flags")))
            r = c.post(f"/api/review/orf?teacher_id={teacher_id}", json={"session_date": str(D), "roll_number": 999, "passage_id": "RP-004", "cwpm": 30, "error_count": 0})
            check("reading aloud for an unknown roll number is a failed save (HTTP 404), not a success", r.status_code == 404, f"{r.status_code} {r.text[:120]}")
            r = c.post(f"/api/review/orf?teacher_id={teacher_id}", json={"session_date": str(D), "roll_number": 2, "passage_id": "RP-004", "cwpm": 20, "error_count": 1, "competency_id": "L1.5.1"})
            st = await db.fetchval("SELECT competency_id FROM assessment_evidence WHERE teacher_id = $1 AND channel = 'oral_reading' ORDER BY created_at DESC LIMIT 1", teacher_id)
            check("reading aloud is scored on the skill it was given: 20 CWPM on L1.5.1 is PA (on the old default L2.5.1 it would be NA)", r.status_code == 200 and r.json()["classification"] == "partially_achieved" and st == "L1.5.1", r.text[:160])
            r = c.post(f"/api/review/orf?teacher_id={teacher_id}", json={"session_date": str(D), "roll_number": 2, "passage_id": "RP-004", "cwpm": 20, "error_count": 1})
            check("without a skill it still works, on Grade 2 reading (L2.5.1): 20 CWPM is NA", r.status_code == 200 and r.json()["classification"] == "not_achieved", r.text[:160])
    finally:
        await _scratch.remove_class(db, teacher_id, school)
        await db.close()
    if failures:
        print(f"\nFAILED ({len(failures)})")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("\nOK: the Progress screen's 'today' counts only today, once per child, with today's decision; reading aloud is scored on its own skill")


if __name__ == "__main__":
    asyncio.run(main())
