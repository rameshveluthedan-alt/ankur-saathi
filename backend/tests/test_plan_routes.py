"""
GET /plan/{teacher}/{date}/{subject} tells the Plan screen what has already been recorded against the stored plan (has_evidence, evidence_by_group),
so it can warn before the plan is replaced. Counted per group: the children in the plan's snapshot, on that day, on the group's own skill, any channel.
No AI call.

    cd backend && AUTH_MODE=off python tests/test_plan_routes.py --env-file .env
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
sys.path.insert(0, os.path.join(HERE, "..", "..", "prompts"))
import _scratch
from fastapi.testclient import TestClient
from app.main import app

TODAY = date.today()
failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


SNAPSHOT = {"beginner": {"count": 3, "rolls": [1, 2, 3], "target": "N2.3.1"},
            "progressor": {"count": 3, "rolls": [4, 5, 6], "target": "N2.3.2"},
            "proficient": {"count": 2, "rolls": [7, 8], "target": "N3.3.1"}}
ZERO = {"beginner": 0, "progressor": 0, "proficient": 0}


async def main():
    db = await _scratch.connect()
    levels = {1: "beginner", 2: "beginner", 3: "beginner", 4: "progressor", 5: "progressor", 6: "progressor", 7: "proficient", 8: "proficient"}
    teacher_id, school = await _scratch.make_class(db, {r: (lv, lv) for r, lv in levels.items()}, grade="grade_2")
    other_id, other_school = await _scratch.make_class(db, {1: ("beginner", "beginner")}, grade="grade_2")
    kid = {r["roll_number"]: r["id"] for r in await db.fetch("SELECT id, roll_number FROM children WHERE teacher_id = $1", teacher_id)}

    async def plan(day, snapshot=SNAPSHOT):
        await db.execute("""
            INSERT INTO daily_plans (teacher_id, plan_date, domain_id, selected_competency_id, plan_content, explainability, groups_snapshot, generation_time_ms, claude_model)
            VALUES ($1, $2, 'numeracy', 'N2.3.2', $3, '{}'::jsonb, $4, 0, 'test')
            ON CONFLICT (teacher_id, plan_date, domain_id) DO UPDATE SET groups_snapshot = EXCLUDED.groups_snapshot""",
            teacher_id, day, json.dumps({"rotation_schedule": {"blocks": []}, "session_minutes": 90}), json.dumps(snapshot))

    async def evidence(roll, skill, day, channel="observed", by=None):
        await db.execute("""
            INSERT INTO assessment_evidence (child_id, competency_id, teacher_id, channel, status, evidence_data, session_date)
            VALUES ($1, $2, $3, $4, 'achieved', '{}'::jsonb, $5)""", kid[roll], skill, by or teacher_id, channel, day)

    try:
        with TestClient(app) as c:
            def get(day):
                r = c.get(f"/api/plan/{teacher_id}/{day}/numeracy")
                return r.status_code, (r.json() if r.status_code == 200 else {})

            print("B1: a plan with nothing recorded")
            D1 = TODAY
            await plan(D1)
            st, j = get(D1)
            check("has_evidence is false and every group counts 0 (all three groups are in the reply)", st == 200 and j.get("has_evidence") is False and j.get("evidence_by_group") == ZERO, j.get("evidence_by_group"))
            check("the rest of the reply is unchanged: plan, groups, selected skill, served_from", all(k in j for k in ("plan", "groups", "selected_competency_id", "served_from", "plan_date")) and j["plan"]["session_minutes"] == 90)

            print("\nB2: one observation for a Progressor on the Progressors' skill, that day")
            await evidence(4, "N2.3.2", D1)
            st, j = get(D1)
            check("has_evidence is true: Progressor 1, the others 0", j.get("has_evidence") is True and j.get("evidence_by_group") == {"beginner": 0, "progressor": 1, "proficient": 0}, j.get("evidence_by_group"))
            await evidence(4, "N2.3.2", D1, channel="oral_reading")
            check("the same child recorded twice (two channels) is counted once", get(D1)[1]["evidence_by_group"]["progressor"] == 1)

            print("\nB3: results that must NOT count")
            D3 = TODAY + timedelta(days=10)
            await plan(D3 - timedelta(days=1))
            await plan(D3)
            await evidence(4, "N2.3.2", D3 - timedelta(days=1))           # the day before (against yesterday's plan)
            await evidence(4, "N1.1.1", D3)                              # that day, another skill
            await evidence(4, "N2.3.2", D3, by=other_id)                 # that day, the right skill, recorded by another teacher
            await evidence(1, "N2.3.2", D3)                              # that day, the Progressors' skill, but roll 1 is a Beginner in the snapshot
            st, j = get(D3)
            check("yesterday, another skill, another teacher, a child outside the group's snapshot: has_evidence stays false", j.get("has_evidence") is False and j.get("evidence_by_group") == ZERO, j.get("evidence_by_group"))
            check("(and yesterday's plan does see its own result)", get(D3 - timedelta(days=1))[1].get("evidence_by_group", {}).get("progressor") == 1)

            print("\nB4: a photo result")
            D4 = TODAY + timedelta(days=20)
            await plan(D4)
            await evidence(2, "N2.3.1", D4, channel="written_photo")
            st, j = get(D4)
            check("a written_photo row (written as soon as the AI reads the sheet) counts: Beginner 1", j.get("has_evidence") is True and j["evidence_by_group"]["beginner"] == 1, j.get("evidence_by_group"))

            print("\nthe day's review decisions come back with the plan (the Review carries on where the teacher left it)")
            st, j = get(D1)
            check("nothing decided yet: decisions is empty", j.get("decisions") == {}, j.get("decisions"))
            r = c.post(f"/api/review/decisions?teacher_id={teacher_id}", json={"plan_date": str(D1), "domain_id": "numeracy", "decisions": {"beginner": "advance", "progressor": "reteach"}})
            st, j = get(D1)
            check("after Review step 1: the two decisions, exactly as recorded", r.status_code == 200 and j.get("decisions") == {"beginner": "advance", "progressor": "reteach"}, (r.status_code, j.get("decisions")))
            check("...and only that day's: another day's plan has none", get(D3)[1].get("decisions") == {})
            check("a save without a stage is the first judgment (an older app is unchanged)", get(D1)[1].get("first_judgments") == {"beginner": "advance", "progressor": "reteach"} and get(D1)[1].get("final_decisions") == {})

            print("\nthe Review's two stages: the first judgment, then the final decision with today's evidence")
            dec = lambda d, stage: c.post(f"/api/review/decisions?teacher_id={teacher_id}", json={"plan_date": str(D1), "domain_id": "numeracy", "decisions": d, "stage": stage})
            r = dec({"beginner": "reteach", "progressor": "reteach"}, "final")
            st, j = get(D1)
            check("the final decision becomes the current decision (what tomorrow's plan suggests from): Beginners now re-teach",
                  r.status_code == 200 and j["decisions"] == {"beginner": "reteach", "progressor": "reteach"} and j["final_decisions"] == {"beginner": "reteach", "progressor": "reteach"}, j.get("decisions"))
            check("...and the first judgment is kept as it was (Beginners: advance), so the screen can say it changed", j["first_judgments"] == {"beginner": "advance", "progressor": "reteach"}, j.get("first_judgments"))
            check("a stage that is neither is refused", dec({"beginner": "advance"}, "maybe").status_code == 422)
            ev = j.get("today_evidence") or {}
            check("today's evidence per group comes with the plan: the Progressors' child observed this morning (A 1, assessed 1 of 3), with whether a re-teach is suggested",
                  ev.get("progressor", {}).get("a") == 1 and ev["progressor"].get("assessed") == 1 and ev["progressor"].get("group_size") == 3 and "recommend" in ev["progressor"], ev.get("progressor"))
            for roll in (1, 2):                  # two Beginners' photos found a mistake: two of the three, so a re-teach is suggested
                await db.execute("""INSERT INTO assessment_evidence (child_id, competency_id, teacher_id, channel, status, evidence_data, detected_misconception_ids, session_date)
                                    VALUES ($1, 'N2.3.1', $2, 'written_photo', 'not_achieved', '{}'::jsonb, $3, $4)""",
                                 kid[roll], teacher_id, ["N2.3.1-M1"], D1)
            ev = get(D1)[1]["today_evidence"]
            check("two Beginners' sheets with a mistake, but only two checked: too few to suggest anything (very_small), the counts still shown",
                  ev["beginner"]["recommend"] is False and ev["beginner"]["very_small"] is True and ev["beginner"]["na"] == 2, ev["beginner"])
            D6 = TODAY + timedelta(days=50)
            await plan(D6, {"progressor": {"count": 6, "rolls": [1, 2, 3, 4, 5, 6], "target": "N2.3.2"}})
            for roll, wrong in ((1, True), (2, True), (3, False), (4, False), (5, False), (6, False)):
                await db.execute("""INSERT INTO assessment_evidence (child_id, competency_id, teacher_id, channel, status, evidence_data, detected_misconception_ids, session_date)
                                    VALUES ($1, 'N2.3.2', $2, 'written_photo', $3, '{}'::jsonb, $4, $5)""",
                                 kid[roll], teacher_id, 'not_achieved' if wrong else 'achieved', ["N2.3.2-M1"] if wrong else None, D6)
            ev6 = get(D6)[1]["today_evidence"]["progressor"]
            check("six checked, two with a mistake (a third): the evidence suggests a re-teach (the same rule as the Plan screen)", ev6["recommend"] is True and ev6["very_small"] is False and ev6["assessed"] == 6, ev6)

            print("\nan older snapshot, and no plan")
            D5 = TODAY + timedelta(days=30)
            await plan(D5, {"beginner": {"count": 3, "target": "N2.3.1"}, "progressor": {"count": 3, "target": "N2.3.2"}})
            await evidence(1, "N2.3.2", D5)
            st, j = get(D5)
            check("a snapshot without roll numbers counts any of the teacher's children on the group's skill (a missing list never hides evidence)", j.get("has_evidence") is True and j["evidence_by_group"]["progressor"] == 1, j.get("evidence_by_group"))
            st, j = get(TODAY + timedelta(days=40))
            check("no plan that day: still HTTP 404 (the Plan screen shows its open picker)", st == 404, st)
    finally:
        await db.execute("DELETE FROM assessment_evidence WHERE child_id = ANY($1::uuid[])", list(kid.values()))
        await db.execute("DELETE FROM daily_plans WHERE teacher_id = $1", teacher_id)
        await _scratch.remove_class(db, other_id, other_school)
        await _scratch.remove_class(db, teacher_id, school)
        await db.close()
    if failures:
        print(f"\nFAILED ({len(failures)})")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("\nOK: the stored plan says what has been recorded against it, per group, that day, on each group's own skill, for the children in its snapshot")


if __name__ == "__main__":
    asyncio.run(main())
