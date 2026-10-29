"""
Today's time (the Plan screen's 45 / 60 / 90-minute picker): the plan is laid out for the minutes the teacher chose. They reach the prompt builder as the plan's
teaching time, so the request to the AI says them and PART C splits them into blocks. Without the field the teacher's stored time is used (90 unless changed),
so an older app is unchanged. What the AI then makes of a shorter session (fewer activities, a shorter worksheet) is the prompt's work, not tested here.
The AI is a fake: no paid call.

    cd backend && AUTH_MODE=off python tests/test_plan_service.py --env-file .env
"""
import sys as _sys
for _stream in (_sys.stdout, _sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

import asyncio
import contextlib
import copy
import io
import json
import os
import re
import sys
from datetime import date, timedelta
from types import SimpleNamespace

os.environ.setdefault("AUTH_MODE", "off")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "prompts"))
import _scratch
import anthropic
from fastapi.testclient import TestClient
from app.main import app
from app.services import ai_budget, plan_service

TODAY = date.today()
failures = []
SAMPLE = json.load(open(os.path.join(HERE, "..", "..", "db", "seeds", "sample_plans", "N2.3.2.json"), encoding="utf-8"))


def check(label, ok, extra=""):
    print(f"  {'OK ' if ok else 'FAIL'} {label}{('  ' + str(extra)) if (extra and not ok) else ''}")
    if not ok:
        failures.append(label)


class FakeMessages:
    def __init__(self):
        self.prompts = []

    async def create(self, **kw):
        self.prompts.append(kw["messages"][0]["content"])
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=json.dumps(copy.deepcopy(SAMPLE), ensure_ascii=False))], stop_reason="end_turn",
                               usage=SimpleNamespace(input_tokens=6000, output_tokens=9000))


def minutes_in(prompt):
    """What the request to the AI says about the session: the stated teaching time, PART C's total, and the minutes of PART C's blocks added up."""
    stated = re.search(r"\*\*Available teaching time:\*\* (\d+) minutes", prompt)
    part_c = re.search(r"PART C: ROTATION SCHEDULE \((\d+) min total\)", prompt)
    section = prompt[part_c.start():] if part_c else ""
    blocks = [int(m) for m in re.findall(r"^- [^\n]*?\((\d+) min\)", section, re.M)]
    return (int(stated.group(1)) if stated else None), (int(part_c.group(1)) if part_c else None), blocks


