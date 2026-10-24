"""
The demo seed stores YESTERDAY'S PLAN (with the groups, their roll numbers and skills, and the teacher's recorded decisions), so the Plan screen has a yesterday to suggest from.

    cd backend && python tests/test_demo_seed.py --env-file .env

Everything runs inside a transaction that is ROLLED BACK at the end: your local demo data is not changed.
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
sys.path[:0] = [os.path.join(HERE, "..", "..", "scripts"), os.path.join(HERE, "..", "..", "prompts"), os.path.join(HERE, "..")]
import demo_progress as dp

failures = []


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


def obj(v):
    return json.loads(v) if isinstance(v, str) else (v or {})


async def main():
    import _scratch
    from app.services import group_skills as gs
    db = await _scratch.connect()
    T, end = dp.DEMO_TEACHER, date.today() - timedelta(days=1)
    before = await db.fetchval("SELECT count(*) FROM daily_plans WHERE teacher_id = $1", T)
    tr = db.transaction()
    await tr.start()
    try:
        async def plan_row(day):
            return await db.fetchrow("SELECT selected_competency_id, plan_content, explainability, groups_snapshot FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2 AND domain_id = 'numeracy'", T, day)
        real_day = end - timedelta(days=5)
        await db.execute("INSERT INTO daily_plans (teacher_id, plan_date, domain_id, selected_competency_id, plan_content, explainability, groups_snapshot) VALUES ($1, $2, 'numeracy', 'N2.3.3', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb) ON CONFLICT DO NOTHING", T, real_day)

        print("the seed stores yesterday's plan")
        r, snap = await dp.do_seed(db, T, end)
        ladder = await gs.ladder(db, dp.COMPETENCY)
        check("three groups, each on the skill the plan derives for N2.3.2 (Beginners N2.3.1, Progressors N2.3.2, Proficients N3.3.1)", {k: v["target"] for k, v in snap.items()} == {"beginner": "N2.3.1", "progressor": "N2.3.2", "proficient": "N3.3.1"} == {k: ladder[k]["id"] for k in snap}, snap)
        row = await plan_row(end)
        expl, stored = obj(row["explainability"]), obj(row["groups_snapshot"])
        check("the plan is stored for the last seeded day, as a plan for N2.3.2, marked as seeded", row is not None and row["selected_competency_id"] == "N2.3.2" and expl.get("demo_seed") is True)
        check("it keeps each group's children (roll numbers) as a real plan does, and the Progressors' children include the ones the evidence is about", all(stored[k]["rolls"] and stored[k]["count"] == len(stored[k]["rolls"]) for k in stored) and set(dp.PATTERNS) <= set(stored["progressor"]["rolls"]), {k: v["count"] for k, v in stored.items()})
        check("the teacher's recorded decisions: the Beginners ADVANCE, and the Progressors have NONE on purpose (the evidence recommends the re-teach)", expl.get("teacher_decision_beginner") == "advance" and "teacher_decision_progressor" not in expl and "teacher_decision_proficient" not in expl, expl)
        check("the plan is a real plan (the recorded sample for N2.3.2), not an empty one", bool(obj(row["plan_content"]).get("rotation_schedule", {}).get("blocks")))

        print("\nwhat the Plan screen then suggests (today)")
        p = await gs.propose(db, T, "numeracy", end + timedelta(days=1))
        g = p["groups"]
        check("there is a yesterday: the stored plan's date", p["has_history"] and p["previous_date"] == str(end))
        check("the seeded plan re-taught nobody (the Progressors' re-teach is the app's suggestion for TODAY, not something already done)", not any(p["groups"][k]["previous_reteach"] for k in p["groups"]))
        check("the Beginners: Advance, so N2.3.2 is suggested, from the teacher's decision", g["beginner"]["reason"] == "advance" and g["beginner"]["proposed"]["id"] == "N2.3.2")
        ev = g["progressor"]["evidence"]
        check("the Progressors: the three days of worksheets are the evidence: every child of the seed was assessed, a third or more made a mistake, so a RE-TEACH is recommended", ev["assessed"] == len(dp.PATTERNS) and ev["recommend"] and ev["with_mistakes"] >= ev["needed"], ev)
        check("...and with no decision recorded the suggestion is to stay on N2.3.2, said to come from the evidence", g["progressor"]["reason"] == "recommended" and g["progressor"]["proposed"]["id"] == "N2.3.2" and g["progressor"]["conflict"] is False)
        check("the Progressors' mistakes are named, with how many children made each", bool(ev["mistakes"]) and all(m["name_hi"] and m["children"] >= 1 for m in ev["mistakes"]), ev["mistakes"])
        check("the demo tells the SAME story every night (the seed is deterministic): 6 of the 14 made a mistake on the last day (rolls 16, 19, 24, 25, 26, 27), against 5 needed: the dropped carry 4 times, the whole ones sum 2 times",
              (ev["assessed"], ev["with_mistakes"], ev["needed"]) == (14, 6, 5) and ev["rolls"] == [16, 19, 24, 25, 26, 27] and {m["misconception_id"][-2:]: m["children"] for m in ev["mistakes"]} == {"M1": 4, "M2": 2}, ev)
        check("the Proficients: no decision and no evidence, so nothing is suggested (the skill follows the one chosen)", g["proficient"]["proposed"] is None and g["proficient"]["evidence"]["assessed"] == 0)

        print("\nseeding again, and reset")
        await dp.seed_yesterday_plan(db, T, end)
        check("seeding again leaves ONE plan for that day (nothing piles up night after night)", await db.fetchval("SELECT count(*) FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2 AND domain_id = 'numeracy'", T, end) == 1)
        r2 = await dp.reset(db, T)
        check("reset removes the plan the seed stored, and says so", r2["plans_deleted"] >= 1 and await plan_row(end) is None, r2)
        check("...and leaves a REAL plan alone (one stored for another day without the seed's mark)", await plan_row(real_day) is not None)
        await db.execute("INSERT INTO daily_plans (teacher_id, plan_date, domain_id, selected_competency_id, plan_content, explainability, groups_snapshot) VALUES ($1, $2, 'numeracy', 'N2.3.3', '{}'::jsonb, '{}'::jsonb, '{}'::jsonb)", T, end)
        await dp.seed_yesterday_plan(db, T, end)
        row = await plan_row(end)
        check("a real plan stored for the seeded day itself is replaced (the demo must tell the same story every day)", row["selected_competency_id"] == "N2.3.2" and obj(row["explainability"]).get("demo_seed") is True)
    finally:
        await tr.rollback()
    check("NOTHING was changed: the transaction was rolled back", await db.fetchval("SELECT count(*) FROM daily_plans WHERE teacher_id = $1", T) == before)
    await db.close()
    if failures:
        print(f"\nFAILED ({len(failures)})")
        sys.exit(1)
    print("\nOK: the seed stores yesterday's plan with the groups and the teacher's decisions, the Plan screen suggests from it, and reset only removes what the seed stored")


if __name__ == "__main__":
    asyncio.run(main())