async def main():
    db = await _scratch.connect()
    levels = {1: "beginner", 2: "beginner", 3: "progressor", 4: "progressor", 5: "progressor", 6: "proficient", 7: "proficient"}
    teacher_id, school = await _scratch.make_class(db, {r: (lv, lv) for r, lv in levels.items()}, grade="grade_2")
    real_client, fake = anthropic.AsyncAnthropic, FakeMessages()
    anthropic.AsyncAnthropic = lambda **kw: SimpleNamespace(messages=fake)
    try:
        async def gen(day, **kw):
            with contextlib.redirect_stdout(io.StringIO()):
                await plan_service.generate_dainik_yojana(db, teacher_id, "N2.3.2", "numeracy", day, **kw)
            return fake.prompts[-1]

        print("the prompt builder gets today's time")
        seen = {}
        for i, m in enumerate((45, 60, 90)):
            seen[m] = minutes_in(await gen(TODAY + timedelta(days=i), session_minutes=m))
            stated, total, _ = seen[m]
            check(f"{m} minutes chosen: the request to the AI says {m} minutes of teaching time, and PART C lays out {m} minutes", stated == m and total == m, seen[m][:2])
        check("the three lengths give three different layouts (the blocks get shorter, not just a label)", len({tuple(seen[m][2]) for m in seen}) == 3 and sum(seen[45][2]) < sum(seen[60][2]) < sum(seen[90][2]), {m: seen[m][2] for m in seen})
        stated, total, _ = minutes_in(await gen(TODAY + timedelta(days=3)))
        check("no time given: the teacher's stored time, which is 90 unless changed (an older app is unchanged)", stated == 90 and total == 90, (stated, total))

        print("\nthe plan records its length (the plan screen's time chip reads it)")
        async def stored(day):
            row = await db.fetchrow("SELECT plan_content FROM daily_plans WHERE teacher_id = $1 AND plan_date = $2 AND domain_id = 'numeracy'", teacher_id, day)
            pc = row["plan_content"]
            return json.loads(pc) if isinstance(pc, str) else pc
        check("(the AI's own total_minutes in the fixture is 90, so a 45 can only come from the teacher's choice)", SAMPLE["rotation_schedule"]["total_minutes"] == 90)
        pc = await stored(TODAY)
        check("45 chosen: the stored plan records session_minutes 45, not the AI's own total_minutes (90)", pc.get("session_minutes") == 45 and pc["rotation_schedule"].get("total_minutes") == 90, pc.get("session_minutes"))
        check("60 chosen: 60 recorded", (await stored(TODAY + timedelta(days=1))).get("session_minutes") == 60)
        check("nothing chosen: the time the plan was laid out for (the teacher's stored time, 90) is recorded", (await stored(TODAY + timedelta(days=3))).get("session_minutes") == 90)
        real_check = ai_budget.check
        async def cap(*a, **k):
            raise ai_budget.AICapReached("disabled")
        ai_budget.check = cap
        try:
            n_before = len(fake.prompts)
            with contextlib.redirect_stdout(io.StringIO()):
                res = await plan_service.generate_dainik_yojana(db, teacher_id, "N2.3.2", "numeracy", TODAY + timedelta(days=4), session_minutes=45)
        finally:
            ai_budget.check = real_check
        pc = await stored(TODAY + timedelta(days=4))
        check("the AI limit reached with 45 chosen: the recorded sample plan is served and records the length it was made for, 90 (not the 45 asked for)",
              res["served_from"] == "sample" and len(fake.prompts) == n_before and pc.get("session_minutes") == 90 and res["plan"]["session_minutes"] == 90, (res["served_from"], pc.get("session_minutes")))

        print("\nthe API")
        with TestClient(app) as c:
            def post(day, **extra):
                return c.post(f"/api/plan/generate?teacher_id={teacher_id}", json={"competency_id": "N2.3.2", "domain_id": "numeracy", "plan_date": str(TODAY + timedelta(days=day)), **extra})
            n = len(fake.prompts)
            r = post(5, session_minutes=45)
            check("POST /plan/generate with session_minutes 45: the plan is made for 45 minutes", r.status_code == 200 and len(fake.prompts) == n + 1 and minutes_in(fake.prompts[-1])[0] == 45, r.text[:140])
            check("...and the reply carries it in the plan", r.status_code == 200 and r.json()["plan"]["session_minutes"] == 45)
            r = c.get(f"/api/plan/{teacher_id}/{TODAY + timedelta(days=5)}/numeracy")
            check("a stored plan opened again (GET /plan/...) carries it too", r.status_code == 200 and r.json()["plan"]["session_minutes"] == 45, r.text[:140])
            r = post(6)
            check("without session_minutes: 90", r.status_code == 200 and minutes_in(fake.prompts[-1])[0] == 90 and r.json()["plan"]["session_minutes"] == 90, r.text[:140])
            n = len(fake.prompts)
            for bad in (50, 0, "45 मिनट", 120):
                r = post(7, session_minutes=bad)
                check(f"a time the app does not offer ({bad!r}) is refused (HTTP 422), before any paid call", r.status_code == 422 and len(fake.prompts) == n, r.status_code)

            print("\nan existing plan is never replaced silently (item 12): only with replace: true")
            stored5 = lambda: c.get(f"/api/plan/{teacher_id}/{TODAY + timedelta(days=5)}/numeracy").json()["plan"]["session_minutes"]
            n = len(fake.prompts)
            r = post(5, session_minutes=60)
            check("day 5 already has a plan: without replace, HTTP 409 plan_exists, with a message the app can show", r.status_code == 409 and r.json()["detail"]["code"] == "plan_exists" and r.json()["detail"]["message"], r.text[:140])
            check("...refused before any paid call, and the stored plan is untouched (still 45 minutes)", len(fake.prompts) == n and stored5() == 45)
            r = post(5, session_minutes=60, replace=False)
            check("replace: false is the same refusal", r.status_code == 409 and len(fake.prompts) == n)
            r = post(5, session_minutes=60, replace=True)
            check("replace: true replaces it: one AI call, and the stored plan is the new one (60 minutes)", r.status_code == 200 and len(fake.prompts) == n + 1 and stored5() == 60, r.text[:140])
            kid = await db.fetchval("SELECT id FROM children WHERE teacher_id = $1 AND roll_number = 3", teacher_id)
            await db.execute("INSERT INTO assessment_evidence (child_id, competency_id, teacher_id, channel, status, evidence_data, session_date) VALUES ($1, 'N2.3.2', $2, 'observed', 'achieved', '{}'::jsonb, $3)",
                             kid, teacher_id, TODAY + timedelta(days=5))
            n = len(fake.prompts)
            r1, r2 = post(5), post(5, replace=True)
            check("the server does not look at evidence: with a result recorded it is still 409 without replace, and still replaced with it", r1.status_code == 409 and r2.status_code == 200 and len(fake.prompts) == n + 1, (r1.status_code, r2.status_code))
            for stage, d in (("first", "advance"), ("final", "reteach")):
                c.post(f"/api/review/decisions?teacher_id={teacher_id}", json={"plan_date": str(TODAY + timedelta(days=5)), "domain_id": "numeracy", "decisions": {"progressor": d}, "stage": stage})
            post(5, replace=True)
            j = c.get(f"/api/plan/{teacher_id}/{TODAY + timedelta(days=5)}/numeracy").json()
            check("a plan made again keeps the day's review: the first judgment, the final decision and the current decision",
                  j.get("first_judgments") == {"progressor": "advance"} and j.get("final_decisions") == {"progressor": "reteach"} and j.get("decisions") == {"progressor": "reteach"}, (j.get("first_judgments"), j.get("final_decisions"), j.get("decisions")))
            r = post(8, replace=True)
            check("replace: true with no plan that day simply makes one", r.status_code == 200, r.text[:140])
            r = post(9)
            check("a day with no plan needs no replace", r.status_code == 200, r.text[:140])
            r = c.post(f"/api/plan/generate?teacher_id={teacher_id}", json={"competency_id": "L2.7.2", "domain_id": "r1_literacy", "plan_date": str(TODAY + timedelta(days=5))})
            check("per subject: a maths plan on day 5 does not block a Hindi plan that day", r.status_code != 409, r.status_code)
    finally:
        await db.execute("DELETE FROM assessment_evidence WHERE teacher_id = $1", teacher_id)
        anthropic.AsyncAnthropic = real_client
        await db.execute("DELETE FROM daily_plans WHERE teacher_id = $1", teacher_id)
        await _scratch.remove_class(db, teacher_id, school)
        await db.close()
    if failures:
        print(f"\nFAILED ({len(failures)})")
        for f in failures:
            print("  -", f)
        sys.exit(1)
    print("\nOK: the plan is laid out for the time the teacher chose (45, 60 or 90 minutes), and for 90 when none is given")


if __name__ == "__main__":
    asyncio.run(main())
